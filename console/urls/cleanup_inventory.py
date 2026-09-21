from django.urls import re_path
from console.views.cleanup_inventory import CleanupInventoryView
from console.views.cleanup_retirement import CleanupRetirementView

urlpatterns = [
    re_path(r'^cleanup/internal/retire/(?P<enterprise_id>[A-Za-z0-9_-]+)/(?P<region_name>[A-Za-z0-9_-]+)$',
            CleanupRetirementView.as_view()),
    re_path(r'^cleanup/internal/inventory/(?P<enterprise_id>[A-Za-z0-9_-]+)/(?P<region_name>[A-Za-z0-9_-]+)$',
            CleanupInventoryView.as_view()),
]
