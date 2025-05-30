import os
import requests
from django.http import HttpResponse
from django.views import View
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class BillProxyView(View):
    def __init__(self, **kwargs):
        super(BillProxyView, self).__init__(**kwargs)
        self.bill_service_url = os.getenv('BILL_SERVICE_URL', '')

    def dispatch(self, request, *args, **kwargs):
        # 获取原始请求路径
        path = request.get_full_path()
        # 构建目标URL
        target_url = f"{self.bill_service_url}{path}"

        # 转发请求头
        headers = {
            'X-Real-IP': request.META.get('REMOTE_ADDR', ''),
            'X-Forwarded-For': request.META.get('HTTP_X_FORWARDED_FOR', ''),
            'X-Forwarded-Proto': request.scheme,
        }
        
        # 如果有认证信息，转发 Authorization 头
        if 'HTTP_AUTHORIZATION' in request.META:
            headers['Authorization'] = request.META['HTTP_AUTHORIZATION']

        # 复制原始请求的其他相关头信息
        for header in request.META:
            if header.startswith('HTTP_') and header not in ('HTTP_HOST', 'HTTP_X_FORWARDED_FOR'):
                headers[header[5:].replace('_', '-').title()] = request.META[header]

        try:
            # 发送请求到账单服务
            response = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.body if request.method in ('POST', 'PUT', 'PATCH') else None,
                params=request.GET,
                stream=True,
                verify=False
            )

            # 创建Django响应
            django_response = HttpResponse(
                content=response.content,  # 使用 content 而不是 raw
                status=response.status_code,
                content_type=response.headers.get('Content-Type', '')
            )

            # 复制响应头
            for key, value in response.headers.items():
                if key.lower() not in ('content-encoding', 'transfer-encoding', 'content-length'):
                    django_response[key] = value

            return django_response

        except requests.RequestException as e:
            return HttpResponse(f"Error proxying request: {str(e)}", status=502) 