"""
Development settings for serpent-mail project.
"""

from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-0-s3nzb$^1yk(!-_e553a!&b(74^d1rg()vziok)h33!oz)mhv"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

# django-vite settings
DJANGO_VITE_DEV_MODE = DEBUG  # follow Django's dev mode
