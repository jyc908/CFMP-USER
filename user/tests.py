# user/tests/test_views.py
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone
from .models import User, Captcha, Follow, ChatLog, Messages
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
import jwt
from django.conf import settings
from django.contrib.auth.hashers import make_password

class UserViewsTests(APITestCase):
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create(
            username="testuser",
            password=make_password("Testpass123!"),
            email="test@example.com",
            status=0,
            privilege=0
        )
        
        # 创建另一个用户
        self.other_user = User.objects.create(
            username="otheruser",
            password=make_password("Otherpass123!"),
            email="other@example.com",
            status=0,
            privilege=0
        )
        
        # 创建验证码
        self.captcha = Captcha.objects.create(
            captcha="123456",
            email="test@example.com",
            is_used=False
        )
        
        # 创建 JWT token
        self.token = self.generate_token(self.user)
        
        # 设置认证客户端
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def generate_token(self, user):
        payload = {
            'user_id': user.user_id,
            'username': user.username,
            'exp': timezone.now() + timedelta(days=3)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    def test_captcha_view(self):
        url = reverse('user:captcha')
        
        # 测试场景无效
        data = {'email': 'new@example.com', 'scene': 'invalid_scene'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # 测试注册场景
        data = {'email': 'new@example.com', 'scene': 'register'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_register_view(self):
        url = reverse('user:register')
        
        # 创建有效验证码
        Captcha.objects.create(
            captcha="654321",
            email="register@example.com",
            is_used=False
        )
        
        # 有效注册数据
        valid_data = {
            'username': 'newuser',
            'password': 'Newpass123!',
            'password_repeat': 'Newpass123!',
            'email': 'register@example.com',
            'captcha': '654321'
        }
        
        # 测试成功注册
        response = self.client.post(url, valid_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_login_password_view(self):
        url = reverse('user:login_password')
        
        # 有效登录凭据
        valid_data = {'email': 'test@example.com', 'password': 'Testpass123!'}
        response = self.client.post(url, valid_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
    
# user/tests/test_views.py

    def test_user_info_view(self):
        url = reverse('user:update_user')
        response = self.client.get(url)

        # 打印响应内容用于调试
        print(f"User Info Response: {response.content}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 确保响应是列表
        self.assertIsInstance(response.data, list)

        # 确保列表中至少有一个元素
        self.assertGreater(len(response.data), 0)

        # 获取第一个用户对象
        user_data = response.data[0]

        # 验证用户名
        self.assertEqual(user_data['username'], 'testuser')
    
    def test_upload_avatar_view(self):
        url = reverse('user:upload_portrait')
        
        # 创建测试图片
        image = SimpleUploadedFile(
            "avatar.jpg", 
            b"file_content", 
            content_type="image/jpeg"
        )
        
        # 测试上传头像
        response = self.client.post(url, {'avatar': image}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('avatar', response.data)
    
    def test_follow_operations(self):
        # 关注用户
        follow_url = reverse('user:user-follow-detail', kwargs={'followee': self.other_user.user_id})
        response = self.client.post(follow_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 获取关注列表
        following_url = reverse('user:user-follow-list')
        response = self.client.get(following_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        # 获取粉丝列表
        followers_url = reverse('user:user-followee-list')
        response = self.client.get(followers_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 取消关注
        response = self.client.delete(follow_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_modify_email(self):
        url = reverse('user:modify_email')
        
        # 创建新邮箱验证码
        Captcha.objects.create(
            captcha="789012",
            email="newemail@example.com",
            is_used=False
        )
        
        # 有效修改请求
        data = {
            'new_email': 'newemail@example.com',
            'captcha': '789012'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 验证邮箱已更新
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')
    
    def test_chat_log_view(self):
        # 创建聊天记录
        ChatLog.objects.create(
            sender=self.user,
            receiver=self.other_user,
            content="Hello there"
        )
        
        url = reverse('user:user-chat-detail', kwargs={'user_id': self.other_user.user_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
    
    def test_messages_view(self):
        # 创建系统消息
        message = Messages.objects.create(
            title="System Notification",
            content="System notification content"
        )
        
        # 将消息关联到用户
        self.user.messages.add(message)
        
        url = reverse('user:user-message-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
    
    def test_password_complexity(self):
        url = reverse('user:register')
        
        # 测试简单密码
        weak_password = {
            'username': 'weakuser',
            'password': 'simple',
            'password_repeat': 'simple',
            'email': 'weak@example.com',
            'captcha': '111111'
        }
        response = self.client.post(url, weak_password)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['fail_code'], "PASSWORD_COMPLEXITY")
    
    def test_token_authentication(self):
        # 测试受保护端点无token
        self.client.credentials()
        url = reverse('user:update_user')
        response = self.client.get(url)
        
        # 打印响应内容用于调试
        print(f"Token Auth Response (no token): {response.content}")
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # 测试无效token
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalidtoken')
        response = self.client.get(url)
        
        # 打印响应内容用于调试
        print(f"Token Auth Response (invalid token): {response.content}")
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_captcha_validation(self):
        url = reverse('user:login_captcha')
        
        # 创建有效验证码
        Captcha.objects.create(
            captcha="112233",
            email="captcha@example.com",
            is_used=False
        )
        
        # 创建用户
        user = User.objects.create(
            username="captchauser",
            password=make_password("Testpass123!"),
            email="captcha@example.com",
            status=0
        )
        
        # 有效验证码登录
        valid_data = {'email': 'captcha@example.com', 'captcha': '112233'}
        response = self.client.post(url, valid_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)