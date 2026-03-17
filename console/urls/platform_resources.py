# -*- coding: utf-8 -*-
from django.conf.urls import url

from console.views.platform_resources.cluster import (
    PlatformResourceTypesView,
    PlatformResourcesView,
    PlatformResourceDetailView,
    StorageClassesView,
    StorageClassDetailView,
    PersistentVolumesView,
    PersistentVolumeDetailView,
)

urlpatterns = [
    url(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/platform-resources/types$',
        PlatformResourceTypesView.as_view()),
    url(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/platform-resources$',
        PlatformResourcesView.as_view()),
    url(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/platform-resources/(?P<name>[^/]+)$',
        PlatformResourceDetailView.as_view()),
    url(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/storageclasses$',
        StorageClassesView.as_view()),
    url(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/storageclasses/(?P<name>[^/]+)$',
        StorageClassDetailView.as_view()),
    url(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/persistentvolumes$',
        PersistentVolumesView.as_view()),
    url(r'^enterprise/(?P<eid>[^/]+)/platform/regions/(?P<region>[^/]+)/persistentvolumes/(?P<name>[^/]+)$',
        PersistentVolumeDetailView.as_view()),
]
