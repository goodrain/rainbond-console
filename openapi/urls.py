# -*- coding: utf-8 -*-
# creater by: barnett
from django.conf.urls import url
from openapi.views.region_view import ListRegionInfo
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from openapi.auth.permissions import OpenAPIPermissions
from openapi.auth.authentication import OpenAPIAuthentication

schema_view = get_schema_view(
   openapi.Info(
      title="Rainbond Open API",
      default_version='v1',
      description="Rainbond open api",
      terms_of_service="https://www.rainbond.com",
      contact=openapi.Contact(email="barnett@goodrain.com"),
      license=openapi.License(name="LGPL License"),
   ),
   public=False,
   permission_classes=(OpenAPIPermissions,),
   authentication_classes=(OpenAPIAuthentication,),
)

urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    url(r'^v1/regions', ListRegionInfo.as_view())
]
