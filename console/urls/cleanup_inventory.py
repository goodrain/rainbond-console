from django.urls import re_path
from console.views.cleanup_inventory import CleanupInventoryView
from console.views.cleanup_retirement import CleanupRetirementView
from console.views.cleanup_core_bridge import CleanupCoreBridgeView, CleanupSystemCoreBridgeView

urlpatterns = [
    re_path(r'^cleanup/internal/system-coordination/(?P<enterprise_id>[A-Za-z0-9_-]+)/(?P<region_name>[A-Za-z0-9_-]+)$',
            CleanupSystemCoreBridgeView.as_view()),
    re_path(r'^cleanup/internal/coordination/(?P<enterprise_id>[A-Za-z0-9_-]+)/(?P<region_name>[A-Za-z0-9_-]+)$',
            CleanupCoreBridgeView.as_view()),
    re_path(r'^cleanup/internal/retire/(?P<enterprise_id>[A-Za-z0-9_-]+)/(?P<region_name>[A-Za-z0-9_-]+)$',
            CleanupRetirementView.as_view()),
    re_path(r'^cleanup/internal/inventory/(?P<enterprise_id>[A-Za-z0-9_-]+)/(?P<region_name>[A-Za-z0-9_-]+)$',
            CleanupInventoryView.as_view()),
]
