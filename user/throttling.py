from rest_framework.throttling import SimpleRateThrottle

# 自定义限流类
class EmailRateThrottle(SimpleRateThrottle):
    scope = 'email'  # 对应 settings.py 中的配置项
    
    def get_cache_key(self, request, view):
        # 根据邮箱地址限流（替代原有的 IP 限流）
        email = request.data.get('email', None)
        if not email:
            # 如果没有提供邮箱，回退到 IP 限流
            return self.cache_format % {
                'scope': self.scope,
                'ident': self.get_ident(request)
            }
            
        # 使用邮箱作为限流标识
        return self.cache_format % {
            'scope': self.scope,
            'ident': email
        }
