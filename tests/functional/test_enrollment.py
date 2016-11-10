import utils
import pytest
import knuverse.exceptions as kex

def test_enroll_success(sdk):
    """
    Test the successful enrollment of a user.
    """

    utils.unenroll_without_exception(sdk, "bob")
    utils.enroll_user(sdk, "bob", "1235")
    client_info = sdk.client_info("bob")
    assert client_info['state'] == 'enrolled'


def test_enroll_already_enrolled(sdk):
    """
    Test the enrollment of a user who is already enrolled.
    """

    utils.enroll_without_exception(sdk, "bob", "2358")

    with pytest.raises(kex.BadRequestException):
        utils.enroll_user(sdk, "bob", "1235")
