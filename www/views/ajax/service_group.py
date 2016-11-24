# -*- coding: utf8 -*-
import datetime
import json
import re

from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required

from www.service_http import RegionServiceApi
from django.conf import settings
from goodrain_web.decorator import method_perf_time

import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()

class AddGroupView(LeftSideBarMixin, AuthedView):
    """添加组"""

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        group_name = request.POST.get("group_name", "")
        try:
            if group_name.strip == "":
                return JsonResponse({"ok": False, "info": "参数错误"})
            if ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region,
                                           group_name=group_name).exists():
                return JsonResponse({"ok": False, "info": "组名已存在"})
            ServiceGroup.objects.create(tenant_id=self.tenant.tenant_id, region_name=self.response_region,
                                        group_name=group_name)
            return JsonResponse({'ok': True, "info": "修改成功"})
        except Exception as e:
            print e
            logger.exception(e)


class UpdateGroupView(LeftSideBarMixin, AuthedView):
    """修改组"""

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        new_group_name = request.POST.get("new_group_name", "")
        group_id = request.POST.get("group_id")
        try:
            if new_group_name.strip == "" or group_id.strip == "":
                return JsonResponse({"ok": False, "info": "参数错误"})
            ServiceGroup.objects.filter(ID=group_id).update(group_name=new_group_name)
            return JsonResponse({"ok": True, "info": "修改成功"})
        except Exception as e:
            logger.exception(e)


class DeleteGroupView(LeftSideBarMixin, AuthedView):
    """删除组"""

    @perm_required('manage_service')
    def post(self, request, *args, **kwargs):
        group_id = request.POST.get("group_id")
        try:
            ServiceGroup.objects.filter(ID=group_id).delete()
            ServiceGroupRelation.objects.filter(group_id=group_id).delete()
            return JsonResponse({"ok": True, "info": "删除成功"})
        except Exception as e:
            logger.exception(e)


class UpdateServiceGroupView(LeftSideBarMixin, AuthedView):
    """修改服务所在的组"""

    def post(self, request, *args, **kwargs):
        group_id = request.POST.get("group_id", "")
        service_id = request.POST.get("service_id", "")
        try:
            if group_id.strip == "" or service_id.strip == "":
                return JsonResponse({"ok": False, "info": "参数错误"})
            if ServiceGroupRelation.objects.filter(service_id=service_id).count() > 0:
                ServiceGroupRelation.objects.filter(service_id=service_id).update(group_id=group_id)
            else:
                ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id)
            return JsonResponse({"ok": True, "info": "修改成功"})
        except Exception as e:
            logger.exception(e)