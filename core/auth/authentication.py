from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from db.models import UserSession


class SessionJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        jwt_auth = JWTAuthentication()
        auth_result = jwt_auth.authenticate(request)

        if not auth_result:
            return None

        user, token = auth_result
        raw_token = request.headers.get("Authorization").split(" ")[1]

        session = UserSession.objects.filter(
            user=user,
            session_token=raw_token,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()

        if not session:
            raise AuthenticationFailed("Session expired or logged out")

        request.session = session
        return user, token
