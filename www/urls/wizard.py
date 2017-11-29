from django.conf.urls import patterns, url
from www.views.wizard import *

urlpatterns = patterns(
    '',
    url(r'^prefix/$', PrefixView.as_view()),
    url(r'^index/$', WizardView.as_view()),
)
