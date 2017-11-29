from django.conf.urls import patterns, url

from www.views.auth import DiscourseAuthView

urlpatterns = patterns(
    '',
    url(r'^discourse/sso$', DiscourseAuthView.as_view()),
)
