# -*- coding: utf8 -*-
from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from console.views.index import IndexTemplateView
from django.views.generic.base import RedirectView
from django.conf.urls.static import static
import sys
reload(sys)  # Python2.5 初始化后会删除 sys.setdefaultencoding 这个方法，我们需要重新载入
sys.setdefaultencoding('utf-8')


urlpatterns = [
    # url(r'^$', views.Index.as_view()),
    url(r'^favicon\.ico$',
        RedirectView.as_view(url='/static/www/favicon.ico')),
    url(r'^$', IndexTemplateView.as_view()),
    url(r'^console/', include('console.urls')),
    url(r'^openapi/', include('openapi.urls')),
    url(r'^backend/', include('backends.urls')),
 ] + staticfiles_urlpatterns()+static(r'^data/media/(?P<path>.*)$', document_root=settings.MEDIA_ROOT)
