# -*- coding: utf8 -*-
from rest_framework.response import Response
from api.views.base import APIView
from www.models import TenantServiceStatics, Tenants, TenantServiceInfo
from www.service_http import RegionServiceApi

import datetime
import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()

class TenantServiceStaticsView(APIView):
    '''
    计费基础数据统计
    '''
    allowed_methods = ('POST',)
        
    def post(self, request, format=None):
        """
        统计租户服务
        ---
        parameters:
            - name: data
              description: 数据列表
              required: true
              type: string
              paramType: body
        """
        datas = request.data
        for data in datas:
            try:
                tenant_id = data["tenant_id"]
                service_id = data["service_id"]
                node_num = data["node_num"]
                node_memory = data["node_memory"]
                time_stamp = data["time_stamp"]
                storage_disk = data["storage_disk"]
                net_in = data["net_in"]
                net_out = data["net_out"]
                cnt = TenantServiceStatics.objects.filter(service_id=service_id, time_stamp=time_stamp).count()
                if cnt < 1:
                    ts = TenantServiceStatics(tenant_id=tenant_id, service_id=service_id, node_num=node_num, node_memory=node_memory, time_stamp=time_stamp, storage_disk=storage_disk, net_in=net_in, net_out=net_out)
                    ts.save()
            except Exception as e:
                logger.error(e)
        return Response({"ok": True}, status=200)

class TenantHibernateView(APIView):
    '''
    租户休眠
    '''
    allowed_methods = ('put', 'post')
        
    def put(self, request, format=None):
        """
        休眠容器(pause,unpause)
        ---
        parameters:
            - name: tenant_id
              description: 租户ID
              required: true
              type: string
              paramType: form
            - name: action
              description: 动作
              required: true
              type: string
              paramType: form
        """
        tenant_id = request.data.get('tenant_id', "")
        action = request.data.get('action', "")
        logger.debug(tenant_id + "==" + action)
        try:
            tenant = Tenants.objects.get(tenant_id=tenant_id)
            if action == "pause":
                if tenant.service_status == 1:
                    regionClient.pause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 0
                    tenant.save()
                else:
                    logger.debug(tenant.tenant_name + " had paused")
            elif action == 'unpause':
                if tenant.service_status == 0:
                    regionClient.unpause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 1
                    tenant.save()
                else:
                    logger.debug(tenant.tenant_name + " not paused")
        except Exception as e:
            logger.error(e)
        return Response({"ok": True}, status=200)
    
    def post(self, request, format=None):
        """
        休眠容器(pause,unpause)
        ---
        parameters:
            - name: tenant_name
              description: 租户名
              required: true
              type: string
              paramType: form
            - name: action
              description: 动作
              required: true
              type: string
              paramType: form
        """
        tenant_name = request.data.get('tenant_name', "")
        action = request.data.get('action', "")
        logger.debug(tenant_name + "==" + action)
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            if action == "pause":
                if tenant.service_status == 1:
                    regionClient.pause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 0
                    tenant.save()
                else:
                    logger.debug(tenant.tenant_name + " had paused")
            elif action == 'unpause':
                if tenant.service_status == 0:
                    regionClient.unpause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 1
                    tenant.save()
                else:
                    logger.debug(tenant.tenant_name + " not paused")
        except Exception as e:
            logger.error(e)
        return Response({"ok": True}, status=200)
    
    
class TenantCloseRestartView(APIView):
    '''
    租户关闭、重启
    '''
    allowed_methods = ('put',)
        
    def put(self, request, format=None):
        """
        租户关闭重启(close,restart)
        ---
        parameters:
            - name: tenant_id
              description: 租户ID
              required: true
              type: string
              paramType: form
            - name: action
              description: 动作
              required: true
              type: string
              paramType: form
        """
        tenant_id = request.data.get('tenant_id', "")
        action = request.data.get('action', "")
        logger.debug(tenant_id + "==" + action)
        try:
            tenant = Tenants.objects.get(tenant_id=tenant_id)
            tenantServices = TenantServiceInfo.objects.filter(tenant_id=tenant_id)
            if len(tenantServices) > 0:
                if action == "close":
                    for tenantService in tenantServices:
                        regionClient.stop(tenant.region, tenantService.service_id)
                    if tenant.pay_type == "payed":
                        tenant.service_status = 2
                        tenant.save()
                elif action == "restart":
                    for tenantService in tenantServices:
                        tenantService.deploy_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                        tenantService.save()
                        body = {}
                        body["deploy_version"] = tenantService.deploy_version
                        regionClient.restart(tenant.region, tenantService.service_id, json.dumps(body))
                    tenant.service_status = 1
                    tenant.save()
        except Exception as e:
            logger.error(e)
        return Response({"ok": True}, status=200)
    
