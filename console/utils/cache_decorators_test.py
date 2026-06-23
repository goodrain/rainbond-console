# -*- coding: utf-8 -*-
import os
from unittest import TestCase

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.test_settings")

import django  # noqa: E402

django.setup()

from django.http import HttpResponse  # noqa: E402

from console.utils.cache_decorators import never_cache  # noqa: E402


class _DRFLikeRequest(object):
    """A stand-in for ``rest_framework.request.Request``.

    DRF passes this to view methods; it is intentionally NOT a subclass of
    ``django.http.HttpRequest``, which is what tripped the stock ``never_cache``.
    """

    def __init__(self):
        self.GET = {}


class NeverCacheDecoratorTests(TestCase):
    def test_passes_through_non_httprequest_and_sets_headers(self):
        class View(object):
            @never_cache
            def get(self, request):
                return HttpResponse("ok")

        # Must not raise "never_cache didn't receive an HttpRequest".
        response = View().get(_DRFLikeRequest())

        self.assertEqual(response.status_code, 200)
        cache_control = response["Cache-Control"]
        self.assertIn("no-cache", cache_control)
        self.assertIn("max-age=0", cache_control)

    def test_forwards_arguments_and_returns_view_response(self):
        class View(object):
            @never_cache
            def get(self, request, *args, **kwargs):
                return HttpResponse("{}-{}".format(args[0], kwargs["flag"]))

        response = View().get(_DRFLikeRequest(), "x", flag="y")

        self.assertEqual(response.content, b"x-y")
        self.assertIn("no-cache", response["Cache-Control"])
