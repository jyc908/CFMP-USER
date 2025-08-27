import urllib3
import jwt
import datetime
from datetime import datetime, timedelta, timezone
from django.core.files.storage import default_storage
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend
from minio_storage import MinioMediaStorage
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.generics import RetrieveUpdateDestroyAPIView, ListCreateAPIView, get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from .serializers import UserSerializer, PublicUserSerializer, FollowSerializer, ChatLogSerializer, MessagesSerializer
from .models import User, Follow, ChatLog, Messages
from .serializers import UserSerializer, PublicUserSerializer
from .models import User
from .models import Captcha
from minio import Minio
from django.conf import settings
from jwt import exceptions
from django.core.mail import send_mail
import random
from config.authentication import JWTAuthentication
from product.models import Product
from product.serializers import ProductSerializer
from root.serializers import ComplaintSerializer
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from .throttling  import EmailRateThrottle
import random
# import redis

# Create your views here.
import re

from .pagination import StandardResultsSetPagination


def send_sms_code(to_email):
    # 生成邮箱验证码
    sms_code = '%06d' % random.randint(0, 999999)
    EMAIL_FROM = "3417934680@qq.com"  # 邮箱来自
    email_title = '邮箱激活'
    email_body = "您的邮箱注册验证码为：{0}, 该验证码有效时间为两分钟，请及时进行验证。".format(sms_code)
    send_status = send_mail(email_title, email_body, EMAIL_FROM, [to_email])
    if send_status != 0:
        # 存储验证码
        captcha = Captcha.objects.create(
            captcha=sms_code,
            email=to_email
        )
        captcha.save()
    return send_status

def varify_captcha(email,captcha):
    captchaObj = Captcha.objects.filter(email=email).last()
    if  not captchaObj:  # 验证码不存在
        return Response({
            "fail_code":"CAPTCHA_NOT_FOUND",
            "fail_msg":"验证码不存在"
        },status=status.HTTP_400_BAD_REQUEST)
    if captcha != captchaObj.captcha:
        return Response({
            "fail_code":"CAPTCHA_ERROR",
            "fail_msg":"验证码错误"
        },status=status.HTTP_400_BAD_REQUEST)
    if captchaObj.created_at < datetime.now(timezone.utc) - timedelta(minutes=2):  # 验证码有效时间2分钟
        return Response({
            "fail_code":"CAPTCHA_EXPIRED",
            "fail_msg":"验证码已过期"
        },status=status.HTTP_400_BAD_REQUEST)
    if captchaObj.is_used:  # 验证码已使用
        return Response({
            "fail_code":"CAPTCHA_ERROR",
            "fail_msg":"验证码错误"
        },status=status.HTTP_400_BAD_REQUEST)
    captchaObj.is_used = True
    captchaObj.save()
    return 0

class CaptchaView(APIView):
    throttle_classes  = [EmailRateThrottle]
    def post(self, request):
        email = request.data.get('email')
        scene = request.data.get('scene')
        if not all([email, scene]):
            return Response({
                "fail_code":"MISSING_PARAM",
                "fail_msg":"缺少参数"
            },status=status.HTTP_400_BAD_REQUEST)
        common_scene = {'register','login','forget'}
        need_token_scene = {'change_email','change_password'}
        need_user_check_scene = {'change_email','register'}
        user = User.objects.filter(email=email)
        if user.exists() and scene in need_user_check_scene:
            return Response({
                "fail_code": "USER_EXIST",
                "fail_msg": "用户已存在"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', email):
            return Response({
                "fail_code": "EMAIL_FORMAT_ERROR",
                "fail_msg": "邮箱格式错误"
            }, status=status.HTTP_400_BAD_REQUEST)

        if scene in common_scene:
            if send_sms_code(email) != 0:
                return Response({
                    "success":True,
                    "msg":"发送成功"
                })
            else:
                return Response({
                    "success":False,
                    "fail_msg":"发送失败"
                },status=status.HTTP_400_BAD_REQUEST)
        elif scene in need_token_scene:
            auth = request.META.get('HTTP_AUTHORIZATION', '')
            if not auth:
                print("not auth")
                return Response({
                    "success":False,
                    "fail_msg":"验证失败"
                },status=status.HTTP_400_BAD_REQUEST)
            JWTAuthentication.authenticate(self,request)
            if send_sms_code(email) != 0:
                return Response({
                    "success":True,
                    "msg":"发送成功"
                })
            else:
                return Response({
                    "success":False,
                    "fail_msg":"发送失败"
                },status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                "success":False,
                "fail_msg":"参数错误"
            },status=status.HTTP_400_BAD_REQUEST)
class RegisterView(APIView):

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        password_repeat = request.data.get('password_repeat')
        email = request.data.get('email')
        captcha = request.data.get('captcha')
        #print(username,password,password_repeat,email,captcha)
        if not all([username, password, password_repeat, email, captcha]):
            return Response({
                "fail_code":"MISSING_PARAM",
                "fail_msg":"缺少参数"
            },status=status.HTTP_400_BAD_REQUEST)

        if password != password_repeat:
            return Response({
                "fail_code":"PASSWORD_NOT_MATCH",
                "fail_msg":"密码不一致"
            },status=status.HTTP_400_BAD_REQUEST)

        #禁止空字符
        if ' ' in username:
            return Response({
                "fail_code":"USERNAME_CONTAINS_SPACE",
                "fail_msg":"用户名不能包含空字符"
            },status=status.HTTP_400_BAD_REQUEST)

        if ' ' in password:
            return Response({
                "fail_code":"PASSWORD_CONTAINS_SPACE",
                "fail_msg":"密码不能包含空字符"
            },status=status.HTTP_400_BAD_REQUEST)

        #密码复杂性检查（长度6-18，包含数字、字母、特殊字符中的2种）
        required_checks = [
            any(char.isdigit() for char in password),  # 包含数字
            any(char.isalpha() for char in password),  # 包含字母
            any(not char.isalnum() for char in password)  # 包含特殊字符
        ]
        if not (6 <= len(password) <= 18 and sum(required_checks) >= 2):
            return Response({
                "fail_code":"PASSWORD_COMPLEXITY",
                "fail_msg":"密码应满足:6-18位,包含数字、字母、特殊字符中的2种"
            },status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email)
        if user.exists():
            return Response({
                "fail_code":"USER_EXIST",
                "fail_msg":"用户已存在"
            },status=status.HTTP_400_BAD_REQUEST)

        #验证码检查
        if varify_captcha(email,captcha)!=0:
            return varify_captcha(email,captcha)
        #对密码加密
        password = make_password(password)
        print(password)
        #存入数据库
        user = User.objects.create(
            username=username,
            password=password,
            email=email
        )
        user.save()

        #返回user_id
        return Response({
            "success":True,
            "user_id":user.user_id
        })
import threading
class login_passwordView(APIView):
    authentication_classes = []
    _lock = threading.Lock()
    request_count = 0
    def post(self, request):
        #看看调用了几次api。貌似调用了两次，有点奇怪 :p
        with self._lock:
            print(f"one processing : {self.request_count}")
            current_count = type(self).request_count
            type(self).request_count = current_count + 1
        email = request.data.get('email')
        password = request.data.get('password')
        if not all([email, password]):
            return Response({
                "fail_code":"MISSING_PARAM",
                "fail_msg":"缺少参数"
            },status=status.HTTP_400_BAD_REQUEST)

        # user = authenticate(email=email, password=password)
        #密码已加密
        user = User.objects.filter(email=email)
        user = user.first()
        #检查user是否存在
        if not user:
            return Response({
                "fail_code":"USER_NOT_EXIST",
                "fail_msg" : "用户不存在"}, status=status.HTTP_400_BAD_REQUEST)

        if check_password(password,user.password)==False:
            return Response({
                "fail_code":"PASSWORD_ERROR",
                "fail_msg":"密码错误"
            },status=status.HTTP_400_BAD_REQUEST)
        #print(user)
        if user:
            salt = settings.SECRET_KEY
            headers = {
                'typ':'jwt',
                'alg':'HS256'
            }
            print(user.username)
            payload = {
                'user_id': user.user_id,
                'username': user.username,
                'exp':datetime.now(timezone.utc) + timedelta(days=3)  # 延长token有效期为60分钟
            }
            if user.status==1:
                return Response({
                    "success":False,
                    "fail_code":"BANNED",
                    "fail_msg":"用户已被封禁"
                },status=status.HTTP_401_UNAUTHORIZED)

            token = jwt.encode(payload = payload, key = salt, algorithm="HS256", headers=headers)
            url= None
            if user.avatar:
                url = user.avatar.url
            return Response({
                "success":True,
                "access_token":token,
                "username":user.username,
                "user_id":user.user_id,
                "avatar":url,
                "privilege":user.privilege
            })

        try:
            User.objects.get(email=email)
            return Response({
                "success": False,
                "fail_code": "WRONG_PASSWORD",
                "fail_msg": "账密错误"
            }, status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "fail_code": "USER_NOT_FOUND",
                "fail_msg": "用户不存在"
            }, status=status.HTTP_404_NOT_FOUND)

class login_captchaView(APIView):

    def post(self, request):
        email = request.data.get('email')
        captcha = request.data.get('captcha')
        if not all([email, captcha]):
            return Response({
                "fail_code":"MISSING_PARAM",
                "fail_msg":"缺少参数"
            },status=status.HTTP_400_BAD_REQUEST)
        if  varify_captcha(email,captcha)!=0:
            return varify_captcha(email,captcha)
        # user = authenticate(email=email, password=password)
        user = User.objects.filter(email=email)
        user = user.first()
        print(user)
        if user:
            salt = settings.SECRET_KEY
            headers = {
                'typ':'jwt',
                'alg':'HS256'
            }
            print(user.username)
            payload = {
                'user_id': user.user_id,
                'username': user.username,
                'exp':datetime.now(timezone.utc) + timedelta(days=3)  # 延长token有效期为60分钟
            }

            token = jwt.encode(payload = payload, key = salt, algorithm="HS256", headers=headers)
            url= None
            if user.avatar:
                url = user.avatar.url
            return Response({
                "success":True,
                "access_token":token,
                "username":user.username,
                "user_id":user.user_id,
                "avatar":url
            })

        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "fail_code": "USER_NOT_FOUND",
                "fail_msg": "用户不存在"
            }, status=status.HTTP_404_NOT_FOUND)
        
class UserIdViewSet(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = PublicUserSerializer
    lookup_field = 'user_id'

class UserInfoView(ListCreateAPIView,RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # 直接返回当前请求的用户对象（通过 Token 解析出的用户）
        print(1)
        print(1234)
        return self.request.user
    def get_queryset(self):
        print(2)
        print(123)
        return User.objects.filter(user_id=self.request.user.user_id)


class UploadAvatarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 检查文件是否存在
        if 'avatar' not in request.FILES:
            return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['avatar']
        user = request.user

        try:
            # 保存文件到MinIO
            user.avatar.save(file.name, file)  # 自动触发存储系统保存

            # 确保用户对象保存到数据库
            user.save()

            # 获取完整的访问URL
            avatar_url = user.avatar.url

            return Response({
                'success': True,
                'avatar': avatar_url
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # 处理存储异常
            return Response({
                'error': f'Failed to upload avatar: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class UserProductsViewSet(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer
    lookup_field = 'user_id'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        sta = self.request.query_params.get('status')
        print(sta)
        return Product.objects.filter(user_id=user_id,status=sta).order_by('-created_at')

class UserComplaintViewSet(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ComplaintSerializer
    def perform_create(self, serializer):
        # 自动将当前登录用户绑定到complainer_id字段
        serializer.save(complainer_id=self.request.user)

class FollowUserDetailsViewSet(ListCreateAPIView,  RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer
    lookup_field = 'followee'
    def create(self, request, *args, **kwargs):
        follower = self.request.user
        followee = User.objects.get(user_id=self.kwargs.get("followee"))
        Follow.objects.create(follower=follower, followee=followee)
        return Response(status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        follower = self.request.user
        followee = User.objects.get(user_id=self.kwargs.get("followee"))
        Follow.objects.filter(follower=follower, followee=followee).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class modify_email(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        new_email = request.data.get('new_email')
        captcha = request.data.get('captcha')
        if not all([new_email, captcha]):
            return Response({
                "fail_code":"MISSING_PARAM",
                "fail_msg":"缺少参数"
            },status=status.HTTP_400_BAD_REQUEST)
        if varify_captcha(new_email,captcha)!=0:
            return varify_captcha(new_email,captcha)
        #确定新邮箱不重复
        if User.objects.filter(email=new_email).exists():
            return Response({
                "fail_code":"EMAIL_EXIST",
                "fail_msg":"邮箱已存在"
            },status=status.HTTP_400_BAD_REQUEST)

        #修改邮箱
        user = request.user
        user.email = new_email
        user.save()
        return Response({
            "success":True,
            "user_id":user.user_id
        })

    #  创建关注

class modify_password(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        new_password = request.data.get('new_password')
        new_password_repeat = request.data.get('new_password_repeat')
        captcha = request.data.get('captcha')
        if not all([new_password, new_password_repeat,captcha]):
            return Response({
                "fail_code":"MISSING_PARAM",
                "fail_msg":"缺少参数"
            },status=status.HTTP_400_BAD_REQUEST)

        if new_password  != new_password_repeat:
            return Response({
                "fail_code":"PASSWORD_NOT_MATCH",
                "fail_msg":"密码不匹配"
            },status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        if varify_captcha(request.user.email,captcha)!=0:
            return varify_captcha(request.user.email,captcha)
        user.password = make_password(new_password)
        user.save()
        return Response({
            "success":True,
            "user_id":user.user_id
        })


class FollowUserViewSet(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer
    """
    我关注的
    """
    def get_queryset(self):
        user = self.request.user
        return Follow.objects.filter(follower=user)

class FolloweeUserViewSet(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer
    """
    关注我的
    """
    def get_queryset(self):
        user = self.request.user
        return Follow.objects.filter(followee=user)


class ChatLogViewSet(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatLogSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        # 获取当前用户和聊天对象
        me = self.request.user
        chater = get_object_or_404(User, user_id=self.kwargs.get("user_id"))

        # 构建查询条件
        return ChatLog.objects.filter(
            Q(sender=me, receiver=chater) |
            Q(sender=chater, receiver=me)
        ).order_by('-send_at')  # 添加排序确保分页稳定

    def list(self, request, *args, **kwargs):
        # 调用父类方法获取分页响应
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class MessageViewSet(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MessagesSerializer
    pagination_class = StandardResultsSetPagination
    def get_queryset(self):
        # 获取当前登录用户
        user = self.request.user
        # 返回与当前用户关联的所有通知消息
        return user.messages.all().order_by('-created_at')

class getPassword(APIView):
    permission_classes = []
    authentication_classes = []
    def get(self, request):
        password = request.data.get('password')
        password = make_password(password)
        return Response({
            "password":password
        })
