import utils

def test_verify_audiopass_success(sdk):
    """
    Test a successful audiopass verification of an enrolled user
    """
    utils.enroll_without_exception(sdk, "bob", "1235")
    result = utils.verify_audiopass(sdk, "bob")
    assert result == 'Verified'


def test_verify_audiopass_single_error(sdk):
    """
    Test an audiopass verification with a single word error.
    """

    utils.enroll_without_exception(sdk, "bob", "1235")
    result = utils.verify_audiopass(sdk, "bob", num_words_wrong=1)
    assert result == 'Single word error'


def test_verify_audiopass_multiple_error(sdk):
    """
    Test an audiopass verification with multiple word errors
    """

    utils.enroll_without_exception(sdk, "bob", "1235")
    result = utils.verify_audiopass(sdk, "bob", num_words_wrong=4)
    assert result == 'Multiple word errors'
