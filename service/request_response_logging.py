import logging
from django.utils.deprecation import MiddlewareMixin

# 创建一个logger
logger = logging.getLogger('myapp')

class RequestResponseLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 记录 POST 请求的数据
        if request.method == 'POST':
            logger.info(f"POST request received: {request.path}")
            logger.info(f"POST data: {request.body.decode('utf-8')}")

    def process_response(self, request, response):
        # 只记录 GET 请求的响应数据
        if request.method == 'GET':
            logger.info(f"GET request made: {request.path}")
            logger.info(f"GET response data: {response.content.decode('utf-8')}")

        return response
