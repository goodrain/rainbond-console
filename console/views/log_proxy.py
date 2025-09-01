# -*- coding: utf8 -*-
import logging
import requests
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework import status
from console.views.base import JWTAuthApiView
from www.utils.return_message import general_message

logger = logging.getLogger("default")


@method_decorator(csrf_exempt, name='dispatch')
class LogProxyView(JWTAuthApiView):
    """
    日志代理接口
    前端传递接口地址和请求参数，后端代理请求并返回结果
    """
    
    def post(self, request, *args, **kwargs):
        try:
            # 获取前端传递的参数
            target_url = request.data.get('url')
            request_data = request.data.get('data', {})
            headers = request.data.get('headers', {})
            
            # 验证必要参数
            if not target_url:
                result = general_message(400, "参数错误", "缺少目标URL参数")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            
            # 设置默认请求头
            default_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Rainbond-Console/1.0'
            }
            
            # 合并请求头
            if headers:
                default_headers.update(headers)
            
            logger.info("日志代理请求 - 目标URL: %s, 数据: %s", target_url, request_data)
            
            # 发送代理请求
            response = requests.post(
                url=target_url,
                json=request_data,
                headers=default_headers,
                timeout=30  # 设置30秒超时
            )
            
            # 获取响应数据
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            
            # 记录响应状态
            logger.info("日志代理响应 - 状态码: %s, 数据长度: %s", response.status_code, len(str(response_data)))
            
            # 返回响应结果
            result = general_message(
                200, 
                "success", 
                "代理请求成功", 
                bean=response_data,
                list=response_data if isinstance(response_data, list) else None
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except requests.exceptions.Timeout:
            logger.error("日志代理请求超时 - URL: %s", target_url)
            result = general_message(408, "请求超时", "目标服务器响应超时")
            return Response(result, status=status.HTTP_408_REQUEST_TIMEOUT)
            
        except requests.exceptions.ConnectionError:
            logger.error("日志代理连接错误 - URL: %s", target_url)
            result = general_message(502, "连接错误", "无法连接到目标服务器")
            return Response(result, status=status.HTTP_502_BAD_GATEWAY)
            
        except requests.exceptions.RequestException as e:
            logger.error("日志代理请求异常 - URL: %s, 错误: %s", target_url, str(e))
            result = general_message(500, "代理请求失败", f"请求异常: {str(e)}")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error("日志代理未知异常 - URL: %s, 错误: %s", target_url, str(e))
            result = general_message(500, "系统错误", f"未知异常: {str(e)}")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
