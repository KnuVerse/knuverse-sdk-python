"""
Copyright 2014, Intellisis
All rights reserved.
"""
import os
import re
import json
import requests
from functools import wraps
from datetime import datetime, timedelta

from .data import url
requests.packages.urllib3.disable_warnings()


class RequestException(Exception):
    """
    Used for invalid requests.
    """


class UnexpectedResponseCodeException(Exception):
    """
    Raised when the server returns an unexpected response code.
    """


class HttpErrorException(Exception):
    """
    Used for HTTP errors. Status codes >= 400
    """


class BadRequestException(HttpErrorException):
    """
    Used for HTTP Bad Request(400) Errors
    """


class UnauthorizedException(HttpErrorException):
    """
    Used for HTTP Unauthorized(401) Errors
    """


class ForbiddenException(HttpErrorException):
    """
    Used for HTTP Forbidden(403) Errors
    """


class NotFoundException(HttpErrorException):
    """
    Used for HTTP Not Found(404) Errors
    """


class InternalServerErrorException(HttpErrorException):
    """
    Used for HTTP Internal Server Error(500) Errors
    """


class Knufactor:
    def __init__(self,
                 server,
                 username=None,
                 password=None,
                 account=None,
                 noauth=False,
                 base_uri="/api/v1/"):

        if not server.startswith("http://") and not server.startswith("https://"):
            # Allow not specifying the HTTP protocol to use. Default to https
            server = "https://" + server

        self._server = server + base_uri
        self._username = username
        self._password = password
        self._account = account
        self._last_auth = None
        self._auth_token = None
        self._noauth = noauth
        self._headers = {
            "Accept": "application/json",
        }
        self.version = "1.0.3"

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
            if not self._noauth and (not self._auth_token or datetime.utcnow() >= self._last_auth + timedelta(minutes=10)):
                # Need to get new jwt
                self.refresh_auth()

            return f(self, *args, **kwargs)
        return method

    def _get(self, uri, params=None, headers=None):
        if not headers:
            headers = {}
        headers.update(self._headers)
        r = requests.get(self._server + uri, params=params, headers=headers, verify=False)
        return r

    def _post(self, uri, body=None, headers=None):
        if not headers:
            headers = {}

        headers.update(self._headers)
        headers.update({
            "Content-type": "application/json"
        })
        r = requests.post(self._server + uri, json=body, headers=headers, verify=False)
        return r

    def _put(self, uri, body=None, files=None, headers=None):
        if not headers:
            headers = {}

        headers.update(self._headers)
        r = requests.put(self._server + uri, json=body, files=files, headers=headers, verify=False)
        return r

    def _delete(self, uri, body=None, headers=None):
        if not headers:
            headers = {}

        headers.update(self._headers)
        r = requests.delete(self._server + uri, json=body, headers=headers, verify=False)
        return r

    def _head(self, uri, headers=None):
        if not headers:
            headers = {}

        headers.update(self._headers)
        r = requests.head(self._server + uri, headers=headers, verify=False)
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
            raise UnexpectedResponseCodeException(response.text)

        elif response_code == 401:
            raise UnauthorizedException(response.text)

        elif response_code == 400:
            raise BadRequestException(response.text)

        elif response_code == 403:
            raise ForbiddenException(response.text)

        elif response_code == 404:
            raise NotFoundException(response.text)

        else:
            raise InternalServerErrorException(response.text)

    def _get_client_id(self, client):

        # If not formatted like a client ID, assume it's a client name and get the ID.
        if not re.match(r"[a-f,0-9]{32}", client):
            client = self.get_client_id(client)

        if not client:
            raise NotFoundException("%s not found." % client)

        return client

    # Authentication interfaces
    # =========================

    def refresh_auth(self, username=None, password=None, account=None):
        """
        Renew authentication token manually.
        Uses POST to /auth interface
        """
        jwt = self.get_authorization_bearer(username=username, password=password, account=account)
        self._headers["Authorization"] = "Bearer %s" % jwt

        self._auth_token = jwt
        self._last_auth = datetime.utcnow()

    def get_authorization_bearer(self, username=None, password=None, account=None):
        """
        Get authentication token.
        Uses POST to /auth interface

        return: Authentication JWT
        """
        body = {
            "user": username or self._username,
            "password": password or self._password
        }
        if account or self._account:
            body.update({
                "account_number": account or self._account
            })
        response = self._post(url.auth, body=body)

        self._check_response(response, 200)
        return self._create_response(response).get("jwt")

    # Client interfaces
    ###################

    @_auth
    def create_client(self, name, password):
        """
        Create a new client
        Uses the POST to /clients interface
        Args:
            name: (str) Name of client
            password: (str) password of client
        Returns: (str) ID of the newly created client.
        """
        body = {
            "name": name,
            "password": password
        }
        response = self._post(url.clients, body=body)
        self._check_response(response, 201)
        return self._create_response(response).get("client_id")

    @_auth
    def get_client_count(self):
        """
        Get number of clients
        Uses HEAD to /clients interface

        Returns: (int) Number of clients
        """
        response = self._head(url.clients)
        self._check_response(response, 200)
        return int(response.headers.get("x-client-count", -1))

    @_auth
    def get_clients(self, name=None, name_only=None, all_enrolled=None):
        """
        Get list of clients.
        Uses GET to /clients interface.

        return: (list) List of clients.
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
    def get_client_id(self, client):
        """
        Get a client's ID
        Uses GET to /clients?name=<client> interface
        args:
            client: (str) Client's name

        return: (str) Client id
        """

        params = {
            "name": client
        }

        response = self._get(url.clients, params=params)
        self._check_response(response, 200)
        return self._create_response(response).get("client_id")

    @_auth
    def get_client_info(self, client):
        """
        Get client info
        Uses GET to /clients/<client> interface
        args:
            client: (str) Client's ID

        return (dict) Client dictionary
        """
        client = self._get_client_id(client)
        response = self._get(url.clients_id.format(id=client))
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def validate_password(self, client, password):
        """
        Validate client's password
        Uses PUT to /clients/<client> interface
        Args:
            client: (str) Client's ID
            password: (str) Client's Password
        """

        client = self._get_client_id(client)
        body = {
            "action": "validate_password",
            "auth_password": password
        }

        response = self._put(url.clients_id.format(id=client), body=body)
        self._check_response(response, 200)

    @_auth
    def validate_pin(self, client, pin):
        """
        Validate client's PIN
        Uses PUT to /clients/<client> interface
        Args:
            client: (str) Client's ID
            pin: (str) Client's PIN
        """

        client = self._get_client_id(client)
        body = {
            "action": "validate_pin",
            "current_pin": pin
        }

        response = self._put(url.clients_id.format(id=client), body=body)
        self._check_response(response, 200)

    @_auth
    def update_client_info(self,
                           client,
                           reason=None,
                           pin=None,
                           current_pin=None,
                           verification_speed=None,
                           row_doubling=None,
                           password=None,
                           bypass_enabled=None,
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
        args:
            client: (str) Client's ID
            See API documentation for other arguments
        """
        client = self._get_client_id(client)

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
        if bypass_enabled is not None:
            body["bypass_enabled"] = bypass_enabled
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
    def remove_client(self, client):
        """
        Remove a client
        Uses DELETE to /clients/<client> interface
        args:
            client: (str) Client's ID
        """
        client = self._get_client_id(client)
        response = self._delete(url.clients_id.format(id=client))
        self._check_response(response, 204)

    # Enrollment interfaces
    #######################

    @_auth
    def get_enrollment_resource(self, client, audio=False):
        """
        Get Client Enrollment Data.
        Uses GET to /enrollments/<client> interface
        args:
            client: (str) Client's ID
            audio: (boolean) If True then the enrollment audio is returned.
        return: (dict)
        """
        client = self._get_client_id(client)
        params = {}
        if audio:
            params["audio"] = True

        response = self._get(url.enrollments_id.format(id=client), params=params)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def start_enrollment(
            self,
            name,
            pin,
            phone_number=None
    ):
        """
        Start Client Enrollment.
        Uses the POST to /enrollments interface

        args:
            client: (str) Client's Name
            pin: (str) Client's PIN. 4 digit string
            phone_number (str) Phone number to call.
        return: (dict) Enrollment record with prompts
        """
        data = {
            "name": name,
            "pin": pin
        }

        if phone_number:
            data["phone_number"] = phone_number

        response = self._post(url.enrollments, body=data)
        self._check_response(response, 201)
        return self._create_response(response)

    @_auth
    def upload_enrollment_resource(
        self,
        enrollment_id,
        audio_file=None,
        recording_start=None,
    ):
        """
        Upload Enrollment Data.
        Uses PUT to /enrollments/<enrollment_id> interface

        args:
            enrollment_id: (str) Enrollment's ID
            audio_file: (str) Path to the audio file of the recorded words. Not required for phone enrollments.
            word_boundaries: (list) Word boundaries for recorded words:
                ex. [
                        {"start": 0, "end": 1741, "phrase": "Nashville"},
                        {"start": 1741, "end": 3505, "phrase": "Nashville"},
                        ...
                    ]
            recording_start: (str) String representation of the time the recording was started. Only needed for phone
                                   enrollments. ex. 2016-06-16 17:27:13.984352

        """
        if recording_start:
            # Phone enrollment
            files = {
                "recording_start": recording_start,
            }
        else:
            # File upload
            files = {
                "file": os.path.basename(audio_file),
                os.path.basename(audio_file): open(audio_file, 'rb')
            }

        response = self._put(url.enrollments_id.format(id=enrollment_id), files=files)
        self._check_response(response, 202)

    # Event interfaces
    # ================

    @_auth
    def get_client_events(self, client):
        """
        Get a client's events
        Uses GET to /events/clients/<client> interface
        Args:
            client: Client's ID

        Returns: (list) Events
        """
        # TODO Add paging to this
        client = self._get_client_id(client)
        response = self._get(url.events_clients_id.format(id=client))
        self._check_response(response, 200)
        return self._create_response(response).get("events")

    @_auth
    def get_all_client_events(self):
        """
        Get all client events
        Uses GET to /events/clients interface

        Returns: (list) Events
        """
        # TODO Add paging to this
        response = self._get(url.events_clients)
        self._check_response(response, 200)
        return self._create_response(response).get("events")

    @_auth
    def get_all_login_events(self):
        """
        Get all login events
        Uses GET to /events/login interface

        Returns: (list) Events
        """
        # TODO Add paging to this
        response = self._get(url.events_logins)
        return self._create_response(response).get("events")

    @_auth
    def get_all_system_events(self):
        """
        Get all system events
        Uses GET to /events/system interface

        Returns: (list) Events
        """
        # TODO Add paging to this
        response = self._get(url.events_system)
        self._check_response(response, 200)
        return self._create_response(response).get("events")

    # General interfaces
    # ==================
    def about(self):
        """
        Get server info.
        Uses GET to /about interface

        return: (dict) Server info
        """
        response = self._get(url.about)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def status(self):
        """
        Get server status
        Uses GET to /status interface

        returns: (dict) Server status
        """
        response = self._get(url.status)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def warnings(self):
        """
        Get server system warnings
        Uses GET to /status/warnings

        returns: (dict) Server messages and warnings
        """
        response = self._get(url.status_warnings)
        self._check_response(response, 200)
        return self._create_response(response)

    # System Modules interfaces
    ###########################

    @_auth
    def get_module_settings(self):
        """
        Get Module settings.
        Uses GET to /settings/modules interface
        return: (dict) module settings
        """
        response = self._get(url.settings_modules)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def set_module_settings(self,
                            ldap_enable=None,
                            phone_enable=None,
                            windows_enable=None,
                            email_enable=None,
                            mode_audiopin_enable=None,
                            mode_audiopass_enable=None,
                            mode_default=None):
        """
        Set Module settings.
        Uses PUT to /settings/modules interface
        Args:
            See API documentation for argument details

        """
        body = {
            "auth_password": self._password
        }
        if ldap_enable:
            body["ldap_enable"] = ldap_enable
        if phone_enable:
            body["phone_enable"] = phone_enable
        if windows_enable:
            body["windows_enable"] = windows_enable
        if email_enable:
            body["email_enable"] = email_enable
        if mode_audiopin_enable:
            body["mode_audiopin_enable"] = mode_audiopin_enable
        if mode_audiopass_enable:
            body["mode_audiopass_enable"] = mode_audiopass_enable
        if mode_default:
            body["mode_default"] = mode_default

        response = self._put(url.settings_modules, body=body)
        self._check_response(response, 200)

    @_auth
    def reset_module_settings(self):
        """
        Resets the module settings back to default.
        Uses DELETE to /settings/modules interface
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
    def create_event_report(self, start_date, end_date, type="system"):
        """
        Create a report for all client events or all system events
        Uses GET to /reports/events/{clients,system} interface
        Args:
            start_date: (datetime) Start time for report generation
            end_date: (datetime) End time for report generation
            type: (str) Type of event report to create. "system" or "clients"

        Returns: (list) List of events in the input range

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
    def create_verification_report(self, start_date, end_date):
        """
        Create a report for all verifications
        Uses GET to /reports/verifications interface
        Args:
            start_date: (datetime) Start time for report generation
            end_date: (datetime) End time for report generation

        Returns: (str) CSV formatted report string

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
    def get_system_settings(self):
        """
        Get system settings.
        Uses GET to /settings/system interface
        return: (dict) System settings
        """
        response = self._get(url.settings_system)
        self._check_response(response, 200)
        return self._create_response(response)

    @_auth
    def set_system_settings(self, data):
        """
        Set system settings.
        Uses PUT to /settings/system interface
        args:
            data: (dict) settings and values to set
        """
        data["auth_password"] = self._password

        response = self._put(url.settings_system, body=data)
        self._check_response(response, 200)

    @_auth
    def reset_system_settings(self):
        """
        Resets the system settings back to default.
        Uses DELETE to /settings/system interface
        """
        data = {
            "auth_password": self._password
        }

        response = self._delete(url.settings_system, body=data)
        self._check_response(response, 204)

    # Verification interfaces
    #########################

    @_auth
    def start_verification(
        self,
        client,
        mode=None,
        verification_speed=None,
        row_doubling="off",
        phone_number=None,
    ):
        """
        Start a verification.
        Uses POST to /verifications interface

        args:
            client: (str) Client's Name
            verification_speed: (int) Allowed values: 0, 25, 50, 75, 100
            row_doubling (str) Allowed values: "off", "train", "on"
            phone_number (str) Phone number to call.

        returns: (dict) verification record with animation.
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
    def upload_verification_resource(
            self,
            resource,
            word_boundaries,
            recording_start=None,
            audio_file=None,
            bypass=False,
            bypass_pin=None,
            bypass_code=None,
            ):
        """
        Upload verification data.
        Uses PUT to /verfications/<resource> interface

        args:
            resource: (str) Verification ID
            word_boundaries: (list) Word boundaries for recorded words:
                ex. [
                        275.558, 1928.548, 3581.672, 5234.646, 6887.727]
                        ...
                    ]
            recording_start: (str) String representation of the time the recording was started. Only needed for phone
                                   verifications. ex. 2016-06-16 17:27:13.984352
            audio_file: (str) Path to the audio file of the recorded words. Not required for phone verifications.
            bypass: (boolean) True if using a bypass code or pin to verify
            bypass_pin: (str) Client's PIN if this is a bypass
            bypass_code: (str) Client's bypass code if this is a bypass

        """
        files = {
            "word_boundaries": json.dumps(word_boundaries)
        }
        if audio_file:
            files[os.path.basename(audio_file)] = open(audio_file, 'rb')
            files["file"] = os.path.basename(audio_file)
        elif bypass:
            files["bypass"] = True
            files["bypass_code"] = bypass_code
            files["pin"] = bypass_pin
        elif recording_start:
            files["recording_start"] = recording_start
        response = self._put(url.verifications_id.format(id=resource), files=files)
        self._check_response(response, 202)
        return self._create_response(response)

    @_auth
    def cancel_verification_resource(self, resource, reason=None):
        """
        Cancels a started verification
        Uses PUT to /verifications/<resource> interface
        args:
            resource: (str) Verification ID
            reason: (str) Reason for cancelling the verification
        """

        data = {
            "cancel": True,
            "cancel_reason": reason
        }

        response = self._put(url.verifications_id.format(id=resource), body=data)
        self._check_response(response, 202)

    @_auth
    def remove_verification_resource(self, resource):
        """
        Remove verification
        Uses DELETE to /verifications/<resource> interface
        args:
            resource: (str) Verification ID
        """
        response = self._delete(url.verifications_id.format(id=resource))
        self._check_response(response, 204)

    @_auth
    def get_verifications_count(self):
        """
        Get Verification Count.
        Uses HEAD to /verifications interface
        return: (int) Number of verifications
        """
        response = self._head(url.verifications)
        self._check_response(response, 200)
        return int(response.headers.get('x-verification-count', -1))

    @_auth
    def get_verifications(self, limit=10):
        """
        Get list of verifications.
        Uses GET to /verifications interface
        return: (list) verification list
        """
        # TODO add arguments for paging and stuff
        params = {}
        params["limit"] = limit

        response = self._get(url.verifications, params=params)
        self._check_response(response, 200)
        return self._create_response(response).get("verifications")

    @_auth
    def get_verification_resource(self, resource, audio=False):
        """
        Get Verification Resource.
        Uses GET to /verifications/<resource> interface
        args:
            resource: (str) Verification ID
            audio: (boolean) If True, audio data associated with verification will be returned.
        return: (dict) Verification data
        """
        params = {}
        if audio:
            params["audio"] = True

        response = self._get(url.verifications_id.format(id=resource), params=params)
        self._check_response(response, 200)
        return self._create_response(response)