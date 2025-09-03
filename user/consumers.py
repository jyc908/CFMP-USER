import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatLog, User
import logging

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        logger.info("=== WebSocket连接开始 ===")

        # 打印完整的scope信息（敏感信息除外）
        scope_info = {
            'type': self.scope.get('type'),
            'path': self.scope.get('path'),
            'user': str(self.scope.get('user'))
        }
        logger.info(f"Scope info: {scope_info}")

        self.user = self.scope["user"]
        logger.info(f"用户对象: {self.user}")
        logger.info(f"用户类型: {type(self.user)}")

        # 检查用户是否已认证
        if isinstance(self.user, User):
            logger.info(f"用户ID: {self.user.user_id}")
            logger.info(f"用户状态: {getattr(self.user, 'status', 'N/A')}")
        else:
            logger.error("用户未正确识别为User对象")
            await self.close()
            return

        # 检查用户认证状态
        if not hasattr(self.user, 'user_id') or not self.user.user_id:
            logger.error("用户未认证 - 缺少user_id")
            await self.close()
            return

        logger.info("用户认证检查通过")

        self.room_group_name = f"user_{self.user.user_id}"  # 使用用户ID作为组名
        logger.info(f"房间组名: {self.room_group_name}")

        # 添加连接状态检查
        if self.channel_layer is None:
            logger.error("Channel layer未配置")
            await self.close()
            return

        logger.info("开始添加用户到房间组")
        try:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            logger.info("成功添加用户到房间组")
        except Exception as e:
            logger.error(f"添加用户到房间组失败: {e}")
            await self.close()
            return

        logger.info("接受WebSocket连接")
        await self.accept()
        logger.info(f"WebSocket连接成功建立，用户: {self.user.user_id}")

    async def disconnect(self, close_code):
        logger.info(f"=== WebSocket断开连接 ===")
        logger.info(f"关闭代码: {close_code}")
        logger.info(f"用户: {getattr(self, 'user', 'Unknown')}")

        # 添加更安全的检查
        if hasattr(self, 'room_group_name') and hasattr(self, 'channel_name'):
            logger.info(f"从房间组移除用户: {self.room_group_name}")
            try:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                logger.info("成功从房间组移除用户")
            except Exception as e:
                logger.error(f"从房间组移除用户失败: {e}")
        else:
            logger.warning("缺少房间组名或频道名")

        logger.info(f"WebSocket连接断开，用户: {getattr(self, 'user', 'Unknown')}")

    async def receive(self, text_data):
        logger.info(f"=== 收到WebSocket消息 ===")
        logger.info(f"原始消息数据: {text_data}")
        logger.info(f"当前用户: {getattr(self, 'user', 'Unknown')}")

        try:
            data = json.loads(text_data)
            logger.info(f"解析后的消息: {data}")

            # 添加数据验证
            if 'receiver_id' not in data or 'content' not in data:
                logger.error("消息缺少必要字段: receiver_id 或 content")
                await self.send(text_data=json.dumps({
                    'error': 'Missing required fields: receiver_id and content'
                }))
                return

            receiver_id = data['receiver_id']
            content = data['content']

            logger.info(f"发送目标: {receiver_id}")
            logger.info(f"消息内容: {content}")

            # 验证receiver_id格式（UUID）
            try:
                import uuid
                uuid.UUID(receiver_id)
                logger.info("接收者ID格式验证通过")
            except ValueError:
                logger.error(f"接收者ID格式无效: {receiver_id}")
                await self.send(text_data=json.dumps({
                    'error': 'Invalid receiver_id format'
                }))
                return

            # 保存消息到数据库
            logger.info("开始保存消息到数据库")
            try:
                await self.save_message(self.user.user_id, receiver_id, content)
                logger.info("消息保存成功")
            except Exception as e:
                logger.error(f"保存消息到数据库失败: {e}")
                await self.send(text_data=json.dumps({
                    'error': 'Failed to save message'
                }))
                return

            # 推送消息给接收者
            logger.info(f"开始推送消息给接收者: {receiver_id}")
            try:
                await self.channel_layer.group_send(
                    f"user_{receiver_id}",
                    {
                        'type': 'chat_message',
                        'message': {
                            'sender_id': str(self.user.user_id),  # 确保转换为字符串
                            'receiver_id': receiver_id,
                            'content': content,
                        }
                    }
                )
                logger.info("消息推送成功")
            except Exception as e:
                logger.error(f"消息推送失败: {e}")
                await self.send(text_data=json.dumps({
                    'error': 'Failed to deliver message'
                }))

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}")
            # 可以选择发送错误信息回客户端
            await self.send(text_data=json.dumps({
                'error': 'Failed to process message'
            }))

    async def chat_message(self, event):
        logger.info(f"=== 处理聊天消息事件 ===")
        logger.info(f"事件内容: {event}")

        try:
            # 发送信息到前端
            message_data = json.dumps(event['message'])
            logger.info(f"发送给前端的消息: {message_data}")
            await self.send(text_data=message_data)
            logger.info("消息发送成功")
        except Exception as e:
            logger.error(f"发送消息到客户端失败: {e}")

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, content):
        try:
            logger.info(f"=== 保存消息到数据库 ===")
            logger.info(f"发送者: {sender_id}")
            logger.info(f"接收者: {receiver_id}")
            logger.info(f"内容: {content}")

            # 验证用户是否存在
            sender_exists = User.objects.filter(user_id=sender_id).exists()
            receiver_exists = User.objects.filter(user_id=receiver_id).exists()

            logger.info(f"发送者存在: {sender_exists}")
            logger.info(f"接收者存在: {receiver_exists}")

            if not sender_exists:
                raise ValueError(f"发送者 {sender_id} 不存在")
            if not receiver_exists:
                raise ValueError(f"接收者 {receiver_id} 不存在")

            chat_log = ChatLog.objects.create(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=content
            )  # 存数据库
            logger.info(f"消息保存成功，ID: {chat_log.chat_id}")
        except Exception as e:
            logger.error(f"保存消息到数据库时出错: {e}")
            raise
