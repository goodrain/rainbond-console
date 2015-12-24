from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from www.views.payedpackage import PackageSelectView, PackageUpgradeView

urlpatterns = patterns(
    '',
    url(r'^select$', login_required(PackageSelectView.as_view())),
    url(r'^upgrade$', login_required(PackageUpgradeView.as_view())),
)
