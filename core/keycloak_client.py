import logging
from functools import lru_cache

import jwt
from jwt import PyJWKClient
from keycloak import KeycloakOpenID
from django.conf import settings

logger = logging.getLogger(__name__)


class KeycloakClient:

    def __init__(self):
        config = settings.KEYCLOAK_CONFIG

        self.client_id     = config["CLIENT_ID"]
        self.algorithms    = config["ALGORITHMS"]
        self.audience      = config["CLIENT_ID"]   # "upload-service" → matche "aud" du token ✅
        self.verify_expiry = config["VERIFY_EXPIRY"]

        self.oidc_client = KeycloakOpenID(
            server_url=config["SERVER_URL"],
            realm_name=config["REALM"],
            client_id=config["CLIENT_ID"],
            client_secret_key=config["CLIENT_SECRET"],
        )

        self._jwks_client = PyJWKClient(
            config["JWKS_URI"],
            cache_keys=True
        )
        logger.info("KeycloakClient initialisé — JWKS : %s", config["JWKS_URI"])

    def decode_token(self, token: str) -> dict:
        signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=self.algorithms,
            audience=self.audience,
            options={"verify_exp": self.verify_expiry},
        )


@lru_cache(maxsize=1)
def get_keycloak_client() -> KeycloakClient:
    return KeycloakClient()
