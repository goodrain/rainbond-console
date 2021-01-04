# -*- coding: utf8 -*-
import importlib
import re
import sys

from console.views.index import IndexTemplateView
from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView
from django.views.static import serve

from goodrain_web import settings

kwargs = {"document_root": settings.MEDIA_ROOT}


def static(prefix, view=serve, **kwargs):
    """
    Helper function to return a URL pattern for serving files whethre it is debug mode or not.
    """
    return [
        url(r'^%s(?P<path>.*)$' % re.escape(prefix.lstrip('/')), view, kwargs=kwargs),
    ]


urlpatterns = [
    # url(r'^$', views.Index.as_view()),
    url(r'^favicon\.ico$', RedirectView.as_view(url='/static/www/favicon.ico')),
    url(r'^$', IndexTemplateView.as_view()),
    url(r'^console/', include('console.urls')),
]
if settings.IS_OPEN_API:
    urlpatterns.append(url(r'^openapi/', include('openapi.urls')), )
urlpatterns += staticfiles_urlpatterns() + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
