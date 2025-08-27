from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from user.models import User
import jwt
from django.conf import settings
class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        scope['user'] = await self.get_user(token)
        return await self.app(scope, receive, send)


    @database_sync_to_async
    def get_user(self, token):
        if not token:
            return AnonymousUser()
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if not user_id:
                return AnonymousUser()
            return User.objects.get(pk=user_id)
        except Exception as e:
            print("Token decode error:", e)
            return AnonymousUser()