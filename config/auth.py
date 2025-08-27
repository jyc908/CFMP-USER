from rest_framework.authentication import BaseAuthentication
import jwt
from rest_framework.exceptions import AuthenticationFailed
from jwt import exceptions
from django.conf import settings

class JwtQueryAuthentication(BaseAuthentication):
    
    def authenticate(self, request):
        token = request.query_params.get('token')
        salt = settings.SECRET_KEY
        try:
            payload = jwt.decode(token, salt, True)
        except exceptions.ExpiredSignatureError:
            raise AuthenticationFailed({'code':1003, 'error':"token已失效"})
        except jwt.DecodeError:
            raise AuthenticationFailed({'code':1003, 'error':"token认证失败"})
        except jwt.InvalidTokenError:
            raise AuthenticationFailed({'code':1003, 'error':"非法的token"})

        return (payload,token)