"""Authenticated, explicitly confirmed platform-record retirement bridge."""
import re
import logging
from typing import Any
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.services.cleanup_gateway import CleanupGatewayUnavailable
from console.services.cleanup_installation import resolve_gateway_key
from console.services.cleanup_retirement import (
    verify_retirement_request, retire_template, retire_build_version, RetirementConflict
)
from www.models.main import Users


logger = logging.getLogger("default")


class CleanupRetirementView(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def post(self, request: Request, enterprise_id: str, region_name: str) -> Response:
        length = request.META.get('CONTENT_LENGTH', '')
        if length and (not str(length).isdigit() or len(str(length)) > 10 or int(length) > 65536):
            return Response({'errorCode': 'INVALID_REQUEST'}, status=400)
        body = request.body
        try:
            key = resolve_gateway_key(enterprise_id, region_name)
        except CleanupGatewayUnavailable:
            return Response({'errorCode': 'SOURCE_AUTH_UNAVAILABLE'}, status=503)
        if not verify_retirement_request(request.method or "", request.get_full_path(), enterprise_id, region_name,
                                         request.headers.get('X-Cleanup-Retirement-Time'),
                                         request.headers.get('X-Cleanup-Retirement-Signature'), body, key):
            return Response({'errorCode': 'FORBIDDEN'}, status=403)
        data = request.data
        if not isinstance(data, dict) or set(data) != {'actor', 'operationId', 'kind', 'expected'}:
            return Response({'errorCode': 'INVALID_REQUEST'}, status=400)
        actor = data.get('actor')
        operation = data.get('operationId')
        if (not isinstance(actor, str) or not re.fullmatch(r'[0-9]{1,10}', actor)
                or not isinstance(operation, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', operation)):
            return Response({'errorCode': 'INVALID_REQUEST'}, status=400)
        if not Users.objects.filter(user_id=int(actor), enterprise_id=enterprise_id, is_active=True).exists():
            return Response({'errorCode': 'FORBIDDEN'}, status=403)
        if not enterprise_user_perm_repo.is_admin(enterprise_id, actor):
            return Response({'errorCode': 'FORBIDDEN'}, status=403)
        expected = data.get('expected')
        if not isinstance(expected, dict):
            return Response({'errorCode': 'INVALID_REQUEST'}, status=400)
        if not isinstance(expected.get('activation_revision'), str) or len(expected['activation_revision']) > 64:
            return Response({'errorCode': 'INVALID_REQUEST'}, status=400)
        try:
            if data['kind'] == 'template_version':
                if (set(expected) != {'id', 'app_id', 'version', 'content_hash', 'activation_revision'}
                        or type(expected['id']) is not int or expected['id'] <= 0
                        or not isinstance(expected['content_hash'], str)
                        or not re.fullmatch(r'[a-f0-9]{64}', expected['content_hash'])):
                    raise ValueError()
                for field in ('app_id', 'version'):
                    if not isinstance(expected[field], str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', expected[field]):
                        raise ValueError()
                result = retire_template(enterprise_id, region_name, expected, key)
            elif data['kind'] == 'build_version':
                if set(expected) != {'service_id', 'version', 'current_version', 'image', 'event_id', 'activation_revision'}:
                    raise ValueError()
                for field in ('service_id', 'version', 'current_version', 'event_id'):
                    if (not isinstance(expected[field], str) or expected[field] in ('.', '..')
                            or not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', expected[field])):
                        raise ValueError()
                if not isinstance(expected['image'], str) or not 1 <= len(expected['image']) <= 2048:
                    raise ValueError()
                result = retire_build_version(enterprise_id, region_name, expected, actor, operation)
            else:
                raise ValueError()
        except (ValueError, KeyError):
            return Response({'errorCode': 'INVALID_REQUEST'}, status=400)
        except ObjectDoesNotExist:
            return Response({'errorCode': 'RESOURCE_CHANGED'}, status=409)
        except RetirementConflict:
            return Response({'errorCode': 'RESOURCE_PROTECTED'}, status=409)
        except Exception:
            # The Region response may contain internal URLs; do not expose it.
            return Response({'errorCode': 'RETIREMENT_UNAVAILABLE'}, status=503)
        logger.info("cleanup record retired enterprise=%s region=%s actor=%s operation=%s kind=%s",
                    enterprise_id, region_name, actor, operation, data["kind"])
        return Response(dict(result, operationId=operation))
