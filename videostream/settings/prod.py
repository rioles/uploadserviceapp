# videostream/settings/prod.py

# pas de load_dotenv — ESO injecte les variables via Kubernetes
from .base import *

DEBUG = False
DATABASES['default']['CONN_MAX_AGE'] = 600
