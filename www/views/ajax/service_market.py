# -*- coding: utf8 -*-
import json

from django.http import JsonResponse
from www.views import AuthedView

from www.models import (ServiceInfo, AppServicePort, AppServiceEnv, AppServiceRelation, ServiceExtendMethod)
from www.service_http import RegionServiceApi
from www.app_http import AppServiceApi
from django.conf import settings
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, CodeRepositoriesService
from www.monitorservice.monitorhook import MonitorHook
from django.shortcuts import redirect

import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()
appClient = AppServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
codeRepositoriesService = CodeRepositoriesService()


class RemoteServiceMarketAjax(AuthedView):
    """远程的服务数据"""
    def post(self, request, *args, **kwargs):
        try:
            res, resp = appClient.getRemoteServices()
            if res.status == 200:
                logger.debug(resp.data)
                return JsonResponse({"success": True, "data": resp.data, "info": u"查询成功"})
            else:
                return JsonResponse({"success": False, "info": u"查询数据失败"})
        except Exception as e:
            logger.exception(e)
            return JsonResponse({"success": True, "info": u"查询数据失败"})





    def get(self, request, *args, **kwargs):
        """安装远程服务"""
        service_key = request.GET.get('service_key')
        app_version = request.GET.get('app_version')
        num = ServiceInfo.objects.filter(service_key=service_key, version=app_version).count()
        if num > 0:
            return redirect('/apps/{0}/service-deploy/?service_key={1}'.format(self.tenantName, service_key))
        else:
            # 请求云市数据
            all_data = {
                'service_key': service_key,
                'app_version': app_version,
                'cloud_assistant': settings.CLOUD_ASSISTANT,
            }
            data = json.dumps(all_data)
            logger.debug('post service json data={}'.format(data))
            res, resp = appClient.getServiceData(body=data)
            if res.status == 200:
                json_data = json.loads(resp.data)
                service_data = json_data.get("service", None)
                if not service_data:
                    logger.error("no service data!")
                    return redirect('/apps/{0}/service/'.format(self.tenantName))
                # add service
                base_info = ServiceInfo()
                base_info.service_key = service_data.get("service_key")
                base_info.publisher = service_data.get("publisher")
                base_info.service_name = service_data.get("service_name")
                base_info.pic = service_data.get("pic")
                base_info.info = service_data.get("info")
                base_info.desc = service_data.get("desc")
                base_info.status = service_data.get("status")
                base_info.category = service_data.get("category")
                base_info.is_service = service_data.get("is_service")
                base_info.is_web_service = service_data.get("is_web_service")
                base_info.version = service_data.get("version")
                base_info.update_version = service_data.get("update_version")
                base_info.image = service_data.get("image")
                base_info.slug = service_data.get("slug")
                base_info.extend_method = service_data.get("extend_method")
                base_info.cmd = service_data.get("cmd")
                base_info.setting = service_data.get("setting")
                base_info.env = service_data.get("env")
                base_info.dependecy = service_data.get("dependecy")
                base_info.min_node = service_data.get("min_node")
                base_info.min_cpu = service_data.get("min_cpu")
                base_info.min_memory = service_data.get("min_memory")
                base_info.inner_port = service_data.get("inner_port")
                base_info.volume_mount_path = service_data.get("volume_mount_path")
                base_info.service_type = service_data.get("service_type")
                base_info.is_init_accout = service_data.get("is_init_accout")
                base_info.save()
                logger.debug('---add app service---ok---')
                # 保存service_env
                pre_list = json_data.get('pre_list', None)
                suf_list = json_data.get('suf_list', None)
                env_list = json_data.get('env_list', None)
                port_list = json_data.get('port_list', None)
                extend_list = json_data.get('extend_list', None)
                # 新增环境参数
                if env_list:
                    env_data = []
                    for env in env_list:
                        app_env = AppServiceEnv(service_key=env.get("service_key"),
                                                app_version=env.get("app_version"),
                                                name=env.get("name"),
                                                attr_name=env.get("attr_name"),
                                                attr_value=env.get("attr_value"),
                                                scope=env.get("scope"),
                                                is_change=env.get("is_change"),
                                                container_port=env.get("container_port"))
                        env_data.append(app_env)
                    AppServiceEnv.objects.bulk_create(env_data)
                logger.debug('---add app service env---ok---')
                # 端口信息
                if port_list:
                    port_data = []
                    for port in port_list:
                        app_port = AppServicePort(service_key=port.get("service_key"),
                                                  app_version=port.get("app_version"),
                                                  container_port=port.get("container_port"),
                                                  protocol=port.get("protocol"),
                                                  port_alias=port.get("port_alias"),
                                                  is_inner_service=port.get("is_inner_service"),
                                                  is_outer_service=port.get("is_outer_service"))
                        port_data.append(app_port)
                    AppServicePort.objects.bulk_create(port_data)
                logger.debug('---add app service port---ok---')
                # 扩展信息
                if extend_list:
                    extend_data = []
                    for extend in extend_list:
                        app_port = ServiceExtendMethod(service_key=extend.get("service_key"),
                                                       app_version=extend.get("app_version"),
                                                       min_node=extend.get("min_node"),
                                                       max_node=extend.get("max_node"),
                                                       step_node=extend.get("step_node"),
                                                       min_memory=extend.get("min_memory"),
                                                       max_memory=extend.get("max_memory"),
                                                       step_memory=extend.get("step_memory"))
                        extend_data.append(app_port)
                    ServiceExtendMethod.objects.bulk_create(extend_data)
                logger.debug('---add app service extend---ok---')
                # 服务依赖关系
                relation_data = []
                if pre_list:
                    for relation in pre_list:
                        app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                          app_version=relation.get("app_version"),
                                                          app_alias=relation.get("app_alias"),
                                                          dep_service_key=relation.get("dep_service_key"),
                                                          dep_app_version=relation.get("dep_app_version"),
                                                          dep_app_alias=relation.get("dep_app_alias"))
                        relation_data.append(app_relation)
                if suf_list:
                    for relation in suf_list:
                        app_relation = AppServiceRelation(service_key=relation.get("service_key"),
                                                          app_version=relation.get("app_version"),
                                                          app_alias=relation.get("app_alias"),
                                                          dep_service_key=relation.get("dep_service_key"),
                                                          dep_app_version=relation.get("dep_app_version"),
                                                          dep_app_alias=relation.get("dep_app_alias"))
                        relation_data.append(app_relation)
                AppServiceRelation.objects.bulk_create(relation_data)
                logger.debug('---add app service relation---ok---')
                # 跳转到页面
                return redirect('/apps/{0}/service-deploy/?service_key={1}'.format(self.tenantName, service_key))
            else:
                logger.error(' error !')
                return redirect('/apps/{0}/service/'.format(self.tenantName))
