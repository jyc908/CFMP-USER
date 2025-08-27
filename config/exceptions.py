from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import Throttled
from rest_framework import status
def custom_exception_handler(exc, context):
    #print("I'm working!!!!!!!!!!!!")
        # 自定义限流异常处理
    if isinstance(exc, Throttled):
        return Response({
            "fail_code": "SEND_TOO_FREQUENTLY",
            "fail_msg": "验证码发送过于频繁",
            "wait_time": exc.wait
            }, status=status.HTTP_400_BAD_REQUEST)
        

    # 调用默认的异常处理器
    response = exception_handler(exc, context)
    return response
    
