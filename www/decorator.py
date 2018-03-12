import logging
from functools import wraps

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import JsonResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import redirect
from django.shortcuts import resolve_url
from django.utils.decorators import available_attrs
from django.utils.six import Module_six_moves_urllib_parse

from goodrain_web.errors import UrlParseError, PermissionDenied
from www.perms import check_perm
from www.utils.url import get_redirect_url

logger = logging.getLogger('default')


def user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def login_redirect(request):
        path = request.build_absolute_uri()
        resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
        login_scheme, login_netloc = Module_six_moves_urllib_parse(resolved_login_url)[:2]
        current_scheme, current_netloc = Module_six_moves_urllib_parse(path)[:2]
        if ((not login_scheme or login_scheme == current_scheme) and
                (not login_netloc or login_netloc == current_netloc)):
            path = request.get_full_path()
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(
            get_redirect_url(path, request), resolved_login_url, redirect_field_name)

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(view_object, *args, **kwargs):
            try:
                if test_func(view_object.user, *args, **kwargs):
                    return view_func(view_object, *args, **kwargs)
                else:
                    return redirect(get_redirect_url('/error', request=view_object.request))
            except PermissionDenied, e:
                if e.redirect_url is not None:
                    request = view_object.request
                    return login_redirect(request)
                else:
                    return JsonResponse({"reason": e.error}, status=403)
            except UrlParseError, e:
                if e.code == 403:
                    response = HttpResponseRedirect(settings.LOGIN_URL)
                    response.delete_cookie('tenant_name')
                    return response
                return JsonResponse({"reason": e.error}, status=e.code)

        return _wrapped_view

    return decorator


def perm_required(perm, tenant_name=None):
    # logger.debug("debug", "check perm {}".format(perm))
    def perm_test(user, *args, **kwargs):
        tenantName = kwargs.get('tenantName', None)
        if not tenantName:
            tenantName = kwargs.get('team_name', None)
        serviceAlias = kwargs.get('serviceAlias', None)
        if not serviceAlias:
            serviceAlias = kwargs.get('service_alias', None)
        if tenant_name:
            tenantName = tenant_name
        return check_perm(perm, user, tenantName, serviceAlias)

    return user_passes_test(perm_test)
