# -*- coding: utf8 -*-
from django.http import JsonResponse

from www.decorator import perm_required
from www.models import ServiceGroup, ServiceGroupRelation
from www.views import AuthedView
import logging
from www.views.mixin import LeftSideBarMixin

logger = logging.getLogger('default')


class GroupServicesView(LeftSideBarMixin, AuthedView):
    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            service_list = self.get_service_list()
            service_map = {service.service_id: service for service in service_list}
            sgrs = ServiceGroupRelation.objects.filter(tenant_id=self.tenant.tenant_id,
                                                       region_name=self.response_region)
            group_services = {}
            for sgr in sgrs:
                group_id = sgr.group_id
                # 查找组对应的信息是否存在
                services = group_services.get(group_id, None)
                # 不存在创建列表
                if not services:
                    services = []
                service = service_map.pop(sgr.service_id, None)
                if service:
                    services.append({"service_id": service.service_id,
                                     "service_alias": service.service_alias,
                                     "service_cname": service.service_cname})
                group_services[group_id] = services
            # 未分组数据
            values = service_map.values()
            ungrouped = []
            for val in values:
                ungrouped.append({"service_id":val.service_id,
                                  "service_alias":val.service_alias,
                                  "service_cname":val.service_cname})

            group_services[-1] = ungrouped
            result.update(group_services)
        except Exception as e:
            logger.exception(e)
        return JsonResponse(result)

