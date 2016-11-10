"""
Copyright 2014-2015, Intellisis
All rights reserved.

Stuff magically picked up by py.test runs.
"""
import os
import pytest
import knuverse.knufactor as kf

def pytest_addoption(parser):
    """
    Command line options for py.test invocations of audiopin functional tests.
    """
    # Test settings
    parser.addoption(
        '--api-key',
        action='store',
        default=os.environ["KV_APIKEY"]
    )
    parser.addoption(
        '--secret',
        action='store',
        default=os.environ["KV_SECRET"]
    )


@pytest.fixture(scope='session')
def sdk(request):
    """Returns an instance of the sdk to use for the interface"""

    return kf.Knufactor(
        request.config.getoption('--api-key'),
        request.config.getoption('--secret'),
    )
