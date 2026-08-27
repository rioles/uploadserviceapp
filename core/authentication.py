import logging
import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .keycloak_client import get_keycloak_client

logger = logging.getLogger(__name__)


class KeycloakUser:
    def __init__(self, payload: dict):
        self.payload          = payload
        self.id               = payload.get("sub")
        self.username         = payload.get("preferred_username", "")
        self.email            = payload.get("email", "")
        self.is_authenticated = True
        self.is_active        = True
        self.is_anonymous     = False

    @property
    def roles(self) -> list:
        return self.payload.get("realm_access", {}).get("roles", [])

    @property
    def client_roles(self) -> list:
        client_id = get_keycloak_client().client_id
        return (
            self.payload
            .get("resource_access", {})
            .get(client_id, {})
            .get("roles", [])
        )

    def has_role(self, role: str) -> bool:
        return role in self.roles or role in self.client_roles

    def __str__(self):
        return self.username


class KeycloakAuthentication(BaseAuthentication):

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            logger.debug("[KEYCLOAK] Pas de header Authorization Bearer — skip.")
            return None

        token = auth_header.split(" ", 1)[1].strip()

        # Logger les 20 premiers chars pour identifier le token sans l'exposer
        logger.debug("[KEYCLOAK] Token reçu : %s...", token[:20])

        try:
            payload = get_keycloak_client().decode_token(token)
            logger.debug(
                "[KEYCLOAK] Token valide — sub: %s, aud: %s",
                payload.get("sub"),
                payload.get("aud"),
            )

        except jwt.ExpiredSignatureError:
            logger.warning("[KEYCLOAK] Token expiré.")
            raise AuthenticationFailed("Token expiré.")

        except jwt.InvalidAudienceError as e:
            logger.warning(
                "[KEYCLOAK] Audience invalide — aud dans token: %s | erreur: %s",
                self._peek_aud(token),
                str(e),
            )
            raise AuthenticationFailed("Audience invalide.")

        except jwt.InvalidTokenError as e:
            logger.warning("[KEYCLOAK] Token JWT invalide — %s", str(e))
            raise AuthenticationFailed("Token invalide.")

        except Exception as e:
            logger.error("[KEYCLOAK] Erreur inattendue — %s : %s", type(e).__name__, str(e))
            raise AuthenticationFailed("Erreur d'authentification.")

        return (KeycloakUser(payload), token)

    def authenticate_header(self, request):
        return 'Bearer realm="videostream"'

    @staticmethod
    def _peek_aud(token: str) -> str:
        """
        Décode le payload JWT sans vérification pour logger l'audience réelle.
        Uniquement utilisé pour le debugging — ne pas utiliser pour l'auth.
        """
        try:
            unverified = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["RS256"],
            )
            return str(unverified.get("aud", "non trouvée"))
        except Exception:
            return "illisible"
