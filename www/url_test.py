from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, url
from www.tests import *
import www.views as views

urlpatterns = patterns(
    '',
    url(r'^base/$', BaseView.as_view()),
    url(r'^raster/$', RasterView.as_view()),
    url(r'^services/$', ServiceListView.as_view()),
    url(r'^login$', views.Login.as_view()),
    url(r'^logout$', views.Logout.as_view()),
    url(r'^invites/$', login_required(views.InviteUser.as_view())),
    url(r'^invite$', views.InviteRegistation.as_view()),
    url(r'^register$', views.Registation.as_view()),
)
