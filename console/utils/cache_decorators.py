# -*- coding: utf-8 -*-
"""Cache-related view decorators compatible with class-based DRF views.

Django 4.0+ hardened ``django.views.decorators.cache.never_cache`` with a strict
``isinstance(request, HttpRequest)`` guard. DRF dispatches view methods with a
``rest_framework.request.Request`` (which is **not** an ``HttpRequest`` subclass),
so applying the stock decorator to a view method — even via ``method_decorator`` —
raises at call time::

    TypeError: never_cache didn't receive an HttpRequest. If you are decorating a
    classmethod, be sure to use @method_decorator.

The project applies ``@never_cache`` to DRF view methods in dozens of places. To
keep those call sites unchanged while supporting any request type, this variant
does not inspect the request at all: it simply invokes the wrapped method and
stamps the standard never-cache headers onto the returned response (which is
exactly what Django's decorator does, minus the request-type guard).
"""

from functools import wraps

from django.utils.cache import add_never_cache_headers


def never_cache(view_method):
    """Mark a class-based view method's response as never-cacheable.

    Use exactly like Django's ``never_cache`` but on a bound view method
    (``def get(self, request, ...)``). The request is passed straight through to
    the wrapped method, so DRF ``Request`` instances (and plain test doubles) are
    supported.
    """

    @wraps(view_method)
    def _wrapped(self, request, *args, **kwargs):
        response = view_method(self, request, *args, **kwargs)
        add_never_cache_headers(response)
        return response

    return _wrapped
