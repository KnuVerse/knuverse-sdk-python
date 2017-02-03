"""
Copyright 2014, Intellisis
All rights reserved.
"""
from __future__ import print_function
import os
import sys
import re
import requests
from functools import wraps
from datetime import datetime, timedelta

from .data import url
from . import exceptions as ex


class Knufactor:
    def __init__(self,
                 apikey,
                 secret,
                 server="https://cloud.knuverse.com",
                 base_uri="/api/v1/"):

        if not server.startswith("http://") and not server.startswith("https://"):
            # Allow not specifying the HTTP protocol to use. Default to https
            server = "https://" + server

        self._server = server + base_uri
        self._apikey = apikey
        self._secret = secret
        self._last_auth = None
        self._auth_token = None
        self._headers = {
            "Accept": "application/json",
        }
        self.version = "1.0.9"

    # Private Methods
    # ###############

    def _auth(f):
        """
        Makes sure the request has a valid authorization jwt before calling the wrapped function.
        It does this by checking the timestamp of the last jwt and if > 10 minutes have elapsed,
        it refreshes it's existing jwt from the server.
        Args:
            f: Function to wrap

        Returns:
            Function, f
        """
        @wraps(f)
        def method(self, *args, **kwargs):
            if not self._auth_token or datetime.utcnow() >= self._last_auth + timedelta(minutes=10):
                # Need to get new jwt
                self.auth_refresh()

            return f(self, *args, **kwargs)
        return method

    def _get(self, uri, params=None, headers=None):
        if not headers:
            headers = {}
        headers.update(self._headers)
        r = requests.get(self._server + uri, params=params, headers=headers)
        return r

    def _post(self, uri, body=None, headers=None):
        if not headers:
            headers = {}

        headers.update(self._headers)
        headers.update({
            "Content-type": "application/json"
        })
        r = requests.post(self._server + uri, json=body, headers=headers)
        return r

    def _put(self, uri, body=None, files=None, headers=None):
        if not headers:
            headers = {}

        headers.update(self._headers)
        r = requests.put(self._server + uri, json=body, files=files, headers=headers)
        return r

    def _delete(self, uri, body=None, headers=None):
        if not headers:
            headers = {}

        headers.update(self._headers)
        r = requests.delete(self._server + uri, json=body, headers=headers)
        return r

    def _head(self, uri, headers=None):
        if not headers:
            headers = {}

        headers.update(self._headers)
        r = requests.head(self._server + uri, headers=headers)
        return r

    @staticmethod
    def _create_response(response):
        """
        Attempts to decode JSON response.
        If encoding fails(due to empty response: 204 No Content, etc), None

        Args:
            response: Requests response object

        Returns: JSON body or None
        """

        try:
            r = response.json()
        except ValueError:
            r = None

        return r

    @staticmethod
    def _check_response(response, expected):
        """
        Checks if the expected response code matches the actual response code.
        If they're not equal, raises the appropriate exception
        Args:
            response: (int) Actual status code
            expected: (int) Expected status code
        """

        response_code = response.status_code
        if expected == response_code:
            return

        if response_code < 400:
            raise ex.UnexpectedResponseCodeException(response.text)

        elif response_code == 401:
            raise ex.UnauthorizedException(response.text)

        elif response_code == 400:
            raise ex.BadRequestException(response.text)

        elif response_code == 403:
            raise ex.ForbiddenException(response.text)

        elif response_code == 404:
            raise ex.NotFoundException(response.text)

        elif response_code == 429:
            raise ex.RateLimitedException(response.text)

        else:
            raise ex.InternalServerErrorException(response.text)

    def _client_id(self, client):

        # If not formatted like a client ID, assume it's a client name and get the ID.
        if not re.match(r"[a-f,0-9]{32}", client):
            client = self.client_id(client)

        if not client:
            raise ex.NotFoundException("%s not found." % client)

        return client

    # Authentication interfaces
    # =========================

    def auth_refresh(self, apikey=None, secret=None):
        """
        Renew authentication token manually.  Uses POST to /auth interface

        :param apikey: Unique identifier for authorized use of the API
        :type apikey: str or None
        :param secret: The secret password corresponding to the API key.
        :type secret: str or None
        :Returns: None

        """
        jwt = self.auth_token(apikey, secret)
        self._headers["Authorization"] = "Bearer %s" % jwt

        self._auth_token = jwt
        self._last_auth = datetime.utcnow()

    def auth_token(self, apikey, secret):
        """
        Get authentication token.  Uses POST to /auth interface.

        :Returns: (str) Authentication JWT
        """
        body = {
            "key_id": apikey or self._apikey,
            "secret": secret or self._secret
        }
        response = self._post(url.auth, body=body)

        self._check_response(response, 200)
        return self._create_response(response).get("jwt")

    @_auth
    def auth_grant(self, client, role=None, mode=None):
        """
        Used to get a grant token.  Grant tokens expire after 5 minutes for role "grant_verify" and 10 minutes for the
        "grant_enroll" and "grant_enroll_verify" roles. Grant tokens can be used to start enrollments and verifications.
        Uses POST to /auth/grant interface

        :Args:
          * *client*: (str) Client name

        :Kwargs:
          * *role*: (str or None) The grant token role. Can be "grant_verify", "grant_enroll", or "grant_enroll_verify". If role is not sent in, the role defaults to "grant_verify".
          * *mode*: (str or None) The mode to perform actions with. Can be "audiopass" or "audiopin". It defaults to the module setting's "mode_default" if None is passed in.

        :Returns: (dictionary) Specified below

        :Return Dictionary:
          * *jwt* - (str) Grant token that can be used to do verifications
          * *mode* - (str) Default enrollment and verification mode for the server. Either "audiopin" or "audiopass"
        """

        body = {
            "name": client
        }
        if role:
            body["role"] = role
        if mode:
            body["mode"] = mode
        response = self._post(url.auth_grant, body=body)

        self._check_response(response, 200)
        return self._create_response(response)

    # Client interfaces
    ###################

    @_auth
    def client_create(self, name, password):
        """
        Create a new client.  Uses the POST to /clients interface.

        :Args:
          * *name*: (str) Name of client
          * *password*: (str) Password of client
        :Returns: (str) ID of the newly created client.
        """
        body = {
            "name": name,
            "password": password
        }
        response = self._post(url.clients, body=body)
        self._check_response(response, 201)
        return self._create_response(response).get("client_id")

    @_auth
    def client_count(self):
        """
        Get number of clients.  Uses HEAD to /clients interface.

        :Returns: (int) Number of clients
        """
        response = self._head(url.clients)
        self._check_response(response, 200)
        return int(response.headers.get("x-client-count", -1))

    @_auth
    def client_list(self, name=None, name_only=None, all_enrolled=None):
        """
        Get list of clients.  Uses GET to /clients interface.

        :Kwargs:
          * *name*: (str) If specified, returns the client information for this client only.
          * *name_only*: (bool) If true, returns only the names of the clients requested
          * *all_enrolled*: (bool) If true, will return all enrolled clients

        :Returns:  (list) List of dictionaries with the client information as requested.
        """
        params = {}

        if name:                    # When specific name value is provided
            params["name"] = name
        if name_only:               # (Boolean) "True": only keyword "name" is provided
            params["name"] = ""
        if all_enrolled:            # (Boolean) "True": returns all enrolled clients
            params["all_enrolled"] = all_enrolled

        response = self._get(url.clients, params=params)

        self._check_response(response, 200)
        if name:
            return response.json()
        return self._create_response(response).get("clients")

    @_auth
    def client_id(self, client):
        """
        Get a client's ID.  Uses GET to /clients?name=<client> interface.

        :Args:
            * *client*: (str) Client's name

        :Returns: (str) Client id
        """

        params = {
            "name": client
        }

        response = self._get(url.clients, params=params)
        self._check_response(response, 200)
        return self._create_response(response).get("client_id")

    @_auth
    def client_info(self, client):
        """
        Get client info.  Uses GET to /clients/<client> interface.

        :Args:
            * *client*: (str) Client's ID

        :Returns: (dict) Client dictionary
        """
        client = self._client_id(client)
        response = self._get(url.clients_id.format(id=client))
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def client_validate_password(self, client, password):
        """
        Validate client's password.  Uses PUT to /clients/<client> interface.

        :Args:
            * *client*: (str) Client's ID
            * *password*: (str) Client's Password
        """

        client = self._client_id(client)
        body = {
            "action": "validate_password",
            "auth_password": password
        }

        response = self._put(url.clients_id.format(id=client), body=body)
        self._check_response(response, 200)

    @_auth
    def client_validate_pin(self, client, pin):
        """
        Validate client's PIN.  Uses PUT to /clients/<client> interface.

        :Args:
            * *client*: (str) Client's ID
            * *pin*: (str) Client's PIN
        """

        client = self._client_id(client)
        body = {
            "action": "validate_pin",
            "current_pin": pin
        }

        response = self._put(url.clients_id.format(id=client), body=body)
        self._check_response(response, 200)

    @_auth
    def client_update(self,
                           client,
                           reason=None,
                           pin=None,
                           current_pin=None,
                           verification_speed=None,
                           row_doubling=None,
                           password=None,
                           bypass_expiration=None,
                           bypass_limit=None,
                           bypass_spacing_minutes=None,
                           bypass_code=None,
                           is_disabled=None,
                           verification_lock=None,
                           password_lock=None,
                           enroll_deadline_extension_minutes=None,
                           enroll_deadline_enable=None,
                           windows_profile=None,
                           role_rationale=None,
                           role=None,
                           ):
        """
        Update client info
        Uses PUT to /clients/<client> interface

        :Args:
            * *client*: (str) Client's ID

        :Kwargs:
            * *reason*: (str) The reason for changing the client's settings
            * *pin*: (str) The new PIN to set
            * *current_pin*: (str) The current PIN of the user. Only required if role is not admin and the Account Reset Mode (System Configuration) requires PIN.
            * *verification_speed*: (int) The speed at which the verification should appear for the client.  Allowed values: 0, 25, 50, 75, 100.
            * *row_doubling*: (str) Row doubling is an AudioPIN only option that puts two rows of words in each pinpad digit.  Allowed values: "OFF", "TRAIN", "ON"
            * *password*: (str) New client password
            * *bypass_expiration*: (int) Used to enable/disable a client's bypass. The time, in minutes, from when the request was received until the bypass expires. 0 removes the bypass, while -1 sets a bypass that doesn't expire.
            * *bypass_limit*: (int) The number of times a user may bypass. Set to 0 for no limit. If set without either an existing valid bypass_expiration, or providing one in the request, the client's bypass_expiration will be set to 10 mins.  Default value: 0.  Size range: >=0
            * *bypass_spacing_minutes*: (int) Specifies the time, in minutes, the user must wait between using each bypass. Set to 0 for no bypass rate limiting. If set without either an existing valid bypass_expiration, or providing one in the request, the client's bypass_expiration will be set to 10 mins.
            * *bypass_code*: (str) The code that the client must enter to bypass.
            * *is_disabled*: (bool) If true, the client cannot do verifications (will automatically bypass).
            * *verification_lock*: (bool) Unlocks the given client if the client verified incorrectly too many times.
            * *password_lock*: (bool) Set to false to unlock a client who enter thier password incorrectly too many times.
            * *enroll_deadline_extension_minutes*: (int) Amount of time, in minutes, to extend an enrollment deadline by.
            * *enroll_deadline_enable*: (bool) When true, enables the enrollment deadline for a certain client, when false disables an enrollment deadline.
            * *windows_profile*: (str) Assigns a Windows Profile to the user using the Windows Profile ID. To remove a profile, send null.
            * *role_rationale*: (str) Update the client rationale for a role
            * *role*: (str) Update the client role. Note: Google users cannot have their role updated.  Allowed values: "admin", "manager", "support", "user".

        :More information: Can be found `here <https://cloud.knuverse.com/docs/api/#api-Clients-Update_client_information>`_.

        """
        client = self._client_id(client)

        body = {}
        if reason is not None:
            body["reason"] = reason
        if pin is not None:
            body["pin"] = pin
        if current_pin is not None:
            body["current_pin"] = current_pin
        if verification_speed is not None:
            body["verification_speed"] = verification_speed
        if row_doubling is not None:
            body["row_doubling"] = row_doubling
        if password is not None:
            body["auth_password"] = self._password
            body["password"] = password
        if bypass_expiration is not None:
            body["bypass_expiration"] = bypass_expiration
        if bypass_limit is not None:
            body["bypass_limit"] = bypass_limit
        if bypass_spacing_minutes is not None:
            body["bypass_spacing_minutes"] = bypass_spacing_minutes
        if bypass_code is not None:
            body["bypass_code"] = bypass_code
        if is_disabled is not None:
            body["is_disabled"] = is_disabled
        if verification_lock is not None:
            body["verification_lock"] = verification_lock
        if password_lock is not None:
            body["password_lock"] = password_lock
        if enroll_deadline_extension_minutes is not None:
            body["enroll_deadline_extension_minutes"] = enroll_deadline_extension_minutes
        if enroll_deadline_enable is not None:
            body["enroll_deadline_enable"] = enroll_deadline_enable
        if windows_profile is not None:
            body["windows_profile"] = windows_profile
        if role is not None:
            body["auth_password"] = self._password
            body["role"] = role
        if role_rationale is not None:
            body["role_rationale"] = role_rationale

        response = self._put(url.clients_id.format(id=client), body=body)
        self._check_response(response, 200)

    @_auth
    def client_unenroll(self, client):
        """
        Unenroll a client.  Uses DELETE to /clients/<client> interface.

        :Args:
            * *client*: (str) Client's ID
        """
        client = self._client_id(client)
        response = self._delete(url.clients_id.format(id=client))
        self._check_response(response, 204)

    # Enrollment interfaces
    #######################

    @_auth
    def enrollment_resource(self, client, audio=False):
        """
        Get Client Enrollment Data.  Uses GET to /enrollments/<client> interface.

        :Args:
            * *client*: (str) Client's ID
            * *audio*: (boolean) If True then the enrollment audio is returned.
        :Returns: (dictionary) Look `here <https://cloud.knuverse.com/docs/api/#api-Enrollments-Get_enrollment_info>`_ for information on keys and values.
        """
        client = self._client_id(client)
        params = {}
        if audio:
            params["audio"] = True

        response = self._get(url.enrollments_id.format(id=client), params=params)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def enrollment_start(
            self,
            name,
            mode=None,
            pin=None,
            phone_number=None
    ):
        """
        Start Client Enrollment.  Uses the POST to /enrollments interface.

        :Args:
            * *client*: (str) Client's Name
            * *mode*: (str) DEPRECATED. Presence of PIN is used to determine mode (AudioPass vs AudioPIN)
            * *pin*: (str) Client's PIN. 4 digit string
            * *phone_number*: (str) Phone number to call.

        :Returns: (dict) Enrollment record with prompts as described `here <https://cloud.knuverse.com/docs/api/#api-Enrollments-Start_enrollment>`_.
        """
        data = {
            "name": name,
        }

        if mode:
            warning_msg = 'WARNING: The "mode" parameter for enrollment_start is DEPRECATED and will be ignored. ' \
                          'To avoid incompatibility with a future release please stop providing it.'
            print(warning_msg, file=sys.stderr)
        if pin:
            data["pin"] = pin
        if phone_number:
            data["phone_number"] = phone_number

        response = self._post(url.enrollments, body=data)
        self._check_response(response, 201)
        return self._create_response(response)

    @_auth
    def enrollment_upload(
        self,
        enrollment_id,
        audio_file,
    ):
        """
        Upload Enrollment Data.  Uses PUT to /enrollments/<enrollment_id> interface.

        :Args:
            * *enrollment_id*: (str) Enrollment's ID
            * *audio_file*: (str) Path to the audio file of the recorded words. Not required for phone enrollments.

        """
        files = {
            "file": os.path.basename(audio_file),
            os.path.basename(audio_file): open(audio_file, 'rb')
        }

        response = self._put(url.enrollments_id.format(id=enrollment_id), files=files)
        self._check_response(response, 202)

    # Event interfaces
    # ================

    @_auth
    def events_client(self, client):
        """
        Get a client's events.  Uses GET to /events/clients/<client> interface.

        :Args:
          * *client*: (str) Client's ID

        :Returns: (list) Events
        """
        # TODO Add paging to this
        client = self._client_id(client)
        response = self._get(url.events_clients_id.format(id=client))
        self._check_response(response, 200)
        return self._create_response(response).get("events")

    @_auth
    def events_clients(self):
        """
        Get all client events.  Uses GET to /events/clients interface.

        :Returns: (list) Events
        """
        # TODO Add paging to this
        response = self._get(url.events_clients)
        self._check_response(response, 200)
        return self._create_response(response).get("events")

    @_auth
    def events_login(self):
        """
        Get all login events.  Uses GET to /events/login interface.

        :Returns: (list) Events
        """
        # TODO Add paging to this
        response = self._get(url.events_logins)
        return self._create_response(response).get("events")

    @_auth
    def events_system(self):
        """
        Get all system events.  Uses GET to /events/system interface.

        :Returns: (list) Events
        """
        # TODO Add paging to this
        response = self._get(url.events_system)
        self._check_response(response, 200)
        return self._create_response(response).get("events")

    # General interfaces
    # ==================
    def about(self):
        """
        Get server info.  Uses GET to /about interface

        :returns: dict - Server information
        """
        response = self._get(url.about)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def status(self):
        """
        Get server status.  Uses GET to /status interface.

        :Returns: (dict) Server status as described `here <https://cloud.knuverse.com/docs/api/#api-General-Status>`_.
        """
        response = self._get(url.status)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def warnings(self):
        """
        Get server system warnings.  Uses GET to /status/warnings.

        :returns: (dict) Server messages and warnings as described `here <https://cloud.knuverse.com/docs/api/#api-General-Warnings>`_.
        """
        response = self._get(url.status_warnings)
        self._check_response(response, 200)
        return self._create_response(response)

    # System Modules interfaces
    ###########################

    @_auth
    def module_settings(self):
        """
        Get Module settings.  Uses GET to /settings/modules interface.

        :Returns: (dict) Module settings as shown `here <https://cloud.knuverse.com/docs/api/#api-Module_Settings-Get_the_module_settings>`_.
        """
        response = self._get(url.settings_modules)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def settings_module_update(self,
                            mode_audiopin_enable=None,
                            mode_audiopass_enable=None,
                            mode_default=None):
        """
        Set Module settings.  Uses PUT to /settings/modules interface.

        :Args:
          * *mode_audiopin_enable*: (bool) Turn on and off the AudioPIN feature
          * *mode_audiopass_enable*: (bool) Turn on and off the AudioPass feature
          * *mode_default*: (str)  Set the default verification mode.  Either 'audiopin' or 'audiopass'.

        :Returns: None
        """
        body = {
            "auth_password": self._password
        }
        if mode_audiopin_enable:
            body["mode_audiopin_enable"] = mode_audiopin_enable
        if mode_audiopass_enable:
            body["mode_audiopass_enable"] = mode_audiopass_enable
        if mode_default:
            body["mode_default"] = mode_default

        response = self._put(url.settings_modules, body=body)
        self._check_response(response, 200)

    @_auth
    def settings_module_reset(self):
        """
        Resets the module settings back to default.  Uses DELETE to /settings/modules interface.
        """
        data = {
            "auth_password": self._password
        }

        response = self._delete(url.settings_modules, body=data)
        self._check_response(response, 204)

    # Report generation interfaces
    ##############################

    @staticmethod
    def _format_input_dates(start_date, end_date):

        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise TypeError("Start date and end date must be datetime objects")

        start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")
        return start_str, end_str

    @_auth
    def report_events(self, start_date, end_date, type="system"):
        """
        Create a report for all client events or all system events.
        Uses GET to /reports/events/{clients,system} interface

        :Args:
          * *start_date*: (datetime) Start time for report generation
          * *end_date*: (datetime) End time for report generation
        :Kwargs:
          * *type*: (str) Type of event report to create. "system" or "clients"

        :Returns: (list) List of events in the input range

        """


        start_str, end_str = self._format_input_dates(start_date, end_date)
        params = {
            "start_date": start_str,
            "end_date": end_str
        }
        endpoint = url.reports_events_clients if type == "clients" else url.reports_events_system
        response = self._get(endpoint, params=params)
        self._check_response(response, 200)
        return self._create_response(response).get("events")

    @_auth
    def report_verifications(self, start_date, end_date):
        """
        Create a report for all verifications.  Uses GET to /reports/verifications interface

        :Args:
            * *start_date*: (datetime) Start time for report generation
            * *end_date*: (datetime) End time for report generation

        :Returns: (str) CSV formatted report string

        """
        start_str, end_str = self._format_input_dates(start_date, end_date)
        params = {
            "start_date": start_str,
            "end_date": end_str
        }
        response = self._get(url.reports_verifications, params=params)
        self._check_response(response, 200)
        return self._create_response(response)

    # System Settings interfaces
    ############################

    @_auth
    def settings_system(self):
        """
        Get system settings.  Uses GET to /settings/system interface.

        :Returns: (dict) System settings as shown `here <https://cloud.knuverse.com/docs/api/#api-System_Settings-Get_System_Settings>`_.

        """
        response = self._get(url.settings_system)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def settings_system_update(self, data):
        """
        Set system settings.  Uses PUT to /settings/system interface

        :Args:
            * *data*: (dict) Settings dictionary as specified `here <https://cloud.knuverse.com/docs/api/#api-System_Settings-Set_System_Settings>`_.

        :Returns: None
        """
        data["auth_password"] = self._password

        response = self._put(url.settings_system, body=data)
        self._check_response(response, 200)

    @_auth
    def settings_system_reset(self):
        """
        Resets the system settings back to default.  Uses DELETE to /settings/system interface.
        """
        data = {
            "auth_password": self._password
        }

        response = self._delete(url.settings_system, body=data)
        self._check_response(response, 204)

    # Verification interfaces
    #########################

    @_auth
    def verification_start(
        self,
        client,
        mode=None,
        verification_speed=None,
        row_doubling="off",
        phone_number=None,
    ):
        """
        Start a verification.  Uses POST to /verifications interface.

        :Args:
            * *client*: (str) Client's Name
            * *mode*: (str) Verification Mode. Allowed values: "audiopin", "audiopass"
            * *verification_speed*: (int) Allowed values: 0, 25, 50, 75, 100
            * *row_doubling*: (str) Allowed values: "off", "train", "on"
            * *phone_number*: (str) Phone number to call.

        :Returns: (dict) Verification record with animation as discussed `here <https://cloud.knuverse.com/docs/api/#api-Verifications-Start_verification>`_.
        """

        data = {
            "name": client,
            "user_agent": "knuverse-sdk-python-v%s" % self.version
        }
        if mode:
            data["mode"] = mode

        if phone_number:
            data["phone_number"] = phone_number

        if verification_speed:
            data["verification_speed"] = verification_speed

        if row_doubling:
            data["row_doubling"] = row_doubling

        response = self._post(url.verifications, body=data)
        self._check_response(response, 201)
        return self._create_response(response)

    @_auth
    def verification_upload(
            self,
            verification_id,
            audio_file=None,
            bypass=False,
            bypass_pin=None,
            bypass_code=None,
            ):
        """
        Upload verification data.  Uses PUT to /verfications/<verification_id> interface

        :Args:
            * *verification_id*: (str) Verification ID
            * *audio_file*: (str) Path to the audio file of the recorded words. Not required for phone verifications.
            * *bypass*: (boolean) True if using a bypass code or pin to verify
            * *bypass_pin*: (str) Client's PIN if this is a bypass
            * *bypass_code*: (str) Client's bypass code if this is a bypass
        """
        files = {}
        if audio_file:
            files[os.path.basename(audio_file)] = open(audio_file, 'rb')
            files["file"] = os.path.basename(audio_file)
        elif bypass:
            files["bypass"] = True
            files["bypass_code"] = bypass_code
            files["pin"] = bypass_pin
        response = self._put(url.verifications_id.format(id=verification_id), files=files)
        self._check_response(response, 202)
        return self._create_response(response)

    @_auth
    def verification_cancel(self, verification_id, reason=None):
        """
        Cancels a started verification.  Uses PUT to /verifications/<verification_id> interface

        :Args:
          * *verification_id*: (str) Verification ID
        :Kwargs:
          * *reason*: (str) Reason for cancelling the verification

        :Returns: None
        """

        data = {
            "cancel": True,
            "cancel_reason": reason
        }

        response = self._put(url.verifications_id.format(id=verification_id), body=data)
        self._check_response(response, 202)

    @_auth
    def verification_delete(self, verification_id):
        """
        Remove verification.  Uses DELETE to /verifications/<verification_id> interface.

        :Args:
            * *verification_id*: (str) Verification ID
        """
        response = self._delete(url.verifications_id.format(id=verification_id))
        self._check_response(response, 204)

    @_auth
    def verification_count(self):
        """
        Get Verification Count.  Uses HEAD to /verifications interface.

        :Returns: (int) Number of verifications
        """
        response = self._head(url.verifications)
        self._check_response(response, 200)
        return int(response.headers.get('x-verification-count', -1))

    @_auth
    def verification_list(self, limit=10):
        """
        Get list of verifications.  Uses GET to /verifications interface.

        :Returns: (list) Verification list as specified `here <https://cloud.knuverse.com/docs/api/#api-Verifications-Get_verification_list>`_.
        """

        # TODO add arguments for paging and stuff
        params = {}
        params["limit"] = limit

        response = self._get(url.verifications, params=params)
        self._check_response(response, 200)
        return self._create_response(response).get("verifications")

    @_auth
    def verification_resource(self, verification_id, audio=False):
        """
        Get Verification Resource.  Uses GET to /verifications/<verification_id> interface.

        :Args:
            * *verification_id*: (str) Verification ID
            * *audio*: (boolean) If True, audio data associated with verification will be returned.
        :Returns: (dict) Verification data as shown `here <https://cloud.knuverse.com/docs/api/#api-Verifications-Get_verification_info>`_.
        """
        params = {}
        if audio:
            params["audio"] = True

        response = self._get(url.verifications_id.format(id=verification_id), params=params)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def verification_resource_secure(self, verification_id, jwt, name):
        """
        Get Verification Resource.
        Uses GET to /verifications/<verification_id> interface
        Use this method rather than verification_resource when adding a second factor to your application.
        See `this <https://cloud.knuverse.com/docs/integration/>`_ for more information.

        :Args:
            * *verification_id*: (str) Verification ID
            * *jwt*: (str) Completion token received from application
            * *name*: (str) Client name associated with the jwt. Received from application.

        :Returns: (dict) Verification data as shown `here <https://cloud.knuverse.com/docs/api/#api-Verifications-Get_verification_info>`_.
        """
        params = {
            "jwt": jwt,
            "name": name
        }

        response = self._get(url.verifications_id.format(id=verification_id), params=params)
        self._check_response(response, 200)
        return self._create_response(response)
