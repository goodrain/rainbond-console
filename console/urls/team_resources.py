# -*- coding: utf-8 -*-
from django.conf.urls import url

from console.views.team_resources import (
    NsResourceTypesView,
    NsResourcesView,
    NsResourceDetailView,
    HelmReleasesView,
    HelmReleaseDetailView,
)

urlpatterns = [
    url(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/ns-resource-types$',
        NsResourceTypesView.as_view()),
    url(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/ns-resources$',
        NsResourcesView.as_view()),
    url(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/ns-resources/(?P<name>[^/]+)$',
        NsResourceDetailView.as_view()),
    url(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/helm/releases$',
        HelmReleasesView.as_view()),
    url(r'^teams/(?P<team_name>[^/]+)/regions/(?P<region_name>[^/]+)/helm/releases/(?P<release_name>[^/]+)$',
        HelmReleaseDetailView.as_view()),
]
