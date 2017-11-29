# -*- coding: utf8 -*-
from rest_framework.response import Response

from www.models import Tenants, TenantServiceInfo, ServiceInfo, \
    TenantServiceAuth, TenantServiceEnvVar, TenantServiceRelation, \
    TenantServiceVolume
from www.utils import crypt
from django.conf import settings
import json
from django.db.models import Q

from openapi.views.base import BaseAPIView
from openapi.controllers.openservicemanager import OpenTenantServiceManager
manager = OpenTenantServiceManager()

import logging
logger = logging.getLogger("default")


class CloudServiceVersionView(BaseAPIView):

    allowed_methods = ('POST',)

    def post(self, request, *args, **kwargs):
        """
        查询云市服务的版本信息
        ---
        parameters:
            - name: service_ids
              description: 服务ID
              required: true
              type: string
              paramType: form
        """
        service_ids = request.data.get("service_ids", None)
        if service_ids is None:
            return Response(status=405, data={"success": False, "msg": u"租户名称为空"})
        logger.debug("openapi.cloudservice", "now create service: service_ids:{0}".format(service_ids))
        #
        tmp_ids = service_ids.split(",")
        tenant_service_list = TenantServiceInfo.objects.filter(service_id__in=tmp_ids)
        service_key_list = [x.service_key for x in list(tenant_service_list)]
        # service_query = Q()
        # for tenant_service in list(tenant_service_list):
        # service_query = service_query|(Q(service_key=tenant_service.service_key) & Q(version=tenant_service.version))
        service_list = ServiceInfo.objects.filter(service_key__in=service_key_list)
        version_map = {}
        for service in list(service_list):
            service_key = service.service_key
            version = service.version
            if version_map.has_key(service_key):
                old_version = version_map.get(service_key)
                if old_version > version:
                    version_map[service_key] = old_version
            else:
                version_map[service_key] = version
        # version_map = {x["service_key"]: x["version"] for x in list(service_list)}
        return Response(status=200, data={"success": True, "data": json.dumps(version_map)})


