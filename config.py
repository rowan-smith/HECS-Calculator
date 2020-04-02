import os

SECRET_KEY = os.urandom(32)


class ApplicationConfig(object):
    WTF_CSRF_ENABLED = True
    CSRF_ENABLED = True

