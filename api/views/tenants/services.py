# -*- coding: utf8 -*-
from rest_framework.response import Response
from api.views.base import APIView
from www.models import TenantServiceStatics, Tenants, TenantServiceInfo
from www.service_http import RegionServiceApi

import datetime
import json
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
                flow = data["flow"]
                runing_status = data["status"]
                cnt = TenantServiceStatics.objects.filter(service_id=service_id, time_stamp=time_stamp).count()
                if cnt < 1:
                    ts = TenantServiceStatics(tenant_id=tenant_id, service_id=service_id, node_num=node_num, node_memory=node_memory, time_stamp=time_stamp, storage_disk=storage_disk, net_in=net_in, net_out=net_out, status=runing_status, flow=flow)
                    ts.save()
            except Exception as e:
                logger.exception(e)
        return Response({"ok": True}, status=200)

class TenantHibernateView(APIView):
    '''
    租户休眠
    '''
    allowed_methods = ('put', 'post')
        
    def put(self, request, format=None):
        """
        休眠容器(pause,systemPause,unpause)
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
        logger.debug(tenant_id)
        logger.debug(action)
        try:
            tenant = Tenants.objects.get(tenant_id=tenant_id)
            if action == "pause":
                if tenant.service_status == 1:
                    regionClient.pause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 0
                    tenant.save()
                else:
                    logger.debug(tenant.tenant_name + " don't been paused")
            elif action == "systemPause":
                if tenant.service_status == 0:
                    regionClient.systemPause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 3
                    tenant.save()
                else:
                    logger.debug(tenant.tenant_name + " don't been paused")                
            elif action == 'unpause':
                if tenant.service_status == 0:
                    regionClient.unpause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 1
                    tenant.save()
                elif tenant.service_status == 3:
                    regionClient.systemUnpause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 1
                    tenant.save()
                else:
                    logger.debug(tenant.tenant_name + " don't been unpaused")
        except Exception as e:
            logger.exception(e)
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
                    logger.debug(tenant.tenant_name + " don't been paused")
            elif action == "systemPause":
                if tenant.service_status == 0:
                    regionClient.systemPause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 3
                    tenant.save()
                else:
                    logger.debug(tenant.tenant_name + " don't been paused")                
            elif action == 'unpause':
                if tenant.service_status == 0:
                    regionClient.unpause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 1
                    tenant.save()
                elif tenant.service_status == 3:
                    regionClient.systemUnpause(tenant.region, tenant.tenant_id)
                    tenant.service_status = 1
                    tenant.save()
                else:
                    logger.debug(tenant.tenant_name + " don't been unpaused")
        except Exception as e:
            logger.exception(e)
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
            logger.exception(e)
        return Response({"ok": True}, status=200)
    
class AllTenantView(APIView):
    '''
    租户信息
    '''
    allowed_methods = ('post',)
        
    def post(self, request, format=None):
        """
        获取所有租户信息
        ---
        parameters:
            - name: service_status
              description: 服务状态
              required: true
              type: string
              paramType: form
            - name: pay_type
              description: 租户类型
              required: true
              type: string
              paramType: form
            - name: region
              description: 区域中心
              required: true
              type: string
              paramType: form
            - name: day
              description: 相差天数
              required: false
              type: string
              paramType: form
            
        """
        service_status = request.data.get('service_status', "1")
        pay_type = request.data.get('pay_type', "free")
        region = request.data.get('region', "")
        query_day = request.data.get('day', "0")
        diff_day = int(query_day)
        data = {}
        try:
            if region != "":
                if diff_day != 0:
                    end_time = datetime.datetime.now() + datetime.timedelta(days=diff_day)      
                    tenantList = Tenants.objects.filter(service_status=service_status, pay_type=pay_type, region=region, update_time__lt=end_time)
                    logger.debug(len(tenantList))
                    if len(tenantList) > 0:
                        for tenant in tenantList:
                            data[tenant.tenant_id] = tenant.tenant_name
                else:
                    tenantList = Tenants.objects.filter(service_status=service_status, pay_type=pay_type, region=region)
                    if len(tenantList) > 0:
                        for tenant in tenantList:
                            data[tenant.tenant_id] = tenant.tenant_name
        except Exception as e:
            logger.error(e)
        return Response(data, status=200)
    
    
class TenantView(APIView):
    '''
    租户信息
    '''
    allowed_methods = ('post',)   
    def post(self, request, format=None):
        """
        获取某个租户信息(tenant_id或者tenant_name)
        ---
        parameters:
            - name: tenant_id
              description: 租户ID
              required: false
              type: string
              paramType: form
            - name: tenant_name
              description: 租户名
              required: false
              type: string
              paramType: form
            
        """
        data = {}
        try:
            print request.data
            tenant_id = request.data.get('tenant_id', "")
            tenant_name = request.data.get('tenant_name', "")
            tenant = None
            if tenant_id != "":
                tenant = Tenants.objects.get(tenant_id=tenant_id)
            if tenant is None:
                if tenant_name != "":
                    tenant = Tenants.objects.get(tenant_name=tenant_name)
            if tenant is not None:
                data["tenant_id"] = tenant.tenant_id
                data["tenant_name"] = tenant.tenant_name
                data["region"] = tenant.region
                data["service_status"] = tenant.service_status
                data["pay_type"] = tenant.pay_type
        except Exception as e:
            logger.exception(e)
        return Response(data, status=200)
