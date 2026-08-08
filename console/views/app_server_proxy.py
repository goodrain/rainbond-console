import json
import logging
import re
import threading
from typing import Any, Optional, Tuple

import requests
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger('default')

# 控制台内应用市场的"应用详情"接口，前端打开条目详情时经由本代理请求。
# 新版: /app-server/marketui/apps/{主键}/detail
# 旧版: /app-server/marketui/{marketID}/apps/{appID}/detail
APP_DETAIL_PATH_RE = re.compile(r'^/app-server/marketui/(?:[\w\-]+/)?apps/[\w\-]+/detail/?$')

# 上报浏览量的超时时间，上报失败不影响详情本身
VIEW_REPORT_TIMEOUT = 5


@method_decorator(csrf_exempt, name='dispatch')
class AppServerProxyView(View):
    def __init__(self, **kwargs: Any) -> None:
        super(AppServerProxyView, self).__init__(**kwargs)
        self.target_base_url = 'https://hub.grapps.cn'

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        # 获取原始请求路径
        path = request.get_full_path()
        # 构建目标URL
        target_url = f"{self.target_base_url}{path}"

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

            # 发送请求到目标服务
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
                content=response.content,
                status=response.status_code,
                content_type=response.headers.get('Content-Type', '')
            )

            # 复制响应头，过滤掉 hop-by-hop 头
            hop_by_hop_headers = (
                'connection', 'keep-alive', 'proxy-authenticate',
                'proxy-authorization', 'te', 'trailers', 'transfer-encoding',
                'upgrade', 'content-encoding', 'content-length'
            )
            for key, value in response.headers.items():
                if key.lower() not in hop_by_hop_headers:
                    django_response[key] = value

            self.report_app_view(request, response)

            return django_response

        except requests.RequestException as e:
            return HttpResponse(f"Error proxying request: {str(e)}", status=502)

    def report_app_view(self, request: Any, response: Any) -> None:
        """控制台内打开应用详情时，向商店上报一次浏览量(showCount)。

        商店只在网页商店里统计浏览，控制台内的浏览一直没有上报，
        导致漏斗最顶端的一格是空的。上报为旁路操作，失败不影响详情返回。
        """
        if request.method != 'GET' or response.status_code != 200:
            return
        if not APP_DETAIL_PATH_RE.match(request.path):
            return

        app = self.parse_app_identity(response)
        if not app:
            return
        market_id, app_key_id = app

        headers = {'Content-Type': 'application/json'}
        # 商店按 X-Forwarded-For / X-Real-Ip 记录浏览来源，透传真实客户端 IP
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        remote_addr = request.META.get('REMOTE_ADDR', '')
        if forwarded_for:
            headers['X-Forwarded-For'] = forwarded_for
        if remote_addr:
            headers['X-Real-IP'] = remote_addr

        url = f"{self.target_base_url}/app-server/markets/{market_id}/apps/{app_key_id}/view"
        try:
            threading.Thread(target=self.post_app_view, args=(url, headers), daemon=True).start()
        except Exception as e:
            logger.warning("report app view not started url=%s error=%s", url, e)

    @staticmethod
    def parse_app_identity(response: Any) -> Optional[Tuple[str, str]]:
        """从应用详情响应里取出商店 ID 和应用 ID。"""
        if 'application/json' not in response.headers.get('Content-Type', ''):
            return None
        try:
            detail = json.loads(response.content)
        except (ValueError, TypeError):
            return None
        if not isinstance(detail, dict):
            return None
        market_id = detail.get('marketID')
        app_key_id = detail.get('appKeyID')
        if not market_id or not app_key_id:
            return None
        return market_id, app_key_id

    @staticmethod
    def post_app_view(url: str, headers: dict) -> None:
        try:
            resp = requests.post(url, headers=headers, data='{}', timeout=VIEW_REPORT_TIMEOUT, verify=False)
            if resp.status_code != 200:
                logger.warning("report app view failed url=%s status_code=%s", url, resp.status_code)
        except Exception as e:
            logger.warning("report app view failed url=%s error=%s", url, e)
