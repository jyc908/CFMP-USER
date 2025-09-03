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
        # 首先尝试从查询参数获取UUID（兼容前端当前实现）
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        user_uuid = query_params.get('uuid', [None])[0]

        # 如果查询参数中没有，再尝试从headers获取（保持向后兼容）
        if not user_uuid:
            headers = dict(scope.get('headers', []))
            user_uuid = headers.get(b'uuid', None)
            # 处理bytes类型
            if isinstance(user_uuid, bytes):
                user_uuid = user_uuid.decode('utf-8')

        print(f"WebSocket connection attempt with UUID: {user_uuid}")  # 添加日志

        if user_uuid:
            user = await self.get_user_by_uuid(user_uuid)
            print(f"User lookup result: {user}")  # 添加日志
            scope['user'] = user
        else:
            scope['user'] = AnonymousUser()
            print("No UUID provided, setting AnonymousUser")  # 添加日志

        return await self.app(scope, receive, send)
    @database_sync_to_async
    def get_user_by_uuid(self, user_uuid):
        """
        根据UUID获取用户
        """
        if not user_uuid:
            return AnonymousUser()
        try:
            # 使用filter().first()而不是get()，避免抛出异常
            return User.objects.filter(user_id=user_uuid).first() or AnonymousUser()
        except Exception as e:
            print("User lookup error:", e)
            return AnonymousUser()

    @database_sync_to_async
    def get_user(self, token):
        """
        保留原有的token认证方法，以保持向后兼容
        """
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