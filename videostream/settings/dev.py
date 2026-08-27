# videostream/settings/dev.py

from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.dev')

from .base import *

DEBUG = True
DATABASES['default']['OPTIONS']['sslmode'] = 'disable'
DATABASES['default']['CONN_MAX_AGE'] = 0
