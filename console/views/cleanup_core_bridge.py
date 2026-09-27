"""Internal cleanup bridge: no browser identity or arbitrary upstream headers."""
import os
from typing import Any

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from console.services.cleanup_core_bridge import decode_core_request, verify_core_request
from console.services.cleanup_gateway import CleanupGatewayUnavailable
from console.services.cleanup_installation import resolve_gateway_key
from www.apiclient.regionapi import RegionInvokeApi


class CleanupCoreBridgeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def finalize_response(self, request: Request, response: Response, *args: Any, **kwargs: Any) -> Response:
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response

    def post(self, request: Request, enterprise_id: str, region_name: str) -> Response:
        enterprise = os.environ.get('CLEANUP_SOURCE_ENTERPRISE_ID', '')
        regions = os.environ.get('CLEANUP_SOURCE_REGIONS', '')
        if (enterprise and enterprise != enterprise_id) or (regions and region_name not in regions.split(',')):
            return Response({'msg': 'FORBIDDEN'}, status=403)
        length = request.META.get('CONTENT_LENGTH', '')
        if length and (not str(length).isdigit() or len(str(length)) > 10 or int(length) > 65536):
            return Response({'msg': 'INVALID_COORDINATION_REQUEST'}, status=400)
        raw = request.body
        try:
            path, body = decode_core_request(raw)
        except ValueError:
            return Response({'msg': 'INVALID_COORDINATION_REQUEST'}, status=400)
        try:
            key = resolve_gateway_key(enterprise_id, region_name)
        except CleanupGatewayUnavailable:
            return Response({'msg': 'COORDINATION_UNAVAILABLE'}, status=503)
        if not verify_core_request(request.get_full_path(), enterprise_id, region_name,
                                   request.headers.get('X-Cleanup-Coordination-Time', ''),
                                   request.headers.get('X-Cleanup-Coordination-Signature', ''), raw, key):
            return Response({'msg': 'FORBIDDEN'}, status=403)
        try:
            status, result = RegionInvokeApi().cleanup_proxy_request(enterprise_id, region_name, path, body)
        except Exception:
            return Response({'msg': 'COORDINATION_UNAVAILABLE'}, status=503)
        return Response(result, status=status)
