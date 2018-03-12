# -*- coding: utf8 -*-

import logging

from django.http import JsonResponse
from django.views.decorators.cache import never_cache

from share.manager.region_provier import RegionProviderManager
from www.decorator import perm_required
from www.models import ServiceGroupRelation, ServiceEvent
from www.monitorservice.monitorhook import MonitorHook
from www.service_http import RegionServiceApi
from www.tenantservice.baseservice import CodeRepositoriesService
from www.utils.crypt import make_uuid
from www.views import AuthedView
from www.views.mixin import LeftSideBarMixin

logger = logging.getLogger('default')

monitorhook = MonitorHook()
rpmManager = RegionProviderManager()
codeRepositoriesService = CodeRepositoriesService()


class BasicInfoEditView(LeftSideBarMixin, AuthedView):
    @never_cache
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        service_name = request.POST.get("service_name", None)
        group_id = request.POST.get("group_id", None)
        git_url = request.POST.get("git_url", None)
        logger.debug("update service info: new service name {0},group_id {1},git_url {2}".format(service_name, group_id,
                                                                                                 git_url))
        result = {}
        service_id = self.service.service_id
        try:
            old_name = self.service.service_cname
            # 如果新名字和原来的不同,就更新
            if old_name != service_name and service_name is not None:
                self.service.service_cname = service_name
                self.service.save()
            # 修改组名
            if group_id is not None:
                group_id = int(group_id)
                old_group_id = -1
                try:
                    sgr = ServiceGroupRelation.objects.get(service_id=service_id, tenant_id=self.tenant.tenant_id)
                    old_group_id = sgr.group_id
                except ServiceGroupRelation.DoesNotExist:
                    pass
                if group_id != old_group_id:
                    if group_id == -1:
                        ServiceGroupRelation.objects.filter(service_id=service_id).delete()
                    elif ServiceGroupRelation.objects.filter(service_id=service_id).count() > 0:
                        ServiceGroupRelation.objects.filter(service_id=service_id,
                                                            tenant_id=self.tenant.tenant_id).update(group_id=group_id)
                    else:
                        ServiceGroupRelation.objects.create(service_id=service_id, group_id=group_id,
                                                            tenant_id=self.tenant.tenant_id,
                                                            region_name=self.response_region)

            if git_url and git_url != self.service.git_url and self.service.category == "application":
                # 修改仓库地址
                self.service.git_url = git_url
                self.service.git_project_id = 0
                self.service.code_version = "master"

                event_id = self.create_gitChange_events(self.service)

                codeRepositoriesService.codeCheck(self.service, check_type="git_change",event_id=event_id)
            else:
                logger.debug("代码仓库地址未发生修改")
            result["ok"] = True
            result["msg"] = "修改成功"
        except Exception as e:
            logger.error(e)
            result["ok"] = False
            result["msg"] = "失败"
        return JsonResponse(result, status=200)

    def create_gitChange_events(self,service):
        try:
            import datetime
            event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                                 tenant_id=self.tenant.tenant_id, type="git-change",
                                 deploy_version=service.deploy_version,
                                 old_deploy_version=service.deploy_version,
                                 user_name=self.user.nick_name, start_time=datetime.datetime.now())
            event.save()
            self.event = event
            return event.event_id
        except Exception as e:
            self.event = None
            logger.error(e)