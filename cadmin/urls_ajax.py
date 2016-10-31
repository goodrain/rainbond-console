from django.conf.urls import patterns, url
from www.views.ajax.adminview import AdminViews

urlpatterns = patterns(
    '',
    url(r'^admin/test/$', AdminViews.as_view()),
    
)
