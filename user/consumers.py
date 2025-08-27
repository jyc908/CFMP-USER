import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatLog, User


class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.user = self.scope["user"]
        self.room_group_name = f"user_{self.user.user_id}"  # 使用用户ID作为组名
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
            data = json.loads(text_data)
            print(data)
            receiver_id = data['receiver_id']
            content = data['content']

            # 关注关系?
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

    async def chat_message(self, event):
            await self.send(text_data=json.dumps(event['message']))  #发送信息到前端

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, content):
            ChatLog.objects.create(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=content
            )#存数据库
        
        


