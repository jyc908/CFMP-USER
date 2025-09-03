from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import user.routing
from user.middleware import TokenAuthMiddleware

application = ProtocolTypeRouter({
    # 其他协议处理器...
    'websocket': TokenAuthMiddleware(
        URLRouter(
                user.routing.websocket_urlpatterns
        )
    ),
})
