from django.db import models
from minio_storage import MinioMediaStorage

# User数据表：user, captcha, chatlog, follow, messages
# NOTE:
# 无外键引用的情况


# NOTE:
# 关键表：多次被外键引用需要添加UUID，以便于跨服务通信
class User(models.Model):
    BANNED = 1
    NORMAL = 0
    STATUS_CHOICES = [
        (NORMAL, '正常'),
        (BANNED, '已封禁'),
    ]

    user_id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=30)
    password = models.CharField(max_length=200)
    email = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(choices=STATUS_CHOICES,  default=NORMAL)
    privilege = models.IntegerField(default=0)
    captcha = models.CharField(max_length=4,null=True,blank=True)
    is_authenticated = models.BooleanField(default=False)
    avatar = models.ImageField(storage=MinioMediaStorage(),null=True, blank=True)
    address = models.CharField(max_length=100,null=True,blank=True)
    messages = models.ManyToManyField("Messages",related_name="users")
    class Meta:
        db_table = "user"

class Captcha(models.Model):
    email = models.CharField(max_length=50)
    captcha = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    class Meta:
        db_table = "captcha"
class ChatLog(models.Model):
    chat_id = models.BigAutoField(primary_key=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sender",default=None,null=True)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="receiver",default=None,null=True)
    content = models.TextField()
    send_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        db_table = "chat_log"

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follower")
    followee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followee")

    class Meta:
        db_table = "follow"
# Create your models here.

class Messages(models.Model):
    message_id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages"
