# knuverse-sdk-python

This project is a Python SDK that allows developers to create apps that use Knuverse's Cloud APIs.
You can find the documentation at https://cloud.knuverse.com/docs/

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
    print "%s: %s" % (client.get("name"), client.get("state")),
```