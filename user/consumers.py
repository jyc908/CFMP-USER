import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatLog, User
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.user = self.scope["user"]
        # 检查用户是否已认证
        if not self.user.is_authenticated:
            await self.close()
            return
            
        self.room_group_name = f"user_{self.user.user_id}"  # 使用用户ID作为组名
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"WebSocket connected for user {self.user.user_id}")

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected for user {self.user.user_id} with code {close_code}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            logger.info(f"Received message: {data}")
            receiver_id = data['receiver_id']
            content = data['content']

            # 保存消息到数据库
            await self.save_message(self.user.user_id, receiver_id, content)
            
            # 推送消息给接收者
            await self.channel_layer.group_send(
                f"user_{receiver_id}",
                {
                    'type': 'chat_message',
                    'message': {
                        'sender_id': self.user.user_id,
                        'receiver_id': receiver_id,
                        'content': content,
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # 可以选择发送错误信息回客户端
            await self.send(text_data=json.dumps({
                'error': 'Failed to process message'
            }))

    async def chat_message(self, event):
        try:
            # 发送信息到前端
            await self.send(text_data=json.dumps(event['message']))
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, content):
        try:
            ChatLog.objects.create(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=content
            )  # 存数据库
        except Exception as e:
            logger.error(f"Error saving message to database: {e}")
            raise