import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

def get_env(key, default=None, required=False):
    value = os.environ.get(key, default)
    if required and not value:
        raise ValueError(f"Variable manquante : {key}")
    return value

# charge le bon fichier .env selon l'environnement
ENVIRONMENT   = get_env('ENVIRONMENT', default='local')
AWS_S3_BUCKET = get_env('AWS_S3_BUCKET', default='videostream-chunks')
AWS_REGION    = get_env('AWS_REGION', default='eu-west-1')
ENV = os.environ.get('DJANGO_ENV', 'dev')



  # charge .env.dev ou .env.prod

ENV = os.environ.get('DJANGO_ENV', 'dev')
env_file = f'.env.{ENV}'
if Path(env_file).exists():
    load_dotenv(dotenv_path=env_file)
#load_dotenv(dotenv_path=f'.env.{ENV}')

from videostream.telemetry import setup_tracing
tracer = setup_tracing()

# 4. Fichiers Statiques et Média
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

SECRET_KEY = get_env('SECRET_KEY', required=True)
DEBUG       = get_env('DEBUG', default='False') == 'True'

ALLOWED_HOSTS = get_env('ALLOWED_HOSTS', default='*').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'videos',
    'corsheaders',
]

MIDDLEWARE = [
	'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'videostream.urls'
WSGI_APPLICATION = 'videostream.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]



# Database
DATABASES = {
    'default': {
        'ENGINE':       'django.db.backends.postgresql',
        'NAME':         get_env('DB_NAME',     required=True),
        'USER':         get_env('DB_USER',     required=True),
        'PASSWORD':     get_env('DB_PASSWORD', required=True),
        'HOST':         get_env('DB_HOST',     required=True),
        'PORT':         get_env('DB_PORT',     default='5432'),
        'CONN_MAX_AGE': int(get_env('DB_CONN_MAX_AGE', default='60')),
        'OPTIONS': {
            'connect_timeout': 5,
            'sslmode': get_env('DB_SSL_MODE', default='require'),
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True
STATIC_URL    = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 1. Récupération des morceaux depuis l'environnement (Kubernetes / .env)
REDIS_HOST = get_env('REDIS_HOST', 'localhost')
REDIS_PORT = get_env('REDIS_PORT', '6379')
REDIS_DB = get_env('REDIS_DB', '0')
REDIS_PASSWORD = get_env('REDIS_PASSWORD', '')
REDIS_SSL = get_env('REDIS_SSL', 'False') == 'True'

if REDIS_PASSWORD:
    scheme = "rediss" if REDIS_SSL else "redis"
    ssl_param = "?ssl_cert_reqs=none" if REDIS_SSL else ""
    REDIS_URL = f"{scheme}://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}{ssl_param}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

# Redis — database 15
#REDIS_URLs = get_env('REDIS_URL', default='redis://localhost:6379/15')

# .env
#REDIS_URL='redis://:gfr@master.streaming-platform-redis.jc0kvk.use1.cache.amazonaws.com:6379/0'




AWS_ACCESS_KEY_ID=get_env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY=get_env('AWS_SECRET_ACCESS_KEY')
AWS_DEFAULT_REGION=get_env('AWS_DEFAULT_REGION')
DYNAMODB_CHUNK_TABLE=get_env('DYNAMODB_CHUNK_TABLE')

ENVIRONMENTS = get_env('ENVIRONMENTS', default='stage')

# Celery
CELERY_BROKER_URL        = REDIS_URL
CELERY_RESULT_BACKEND    = REDIS_URL
CELERY_TASK_SERIALIZER   = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT    = ['json']
CELERY_TIMEZONE          = 'UTC'

INSTALLED_APPS += ['django_celery_results']
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

# ──────────────────────────────────────────
# Keycloak
# ──────────────────────────────────────────
KEYCLOAK_CONFIG = {
    "SERVER_URL":    get_env('KEYCLOAK_URL',           required=True),
    "REALM":         get_env('KEYCLOAK_REALM',         required=True),
    "CLIENT_ID":     get_env('KEYCLOAK_CLIENT_ID',     required=True),
    "CLIENT_SECRET": get_env('KEYCLOAK_CLIENT_SECRET', required=False),
    "JWKS_URI":      get_env('KEYCLOAK_JWK_SET_URI',   required=True),
    "ALGORITHMS":    ["RS256"],
    "VERIFY_EXPIRY": True,
}

# ──────────────────────────────────────────
# DRF
# ──────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.KeycloakAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

TRANSCODE_QUEUE_URL = os.environ.get(
    "TRANSCODE_QUEUE_URL",
    "https://sqs.us-east-1.amazonaws.com/868480224885/video-streaming-cluster-transcode-queue"
)

# ──────────────────────────────────────────
# Configuration CORS (django-cors-headers)
# ──────────────────────────────────────────

# Origins autorisées (Next.js en local + votre domaine Frontend s'il y en a un)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Si vous voulez autoriser dynamiquement l'URL ngrok ou le Gateway en dev :
# CORS_ALLOW_ALL_ORIGINS = True  # A utiliser uniquement pour le debug rapide

# Indispensable pour la requête Preflight (OPTIONS) de Next.js qui envoie le Token Keycloak
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# Méthodes HTTP autorisées
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_CREDENTIALS = True
# Empêche Django d'envoyer un HTTP 301 Redirect si le slash manque
APPEND_SLASH = False
