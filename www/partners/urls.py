from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt

from www.partners.ucloud import UcloudView

urlpatterns = patterns(
    '',
    url(r'^ucloud/$', csrf_exempt(UcloudView.as_view())),
)
