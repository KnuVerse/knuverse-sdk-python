"""
Copyright 2014, Intellisis
All rights reserved.
"""

from . import knuverse

class Knufactor(knuverse.Knuverse):
    def __init__(self,
                 apikey=None,
                 secret=None,
                 email=None,
                 password=None,
                 server="https://cloud.knuverse.com",
                 base_uri="/knufactor/api/v1/"):

        super(Knufactor, self).__init__(
            apikey=apikey,
            secret=secret,
            email=email,
            password=password,
            server=server,
            base_uri=base_uri
        )


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
