"""Short-lived installation parameters encrypted using the Console application key."""
import base64
import hashlib
import json
from django.conf import settings
from cryptography.fernet import Fernet


def cipher():
    key = hashlib.sha256((settings.SECRET_KEY + ":delivery-install").encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def seal(environment):
    return cipher().encrypt(json.dumps(environment).encode()).decode()


def open_environment(value):
    return json.loads(cipher().decrypt(value.encode())) if value else {}
