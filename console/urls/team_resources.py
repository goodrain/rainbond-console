# -*- coding: utf-8 -*-
from django.urls import re_path

from console.views.team_resources import (
    NsResourceTypesView,
    NsResourcesView,
    TeamComponentsView,
    NsResourceDetailView,
    HelmReleasesView,
    HelmChartPreviewView,
    HelmReleaseDetailView,
    HelmReleaseHistoryView,
    HelmReleaseRollbackView,
    ResourceCenterWorkloadDetailView,
    ResourceCenterPodDetailView,
    ResourceCenterEventsView,
    ResourceCenterPodLogsView,
    ResourceCenterWSInfoView,
)

urlpatterns = [
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/components$',
        TeamComponentsView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/ns-resource-types$',
        NsResourceTypesView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/ns-resources$',
        NsResourcesView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/ns-resources/(?P<name>[^/]+)$',
        NsResourceDetailView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/helm/releases$',
        HelmReleasesView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/helm/chart-preview$',
        HelmChartPreviewView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/helm/releases/(?P<release_name>[^/]+)$',
        HelmReleaseDetailView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/helm/releases/(?P<release_name>[^/]+)/history$',
        HelmReleaseHistoryView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/helm/releases/(?P<release_name>[^/]+)/rollback$',
        HelmReleaseRollbackView.as_view()),
    re_path(
        r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/resource-center/workloads/'
        r'(?P<resource>[^/]+)/(?P<name>[^/]+)$',
        ResourceCenterWorkloadDetailView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/resource-center/pods/(?P<pod_name>[^/]+)$',
        ResourceCenterPodDetailView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/resource-center/events$',
        ResourceCenterEventsView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/resource-center/pods/(?P<pod_name>[^/]+)/logs$',
        ResourceCenterPodLogsView.as_view()),
    re_path(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/resource-center/ws-info$',
        ResourceCenterWSInfoView.as_view()),
]
