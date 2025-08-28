from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import routing

application = ProtocolTypeRouter({
    # 其他协议处理器...
    'websocket': AuthMiddlewareStack(
        URLRouter(
                routing.websocket_urlpatterns
        )
    ),
})
