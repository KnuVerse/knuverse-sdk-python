# knuverse-sdk-python

This project is a Python SDK that allows developers to create apps that use Knuverse's Cloud APIs.

Documentation for the API can be found [here](https://cloud.knuverse.com/docs/) <br />
Documentation for the SDK can be found [here](https://knuverse.github.io/knuverse-sdk-python/build/html/index.html).

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
    "https://cloud.knuverse.com",
    username="<username>",
    password="<password>",
    account="<account_id>"
)
for client in api.get_clients():
    print "%s: %s" % (client.get("name"), client.get("state"))
```

Notes
-----
A minimum python version of 2.7.9 is required to work with our version of TLS(>v1.1)