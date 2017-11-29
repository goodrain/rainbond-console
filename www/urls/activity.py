from django.conf.urls import patterns, url
from www.views.activities import ActivityView, ActivityIndexView

urlpatterns = patterns(
    '',
    url(r'^$', ActivityIndexView.as_view()),
    url(r'^/(?P<version>\d+)$', ActivityView.as_view()),
)
