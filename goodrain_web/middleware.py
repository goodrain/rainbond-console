from django import http
from django.conf import settings

import logging
logger = logging.getLogger('default')


class ErrorPage(object):

    def process_exception(self, request, exception):
        logger.exception("uncaught_exception", exception)
        if request.path.startswith('/api/'):
            error_report = {"ok": False, "reason": exception.__str__(), "exceptionName": exception.__class__.__name__}
            setattr(request, '_error_report', error_report)
        return None

    def process_response(self, request, response):
        if response.status_code == 500:
            if settings.DEBUG:
                return response
            if hasattr(request, '_error_report'):
                return http.JsonResponse(request._error_report, status=500)
            else:
                return http.HttpResponse("<h1>server error</h1>", status=500)
        return response
