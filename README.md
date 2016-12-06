[![Build Status](https://travis-ci.org/KnuVerse/knuverse-sdk-python.png?branch=master)](https://travis-ci.org/KnuVerse/knuverse-sdk-python)
[![PyPI](https://img.shields.io/pypi/v/knuverse.svg)](https://pypi.python.org/pypi/knuverse)
[![Documentation Status](https://readthedocs.org/projects/knuverse-sdk-python/badge/?version=latest)](http://knuverse-sdk-python.readthedocs.io/en/latest/?badge=latest)

# knuverse-sdk-python

This project is a Python SDK that allows developers to create apps that use Knuverse's Cloud APIs.

Documentation for the API can be found [here](https://cloud.knuverse.com/docs/) <br />

Documentation for the SDK can be found [here](https://knuverse-sdk-python.readthedocs.io/en/latest/?) <br />

Quick Start
-----------
First, install the knuverse-sdk:

```sh
$ pip install knuverse
```
Then, in a Python file:

```python
from knuverse.knufactor import Knufactor

api = Knufactor(
    <api_key>,
    <secret>
)
for client in api.client_list():
    print "%s: %s" % (client.get("name"), client.get("state"))
```

Notes
-----
A minimum python version of 2.7.9 is required to work with our version of TLS(>v1.1)
