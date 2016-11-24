# -*- coding: utf8 -*-
import datetime
import json
import re

from django.http import JsonResponse
from www.views import AuthedView
# from www.decorator import perm_required
from www.models import ServiceGroupRelation, \
    TenantServiceInfo, \
    TenantServiceRelation, \
    ServiceGroup

import logging
logger = logging.getLogger('default')


class TopologicalGraphView(AuthedView):

    def get(self, request, group_id, *args, **kwargs):
        """根据group的id获取group的详细信息"""
        # group_id = request.GET.get("group_id", None)
        result = {}
        logger.debug("query topological graph from:{0}".format(group_id))
        if group_id is None or not group_id.isdigit():
            result["status"] = 501
            result["msg"] = "group id is missing or not digit!"
            return JsonResponse(result, status=501)

        tenant_id = self.tenant.tenant_id
        group_count = ServiceGroup.objects.filter(tenant_id=tenant_id, ID=group_id).count()
        if group_count == 0:
            result["status"] = 502
            result["msg"] = "group is not yours!"
            return JsonResponse(result, status=502)

        # 根据group_id获取group下的信息
        service_group_relation_list = ServiceGroupRelation.objects.filter(group_id=group_id)
        service_id_list = [x.service_id for x in service_group_relation_list]
        # 查询服务依赖信息
        service_relation_list = TenantServiceRelation.objects.filter(service_id__in=service_id_list)
        dep_service_id_list = [x.dep_service_id for x in service_relation_list]

        # 查询服务、依赖服务信息
        all_service_id_list = list(set(dep_service_id_list).union(set(service_id_list)))
        service_list = TenantServiceInfo.objects.filter(service_id__in=all_service_id_list)
        service_map = {x.service_id: x for x in service_list}
        json_data = {}
        for service_info in service_list:
            json_data[service_info.service_cname] = {
                "service_id": service_info.service_id,
                "service_cname": service_info.service_cname,
                "service_alias": service_info.service_alias,
            }

        json_svg = {}
        for service_relation in service_relation_list:
            tmp_id = service_relation.service_id
            tmp_dep_id = service_relation.dep_service_id
            tmp_info = service_map.get(tmp_id)
            tmp_dep_info = service_map.get(tmp_dep_id)
            # 依赖服务的cname
            tmp_info_relation = []
            if tmp_info.service_cname in json_svg.keys():
                tmp_info_relation = json_svg.get(tmp_info.service_cname)
            tmp_info_relation.append(tmp_dep_info.service_cname)
            json_svg[tmp_info.service_cname] = tmp_info_relation
        # dep service info
        for dep_service_id in dep_service_id_list:
            tmp_info = service_map.get(dep_service_id)
            # 依赖服务的cname
            if tmp_info.service_cname not in json_svg.keys():
                json_svg[tmp_info.service_cname] = []

        result["status"] = 200
        result["json_data"] = json_data
        result["json_svg"] = json_svg
        return JsonResponse(result, status=200)


