from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from share.views.region_provider_view import *

urlpatterns = patterns(
    '',
    url(r'^$', login_required(RegionOverviewView.as_view())),
    url(r'^region/$', login_required(RegionOverviewView.as_view())),
    url(r'^region/price/$', login_required(RegionResourcePriceView.as_view())),
    url(r'^region/report/consume/$', login_required(RegionResourceConsumeView.as_view())),
    url(r'^region/settle/$', login_required(RegionResourceSettleView.as_view())),
    url(r'^region/provider/$', login_required(RegionProviderView.as_view())),
    url(r'^teamfix/$', login_required(TeamDataFix.as_view())),
    url(r'^team/create/$', login_required(TeamCreate.as_view())),
)
