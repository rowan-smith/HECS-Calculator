import os
import secrets

SECRET_KEY = os.urandom(32)


class ApplicationConfig(object):
    WTF_CSRF_ENABLED = True
    CSRF_ENABLED = True

    if secrets:
        WTF_CSRF_SECRET_KEY = secrets.token_hex()
