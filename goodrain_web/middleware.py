from django import http
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework.response import Response

import logging

from goodrain_web.sentry_config import get_path_pattern, sanitize_value

logger = logging.getLogger('default')

try:
    import sentry_sdk
except ImportError:  # pragma: no cover - optional production dependency
    sentry_sdk = None


class ErrorPage(MiddlewareMixin):
    def process_exception(self, request, exception):
        if sentry_sdk:
            with sentry_sdk.push_scope() as scope:
                route = get_path_pattern(request.get_full_path())
                team_name = request.META.get("HTTP_X_TEAM_NAME") or getattr(
                    getattr(request, "tenant", None),
                    "tenant_name",
                    "",
                )
                region_name = (
                    request.META.get("HTTP_X_REGION_NAME") or request.META.get("HTTP_X_REGION")
                )
                scope.set_tag("component", "rainbond-console")
                scope.set_tag("error_source", "django")
                scope.set_tag("http.method", request.method)
                if route:
                    scope.set_tag("http.route", route)
                    scope.set_extra("route", route)
                if team_name:
                    scope.set_tag("rainbond.team", sanitize_value(team_name))
                if region_name:
                    scope.set_tag("rainbond.region", sanitize_value(region_name))
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
