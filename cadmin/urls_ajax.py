from django.conf.urls import patterns, url
from cadmin.views.ajax.adminview import AdminViews

urlpatterns = patterns(
    '',
    url(r'^admin/test/$', AdminViews.as_view()),
    
)
