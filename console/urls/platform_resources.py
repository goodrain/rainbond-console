# -*- coding: utf-8 -*-
"""
Platform resources URL configuration.
"""
from django.conf.urls import url

from console.views.platform_resources.storage import (
    StorageClassListView,
    StorageClassDetailView,
    PersistentVolumeListView,
)
from console.views.platform_resources.cluster_resources import (
    NodeListView,
    NodeDetailView,
)
from console.views.platform_resources.discovery import ServiceListView

urlpatterns = [
    # Storage resources (platform admin only)
    url(r'^regions/(?P<region_name>[\w-]+)/storageclasses$',
        StorageClassListView.as_view()),
    url(r'^regions/(?P<region_name>[\w-]+)/storageclasses/(?P<name>[\w.-]+)$',
        StorageClassDetailView.as_view()),
    url(r'^regions/(?P<region_name>[\w-]+)/persistentvolumes$',
        PersistentVolumeListView.as_view()),

    # Cluster resources (platform admin only)
    url(r'^regions/(?P<region_name>[\w-]+)/nodes$',
        NodeListView.as_view()),
    url(r'^regions/(?P<region_name>[\w-]+)/nodes/(?P<name>[\w.-]+)$',
        NodeDetailView.as_view()),

    # Service discovery (team-scoped)
    url(r'^teams/(?P<team_name>[\w-]+)/regions/(?P<region_name>[\w-]+)/services$',
        ServiceListView.as_view()),
]
