# -*- coding: utf-8 -*-
# creater by: barnett
from django.conf.urls import url
from openapi.v2.views.region_view import ListRegionInfo
from openapi.v2.views.enterprise_view import ListEnterpriseInfoView
from openapi.v2.views.region_view import RegionInfo

urlpatterns = [
    url(r'^/manage/regions$', ListRegionInfo.as_view(), name="list_regions"),
    url(r'^/manage/enterprises$', ListEnterpriseInfoView.as_view(), name="list_enterprises"),
    url(r'^/manage/regions/(?P<region_id>[\w\-]+)$', RegionInfo.as_view(), name="region_info"),
]
