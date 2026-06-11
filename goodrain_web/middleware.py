from django import http
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework.response import Response

import logging

logger = logging.getLogger('default')

try:
    import sentry_sdk
except ImportError:  # pragma: no cover - optional production dependency
    sentry_sdk = None


class ErrorPage(MiddlewareMixin):
    def process_exception(self, request, exception):
        if sentry_sdk:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "rainbond-console")
                scope.set_extra("method", request.method)
                sentry_sdk.capture_exception(exception)
        logger.exception("uncaught_exception", exception)
        if request.path.startswith('/api/') or request.path.startswith('/marketapi/') \
                or request.path.startswith('/console/'):
            error_report = {"ok": False, "reason": exception.__str__(), "exceptionName": exception.__class__.__name__}
            setattr(request, '_error_report', error_report)

        return None

    def process_response(self, request, response):
        if response.status_code == 500:
            if hasattr(request, '_error_report'):
                return http.JsonResponse(request._error_report, status=500)
            if settings.DEBUG:
                return response
            if isinstance(response, Response):
                return response
            else:
                return http.HttpResponse("<h1>server error</h1>", status=500)
        return response
