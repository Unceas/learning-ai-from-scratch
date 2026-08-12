"""Authentication module using streamlit-authenticator for user login and access control."""

import os
from dotenv import load_dotenv
import streamlit_authenticator as stauth

load_dotenv()

USERS = {
    "ayush": {
        "name": "Ayush",
        "password": os.getenv("AUTH_AYUSH_PASSWORD", "change-this-password")
    }
}


def create_authenticator():
    """Build and return a configured streamlit-authenticator instance."""
    credentials = {
        "usernames": {}
    }

    passwords_to_hash = [user["password"] for user in USERS.values()]
    try:
        hashed_passwords = stauth.Hasher(passwords_to_hash).generate()
    except Exception:
        hashed_passwords = passwords_to_hash

    for i, (username, user) in enumerate(USERS.items()):
        credentials["usernames"][username] = {
            "name": user["name"],
            "password": hashed_passwords[i] if i < len(hashed_passwords) else user["password"]
        }

    cookie_secret = os.getenv("AUTH_COOKIE_SECRET", "change-this-secret-key-12345")

    return stauth.Authenticate(
        credentials,
        "ai_research_assistant",
        cookie_secret,
        cookie_expiry_days=1
    )
