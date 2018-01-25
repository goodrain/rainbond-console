from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from www.views.plugin import *

urlpatterns = patterns(
    '',
    url(r'^/?$', login_required(AllPluginView.as_view())),
    url(r'^/create/$', login_required(CreatePluginView.as_view())),
    url(r'^/(?P<plugin_id>[\w\-]+)/config', login_required(PluginConfigView.as_view())),
    url(r'^/(?P<plugin_id>[\w\-]+)/manage', login_required(ManageConfigView.as_view())),
    url(r'^/(?P<plugin_id>[\w\-]+)/build', login_required(BuildPluginView.as_view())),
)
