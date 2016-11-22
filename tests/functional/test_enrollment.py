import utils
import pytest
import random
import knuverse.exceptions as kex

def test_enroll_success(sdk):
    """
    Test the successful enrollment of a user.
    """
    name = utils.random_name()
    utils.enroll_user(sdk, name, "1235")
    client_info = sdk.client_info(name)
    assert client_info['state'] == 'enrolled'


def test_enroll_already_enrolled(sdk):
    """
    Test the enrollment of a user who is already enrolled.
    """

    name = utils.random_name()
    utils.enroll_without_exception(sdk, name, "2358")
    with pytest.raises(kex.BadRequestException):
        utils.enroll_user(sdk, name, "1235")
