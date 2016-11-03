from django.conf.urls import patterns, url
from cadmin.views.ajax.adminview import ConfigViews,ConfigAttributeViews,ConfigDetailViews,SingAttrAddOrModifyViews

urlpatterns = patterns(
    '',
    url(r'^custome-config', ConfigViews.as_view()),
    url(r'^custome-attribute', ConfigAttributeViews.as_view()),
    url(r'^detail', ConfigDetailViews.as_view()),
    url(r'^addSingleAttrbuite',SingAttrAddOrModifyViews.as_view()),
)
