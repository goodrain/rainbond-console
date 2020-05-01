# -*- coding: utf8 -*-
import re
import sys

from django.conf.urls import include
from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import RedirectView
from django.views.static import serve

from console.views.index import IndexTemplateView
from goodrain_web import settings

reload(sys)  # Python2.5 初始化后会删除 sys.setdefaultencoding 这个方法，我们需要重新载入
sys.setdefaultencoding('utf-8')

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
