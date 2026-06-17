# -*- coding: utf-8 -*-
# creater by: barnett
from django.urls import re_path
from openapi.v2.views.region_view import ListRegionInfo
from openapi.v2.views.enterprise_view import ListEnterpriseInfoView, EnterpriseSourceView
from openapi.v2.views.region_view import RegionInfo

urlpatterns = [
    re_path(r'^/manage/regions$', ListRegionInfo.as_view(), name="list_regions"),
    re_path(r'^/manage/enterprises$', ListEnterpriseInfoView.as_view(), name="list_enterprises"),
    re_path(r'^/manage/enterprises/(?P<eid>[\w\-]+)/resource$', EnterpriseSourceView.as_view(), name="ent_info"),
    re_path(r'^/manage/regions/(?P<region_id>[\w\-]+)$', RegionInfo.as_view(), name="region_info"),
]
