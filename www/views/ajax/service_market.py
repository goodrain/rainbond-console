# -*- coding: utf8 -*-
import json
import logging
import datetime
import threading

from django.http import JsonResponse
from django.shortcuts import redirect

from www.app_http import AppServiceApi
from www.models import ServiceInfo, TenantEnterprise, PermRelTenant, PublishedGroupServiceRelation, ServiceEvent
from www.utils.crypt import make_uuid
from www.monitorservice.monitorhook import MonitorHook
from www.region import RegionInfo
from www.service_http import RegionServiceApi
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, \
    CodeRepositoriesService
from www.views import AuthedView
from www.views.mixin import LeftSideBarMixin
from www.decorator import perm_required
from www.apiclient.marketclient import MarketOpenAPI
from www.services import app_group_svc

logger = logging.getLogger('default')

regionClient = RegionServiceApi()
appClient = AppServiceApi()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
codeRepositoriesService = CodeRepositoriesService()
market_api = MarketOpenAPI()


class RemoteServiceMarketAjax(AuthedView):
    """远程的服务数据"""

    def post(self, request, *args, **kwargs):
        try:
            res, resp = appClient.getRemoteServices()
            if res.status == 200:
                # logger.debug(resp.data)
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
                    return redirect(
                        '/apps/{0}/service-deploy/?service_key={1}&app_version={2}'.format(self.tenantName, service_key,
                                                                                           app_version))
            # 请求云市数据
            code, base_info, dep_map, error_msg = baseService.download_service_info(service_key, app_version,
                                                                                    action=action)
            if code == 500:
                # 下载失败
                logger.error(error_msg)
                return redirect('/apps/{0}/service/'.format(self.tenantName))
            else:
                # 下载成功
                if service_key != "application":
                    self.downloadImage(base_info)
                # 回写数据
                if callback != "0":
                    appClient.post_statics_tenant(self.tenant.tenant_id, callback)
                # 跳转到页面
                if next_url:
                    # 如果有回跳页面, 直接返回
                    return self.redirect_to(next_url)
                if action != "update":
                    return redirect(
                        '/apps/{0}/service-deploy/?service_key={1}&app_version={2}'.format(self.tenantName, service_key,
                                                                                           app_version))
                else:
                    return redirect('/apps/{0}/service/'.format(self.tenantName))
        except Exception as e:
            logger.exception(e)
        return redirect('/apps/{0}/service/'.format(self.tenantName))

    def downloadImage(self, base_info):
        try:
            download_task = {}
            if base_info.is_slug():
                download_task = {"action": "download_and_deploy", "app_key": base_info.service_key,
                                 "app_version": base_info.version, "namespace": base_info.namespace,
                                 "dep_sids": json.dumps([])}
                for region in RegionInfo.valid_regions():
                    logger.info(region)
                    # TODO v2 api修改
                    regionClient.send_task(region, 'app_slug', json.dumps(download_task))
            else:
                download_task = {"action": "download_and_deploy", "image": base_info.image,
                                 "namespace": base_info.namespace, "dep_sids": json.dumps([])}
                for region in RegionInfo.valid_regions():
                    # TODO v2 api修改
                    regionClient.send_task(region, 'app_image', json.dumps(download_task))
        except Exception as e:
            logger.exception(e)


class BatchDownloadMarketAppGroupTempalteView(LeftSideBarMixin, AuthedView):
    """
    批量下载云市应用组模板
    GET: 获取下载任务进度
    POST: 创建一个新的下载任务
    """

    @perm_required('app_download')
    def get(self, request, *args, **kwargs):
        try:
            perm = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).first()
            enterprise = TenantEnterprise.objects.get(pk=perm.enterprise_id)
        except (TenantEnterprise.DoesNotExist, PermRelTenant.DoesNotExist):
            return JsonResponse(data={'ok': False, 'msg': '企业信息或关系不存在'}, status=200)

        event_list = ServiceEvent.objects.filter(service_id=enterprise.ID, type='market_sync', final_status='')

        event = event_list[0] if event_list.count() > 0 else ServiceEvent()
        return JsonResponse(
            data={'ok': True, 'msg': 'ok', 'event_id': event.event_id, 'final_status': event.final_status,
                  'message': event.message}, status=200)

    @perm_required('app_download')
    def post(self, request, *args, **kwargs):
        try:
            perm = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).first()
            enterprise = TenantEnterprise.objects.get(pk=perm.enterprise_id)
        except (TenantEnterprise.DoesNotExist, PermRelTenant.DoesNotExist):
            return JsonResponse(data={'ok': False, 'msg': '企业信息或关系不存在'}, status=200)

        if ServiceEvent.objects.filter(service_id=enterprise.ID, type='market_sync', final_status='').count() > 0:
            return JsonResponse(data={'ok': False, 'msg': '应用正在同步, 请稍后重试'}, status=200)

        download_event = ServiceEvent(event_id=make_uuid(), service_id=enterprise.ID,
                                      tenant_id=self.tenant.tenant_id, type='market_sync',
                                      status='success', user_name=self.user.nick_name,
                                      start_time=datetime.datetime.now())
        download_event.save()

        t = threading.Thread(target=self.__download, args=(download_event, enterprise, self.tenant))
        t.start()
        return JsonResponse(data={'ok': True}, status=200)

    def __download(self, event, enterprise, tenant):
        # 先获取云市所有免费的组应用列表
        logger.debug('NewMarketSyncTask'.center(90, '-'))
        try:
            app_group_list = market_api.get_service_group_list(tenant.tenant_id)

            total = len(app_group_list)
            succeed = 0
            failed = 0
            failed_msg = []
            message = {'total': total, 'succeed': succeed, 'failed': failed, 'failed_msg': []}
            logger.debug('Free App: {}'.format(total))

            for app_group in app_group_list:
                group_key = app_group['group_key']
                group_version = app_group['group_version']
                group_name = app_group['group_name']
                logger.debug('Download [{}-{}]'.format(group_name, group_version))
                download_group = app_group_svc.download_app_service_group_from_market(tenant.tenant_id,
                                                                                      group_key,
                                                                                      group_version)
                if download_group:
                    succeed += 1
                else:
                    failed += 1
                    failed_msg.append({
                        'group_key': group_key,
                        'group_version': group_version,
                    })

                message.update({
                    'succeed': succeed,
                    'failed': failed,
                    'failed_msg': failed_msg
                })

                # 同步每一个应用的状态进度
                event.message = json.dumps(message)
                event.save()

            event.final_status = 'complete'
            event.end_time = datetime.datetime.now()
            event.save()
        except Exception as e:
            logger.exception(e)

            event.final_status = 'failure'
            event.message = e.message
            event.end_time = datetime.datetime.now()
            event.save()
        logger.debug('NewMarketSyncTask'.center(90, '-'))

    @perm_required('app_download')
    def delete(self, request, *args, **kwargs):
        try:
            # app_service_group_list = app_group_svc.list_app_service_group()
            # for group in app_service_group_list:
            #     app_group_svc.delete_app_service_group(group.group_share_id, group.group_version)

            app_group_svc.delete_app_service_group('d17ff4d5501f575ebfee764f800c49f1', 'V1.0')
        except Exception as e:
            logger.exception(e)

        return JsonResponse(data={'ok': True}, status=200)
