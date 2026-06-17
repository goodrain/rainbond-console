# -*- coding: utf8 -*-
import re

from console.views.index import IndexTemplateView, RKE2Install
from django.urls import include, re_path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView
from django.views.static import serve

from goodrain_web import settings
from console.views.bill_proxy import BillProxyView
from console.views.app_server_proxy import AppServerProxyView

kwargs = {"document_root": settings.MEDIA_ROOT}


def static(prefix, view=serve, **kwargs):
    """
    Helper function to return a URL pattern for serving files whethre it is debug mode or not.
    """
    return [
        re_path(r'^%s(?P<path>.*)$' % re.escape(prefix.lstrip('/')), view, kwargs=kwargs),
    ]


urlpatterns = [
    # re_path(r'^$', views.Index.as_view()),
    re_path(r'^favicon\.ico$', RedirectView.as_view(url='/static/www/favicon.ico')),
    re_path(r'^$', IndexTemplateView.as_view()),
    re_path(r'^install-cluster.sh$', RKE2Install.as_view()),
    re_path(r'^console/', include('console.urls')),
    re_path(r'^app-server/.*$', AppServerProxyView.as_view()),
    re_path(r'^api/.*$', BillProxyView.as_view()),
]
if settings.IS_OPEN_API:
    urlpatterns.append(re_path(r'^openapi/', include('openapi.urls')), )
urlpatterns += staticfiles_urlpatterns() + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
