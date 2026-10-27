#!/usr/bin/env python3
"""A realistic crash: a service looked for a key that was never in config."""

config = {
    "db_host": "localhost",
    "users": {"alice": {"email": "alice@example.com"}},
}

user_id = "bob"
user = config["users"][user_id]
print(user["email"])
