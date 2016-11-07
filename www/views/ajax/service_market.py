# -*- coding: utf8 -*-
import json

from django.http import JsonResponse
from www.views import AuthedView

from www.models import (ServiceInfo, AppServicePort, AppServiceEnv,
                        AppServiceRelation, ServiceExtendMethod,
                        AppServiceVolume)
from www.service_http import RegionServiceApi
from www.app_http import AppServiceApi
from django.conf import settings
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, CodeRepositoriesService
from www.monitorservice.monitorhook import MonitorHook
from django.shortcuts import redirect
from www.region import RegionInfo
from www.utils import sn

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
                #logger.debug(resp.data)
                return JsonResponse({"success": True, "data": resp.data, "info": u"查询成功"})
            else:
                return JsonResponse({"success": False, "info": u"查询数据失败"})
        except Exception as e:
            logger.exception(e)
            return JsonResponse({"success": True, "info": u"查询数据失败"})

    def get(self, request, *args, **kwargs):
        """安装远程服务"""
        try:
            service_key = request.GET.get('service_key')
            app_version = request.GET.get('app_version')
            callback = request.GET.get('callback', "0")
            action = request.GET.get('action', '')
            next_url = request.GET.get("next_url")
            update_version = request.GET.get('update_version', 1)
            if action != "update":
                num = ServiceInfo.objects.filter(service_key=service_key, version=app_version).count()
                if num > 0:
                    # 回写到云市
                    if callback != "0":
                        appClient.post_statics_tenant(self.tenant.tenant_id, callback)
                    return redirect('/apps/{0}/service-deploy/?service_key={1}&app_version={2}'.format(self.tenantName, service_key, app_version))
            # 请求云市数据
            code, base_info, dep_map, error_msg = baseService.download_service_info(service_key, app_version, action=action)
            if code == 500:
                # 下载失败
                logger.error(error_msg)
                return redirect('/apps/{0}/service/'.format(self.tenantName))
            else:
                # 下载成功
                self.downloadImage(base_info)
                # 回写数据
                if callback != "0":
                    appClient.post_statics_tenant(self.tenant.tenant_id, callback)
                # 跳转到页面
                if next_url:
                    # 如果有回跳页面, 直接返回
                    return self.redirect_to(next_url)
                if action != "update":
                    return redirect('/apps/{0}/service-deploy/?service_key={1}&app_version={2}'.format(self.tenantName, service_key, app_version))
                else:
                    return redirect('/apps/{0}/service/'.format(self.tenantName))
        except Exception as e:
            logger.exception(e)
        return redirect('/apps/{0}/service/'.format(self.tenantName))
    
    def downloadImage(self, base_info):
        try:
            download_task = {}
            if base_info.is_slug():
                download_task = {"action": "download_and_deploy", "app_key": base_info.service_key, "app_version": base_info.version, "namespace": base_info.namespace, "dep_sids": json.dumps([])}
                for region in RegionInfo.valid_regions():
                    logger.info(region)
                    regionClient.send_task(region, 'app_slug', json.dumps(download_task))
            else:
                download_task = {"action": "download_and_deploy", "image": base_info.image, "namespace": base_info.namespace, "dep_sids": json.dumps([])}
                for region in RegionInfo.valid_regions():
                    regionClient.send_task(region, 'app_image', json.dumps(download_task))
        except Exception as e:  
            logger.exception(e)

