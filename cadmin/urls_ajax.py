from django.conf.urls import patterns, url
from django.views.decorators.csrf import csrf_exempt
from cadmin.views.ajax.adminview import ConfigViews,ConfigAttributeViews,ConfigDetailViews,SingAttrAddOrModifyViews, \
    UploadLogoViews

urlpatterns = patterns(
    '',
    url(r'^custome-config', ConfigViews.as_view()),
    url(r'^custome-attribute', ConfigAttributeViews.as_view()),
    url(r'^detail', ConfigDetailViews.as_view()),
    url(r'^addSingleAttrbuite',SingAttrAddOrModifyViews.as_view()),
    url(r'^upload',csrf_exempt(UploadLogoViews.as_view())),
)
