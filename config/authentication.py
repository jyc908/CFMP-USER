from rest_framework.authentication import BaseAuthentication
import jwt
from rest_framework.exceptions import AuthenticationFailed
from jwt import exceptions
from django.conf import settings
from user.models import User

class JWTAuthentication(BaseAuthentication):
    """
    JWT认证类，用于处理请求头中的token认证
    """
    def authenticate(self, request):
        """
        从请求头中获取token并验证
        """
        # 获取请求头中的Authorization
        auth = request.META.get('HTTP_AUTHORIZATION', '')

        # 判断是否存在token
        if not auth:
            return None

        # 检查格式是否正确 (Bearer token)
        auth_parts = auth.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != 'bearer':
            return None

        # 获取token
        token = auth_parts[1]

        # 解析token
        try:
            # 使用settings中的密钥解析token
            salt = settings.SECRET_KEY
            payload = jwt.decode(token, salt, algorithms=["HS256"])

            # 获取用户信息
            user_id = payload.get('user_id')
            if not user_id:
                raise AuthenticationFailed({'code': 1003, 'error': "无效的token载荷"})

            try:
                user = User.objects.get(user_id=user_id)
                # 添加Django Auth属性
                user.is_authenticated = True
            except User.DoesNotExist:
                raise AuthenticationFailed({'code': 1004, 'error': "用户不存在"})

            return (user, token)

        except exceptions.ExpiredSignatureError:
            raise AuthenticationFailed({'code': 1003, 'error': "token已过期"})
        except jwt.DecodeError:
            raise AuthenticationFailed({'code': 1003, 'error': "token认证失败"})
        except jwt.InvalidTokenError:
            raise AuthenticationFailed({'code': 1003, 'error': "非法的token"})
