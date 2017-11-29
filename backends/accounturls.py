from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
from backends.views.account import LoginView,LogoutView

urlpatterns = patterns(
    '',
    url(r'^login$', csrf_exempt(LoginView.as_view())),
    url(r'^logout$', csrf_exempt(LogoutView.as_view())),

)
