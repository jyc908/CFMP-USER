from rest_framework import serializers
from . import models
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = '__all__'

class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ['user_id', 'username', 'avatar','status']

class FollowSerializer(serializers.ModelSerializer):
    follower = PublicUserSerializer(read_only=True)
    followee = PublicUserSerializer(read_only=True)
    class Meta:
        model = models.Follow
        fields = '__all__'

class ChatLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.ChatLog
        fields = '__all__'

class MessagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Messages
        fields = '__all__'