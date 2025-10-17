# -*- coding: utf8 -*-
import logging
import requests
import os
from urllib.parse import urljoin, urlparse
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
    
    def post(self, request):
        try:
            # 获取前端传递的参数
            target_url = request.data.get('url')
            base_url = request.data.get('base_url')  # 获取基础URL
            request_data = request.data.get('data', {})
            headers = request.data.get('headers', {})

            # Record request information
            logger.info("Log proxy request - target_url: %s, base_url: %s", target_url, base_url)

            # Validate required parameters
            if not target_url:
                result = general_message(400, "Parameter Error", "Missing target URL parameter")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            # Process URL: If relative path, need to combine with base URL
            parsed_url = urlparse(target_url)

            if not parsed_url.scheme:
                # No protocol (http/https), relative path detected, need to splice
                if base_url:
                    # Priority: use base_url provided by frontend
                    target_url = urljoin(base_url, target_url)
                    logger.info("Using frontend base_url: %s", target_url)
                else:
                    # Try to get log service URL from environment variable
                    log_service_url = os.getenv('LOG_SERVICE_URL', '')
                    if log_service_url:
                        target_url = urljoin(log_service_url, target_url)
                        logger.info("Using LOG_SERVICE_URL env variable: %s", target_url)
                    else:
                        # Try to automatically get log service URL from plugin configuration
                        plugin_backend = self._get_log_plugin_backend()
                        if plugin_backend:
                            target_url = urljoin(plugin_backend, target_url)
                            logger.info("Using plugin backend: %s", target_url)
                        else:
                            # Unable to build complete URL
                            error_msg = f"Cannot build complete URL: {target_url}, please provide base_url parameter"
                            logger.error(error_msg)
                            result = general_message(400, "Parameter Error", error_msg)
                            return Response(result, status=status.HTTP_400_BAD_REQUEST)

            # Set default headers
            default_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Rainbond-Console/1.0'
            }

            # Merge request headers
            if headers:
                default_headers.update(headers)

            logger.info("Log proxy request - target URL: %s, data keys: %s", target_url, list(request_data.keys()) if request_data else [])
            
            # Send proxy request
            response = requests.post(
                url=target_url,
                json=request_data,
                headers=default_headers,
                timeout=30  # Set 30 seconds timeout
            )

            # Get response data
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text

            # Log response status
            logger.info("Log proxy response - status code: %s, data length: %s", response.status_code, len(str(response_data)))

            # Return response result
            result = general_message(
                200,
                "success",
                "Proxy request successful",
                bean=response_data,
                list=response_data if isinstance(response_data, list) else None
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except requests.exceptions.Timeout:
            logger.error("Log proxy request timeout - URL: %s", target_url)
            result = general_message(408, "Request Timeout", "Target server response timeout")
            return Response(result, status=status.HTTP_408_REQUEST_TIMEOUT)

        except requests.exceptions.ConnectionError:
            logger.error("Log proxy connection error - URL: %s", target_url)
            result = general_message(502, "Connection Error", "Cannot connect to target server")
            return Response(result, status=status.HTTP_502_BAD_GATEWAY)

        except requests.exceptions.RequestException as e:
            logger.error("Log proxy request exception - URL: %s, error: %s", target_url, str(e))
            result = general_message(500, "Proxy Request Failed", f"Request exception: {str(e)}")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error("Log proxy unknown exception - URL: %s, error: %s", target_url, str(e))
            result = general_message(500, "System Error", f"Unknown exception: {str(e)}")
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_log_plugin_backend(self):
        """
        Get log plugin backend address from plugin configuration
        """
        try:
            from www.apiclient.regionapi import RegionInvokeApi

            # Get enterprise ID and region name (try multiple ways)
            enterprise_id = None
            region_name = None

            # 1. Get from view properties (if view is initialized)
            if hasattr(self, 'enterprise') and self.enterprise:
                enterprise_id = self.enterprise.enterprise_id

            # 2. Get from request data
            if not enterprise_id:
                request = getattr(self, 'request', None)
                if request:
                    enterprise_id = request.data.get('enterprise_id') or request.headers.get('X-Enterprise-Id')

            # 3. Get region name
            if not region_name:
                request = getattr(self, 'request', None)
                if request:
                    region_name = request.data.get('region_name') or request.headers.get('X-Region-Name')
                    if not region_name and hasattr(request, 'resolver_match'):
                        region_name = request.resolver_match.kwargs.get('region_name')

            if enterprise_id and region_name:
                region_api = RegionInvokeApi()
                _, body = region_api.list_plugins(enterprise_id, region_name, official=True)
                plugins = body.get("list", [])

                # Find log plugin
                for plugin in plugins:
                    if plugin.get("name") == "rainbond-enterprise-logs" and plugin.get("backend"):
                        return plugin["backend"]

            logger.warning("Cannot get enterprise_id or region_name, or log plugin not found")
            return None

        except Exception as e:
            logger.error("Failed to get backend address from plugin configuration: %s", str(e))
            return None
