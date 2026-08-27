from django.conf import settings
from videos.services.storage.base_storage import BaseStorage
from videos.services.storage.local_storage import LocalStorage
from videos.services.storage.s3_storage import S3Storage

STORAGE_REGISTRY = {
    'local':      LocalStorage,
    'test':       LocalStorage,
    'stage':      S3Storage,
    'production': S3Storage,
}

def get_storage() -> BaseStorage:
    #env = settings.ENVIRONMENTS
    env = getattr(settings, 'ENVIRONMENTS', 'stage')
    # 🔍 AJOUTE CE LOG DE DÉBOGAGE
    print(f"DEBUG STORAGE: ENVIRONMENTS = '{env}' | STORAGE CLASS = '{STORAGE_REGISTRY.get(env)}'")
    try:
        storage_class = STORAGE_REGISTRY[env]
    except KeyError:
        raise ValueError(f"Unknown environment storage registry mapping: {env}")
    return storage_class()
