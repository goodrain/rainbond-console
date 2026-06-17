# -*- coding: utf-8 -*-
"""Cache-related view decorators compatible with class-based DRF views.

Django 4.0 added a strict ``hasattr(request, "META")`` guard to
``django.views.decorators.cache.never_cache``. Applying the raw decorator
directly to a class/instance method (``@never_cache`` above ``def get(self, ...)``)
makes the wrapper receive the bound ``self`` as its first argument instead of the
request, so it raises::

    TypeError: never_cache didn't receive an HttpRequest. If you are decorating a
    classmethod, be sure to use @method_decorator.

The project applies ``@never_cache`` to view methods in dozens of places. To keep
those call sites unchanged we expose a ``never_cache`` that is already wrapped with
``method_decorator``, which is the Django-recommended way to apply a function-view
decorator to a method.
"""

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache as _never_cache

# Method-friendly variant. Use exactly like the original ``never_cache`` but on
# class/instance methods of DRF views.
never_cache = method_decorator(_never_cache)
