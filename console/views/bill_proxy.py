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
            # 检查是否是文件上传请求
            content_type = request.META.get('CONTENT_TYPE', '')
            request_data = None
            request_files = None

            if request.method in ('POST', 'PUT', 'PATCH'):
                if content_type.startswith('multipart/form-data'):
                    # 处理文件上传 - 不设置Content-Type让requests自动处理
                    if 'Content-Type' in headers:
                        del headers['Content-Type']

                    # 准备表单数据
                    request_data = {}
                    request_files = {}

                    # 添加普通表单字段
                    for key, value in request.POST.items():
                        request_data[key] = value

                    # 添加文件字段
                    for key, file_obj in request.FILES.items():
                        request_files[key] = (file_obj.name, file_obj.read(), file_obj.content_type)
                else:
                    # 非文件上传请求，使用原始body
                    request_data = request.body

            # 发送请求到账单服务
            if request_files:
                # 文件上传请求
                response = requests.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    data=request_data,
                    files=request_files,
                    params=request.GET,
                    stream=True,
                    verify=False
                )
            else:
                # 普通请求
                response = requests.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    data=request_data,
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