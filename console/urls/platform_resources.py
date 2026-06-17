# -*- coding: utf-8 -*-
from django.urls import re_path

from console.views.platform_resources.cluster import (
    PlatformResourceTypesView,
    PlatformResourcesView,
    PlatformResourceDetailView,
    StorageClassesView,
    StorageClassDetailView,
    PersistentVolumesView,
    PersistentVolumeDetailView,
    StorageConfigView,
)

urlpatterns = [
    re_path(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/platform-resources/types$',
        PlatformResourceTypesView.as_view()),
    re_path(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/platform-resources$',
        PlatformResourcesView.as_view()),
    re_path(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/platform-resources/(?P<name>[^/]+)$',
        PlatformResourceDetailView.as_view()),
    re_path(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/storageclasses$',
        StorageClassesView.as_view()),
    re_path(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/storageclasses/(?P<name>[^/]+)$',
        StorageClassDetailView.as_view()),
    re_path(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/persistentvolumes$',
        PersistentVolumesView.as_view()),
    re_path(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/persistentvolumes/(?P<name>[^/]+)$',
        PersistentVolumeDetailView.as_view()),
    re_path(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/storage-config$',
        StorageConfigView.as_view()),
]
