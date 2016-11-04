from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from cadmin.views.adminview import *

urlpatterns = patterns(
    '',
    url(r'^/?$', login_required(AdminViews.as_view())),
    url(r'^edit', login_required(ConfigDetailViews.as_view())),
    url(r'^update',login_required(UpdateAttrViews.as_view())),
    url(r'^logo',login_required(ConfigLogoViews.as_view())),
    url(r'^info',login_required(SpecificationSViews.as_view())),

)
