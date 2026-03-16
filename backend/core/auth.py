import os
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

class ApiKeyAuthentication(BaseAuthentication):
    """
    Demo API-key auth:
    - Set API_KEYS="key1,key2" in env
    - Client sends header: X-API-Key: <key>
    """
    header_name = "HTTP_X_API_KEY"

    def authenticate(self, request):
        raw = request.META.get(self.header_name)
        if not raw:
            raise AuthenticationFailed("Missing X-API-Key header")

        allowed = os.getenv("API_KEYS", "")
        allowed_keys = {k.strip() for k in allowed.split(",") if k.strip()}

        if raw not in allowed_keys:
            raise AuthenticationFailed("Invalid API key")

        # Return (user, auth) — demo: no user model
        return (None, raw)