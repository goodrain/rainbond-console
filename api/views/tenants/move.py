# -*- coding: utf8 -*-
import json
import datetime

from rest_framework.response import Response
from api.views.base import APIView
from api.serializers import TenantMoveSerializer

from www.models import Tenants, TenantRegionInfo, TenantServiceInfo, TenantServiceRelation, ServiceDomain
from www.views import RegionOperateMixin
from www.tenantservice.baseservice import BaseTenantService
from www.service_http import RegionServiceApi

import logging
logger = logging.getLogger('default')

regionClient = RegionServiceApi()
baseService = BaseTenantService()


def make_deploy_version(self):
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')


class TenantStopView(APIView, RegionOperateMixin):

    '''
    停止服务并做迁移准备
    '''
    allowed_methods = ('POST',)

    def post(self, request, tenantId, format=None):
        """
        在新的region重建服务
        ---
        serializer: TenantMoveSerializer
        """
        serializer = TenantMoveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        source_region = serializer.data.get('source_region')
        dest_region = serializer.data.get('dest_region')

        logger.info("tenant.move", "prepare to move all services from {0} to {1} for tenant {2}".format(
            source_region, dest_region, tenantId))

        try:
            tenant = Tenants.objects.get(tenant_id=tenantId)
            tenant_source_region = TenantRegionInfo.objects.get(tenant_id=tenantId, region_name=source_region)
            tenant_dest_region, created = TenantRegionInfo.objects.get_or_create(tenant_id=tenantId, region_name=dest_region)
            if created or not tenant_dest_region.is_active:
                logger.info("tenant.move", "init region {0} for tenant {1} for move".format(dest_region, tenant.tenant_name))
                success = self.init_for_region(dest_region, tenant.tenant_name, tenant.tenant_id)
                tenant_dest_region.is_active = True if success else False
                tenant_dest_region.service_status = tenant_source_region.service_status
                tenant_dest_region.save()
        except Tenants.DoesNotExist:
            return Response({"ok": False, "info": "tenant match {0} not found".format(tenantId)}, status=400)
        except TenantRegionInfo.DoesNotExist, e:
            return Response({"ok": False, "info": "tenant_region not found: {0}".format(e.__str__())}, status=400)
        except Exception, e:
            logger.exception('tenant.move', e)
            return Response({"ok": False, "info": e.__str__()}, status=500)

        if tenant_dest_region.is_active:
            report = self.stop_and_recreate_services(tenant, source_region, dest_region)
            if report['ok']:
                return Response(report, status=200)
            else:
                return Response(report, status=500)
        else:
            return Response({"ok": False, "info": "dest_region init is not ready"}, status=500)

    def stop_and_recreate_services(self, tenant, source_region, dest_region):
        report = {"ok": True, "moving_services": []}
        moving_services = TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id, service_region=source_region)

        try:
            # 关闭源机房的全部服务
            for service in moving_services:
                regionClient.stop(source_region, service.service_id)
                logger.info("tenant.move", "stop service {0}".format(service.service_id))

            # 在目标机房生成服务以及环境变量
            for service in moving_services:
                baseService.create_region_service(service, tenant.tenant_name, dest_region, do_deploy=False)
                logger.info("tenant.move", "copy service {0} to region {1}".format(service.service_id, dest_region))
                baseService.create_service_env(tenant.tenant_id, service.service_id, dest_region)
                logger.info("tenant.move", "copy service env of {0} to region {1}".format(service.service_id, dest_region))
                report['moving_services'].append(service.service_id)

            # 在目标机房生成服务依赖关系
            ids = map(lambda s: s.service_id, moving_services)
            service_relations = TenantServiceRelation.objects.filter(service_id__in=ids)
            for relation in service_relations:
                task = {
                    "dep_service_id": relation.dep_service_id,
                    "tenant_id": relation.tenant_id,
                    "dep_service_type": relation.dep_service_type
                }
                service_id = relation.service_id
                regionClient.createServiceDependency(dest_region, service_id, json.dumps(task))
                logger.info("tenant.move", "copy relation {0} to region {1}".format(task, dest_region))
        except Exception, e:
            logger.exception("tenant.move", e)
            report.update({"ok": False, "info": e.__str__()})

        return report


class TenantStartView(APIView):

    '''
    启动迁移后的服务
    '''
    allowed_methods = ('POST',)

    def post(self, request, tenantId, format=None):
        """
        在新的region启动服务
        ---
        serializer: TenantMoveSerializer
        """
        serializer = TenantMoveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        source_region = serializer.data.get('source_region')
        dest_region = serializer.data.get('dest_region')

        logger.info("tenant.move", "start all services on region {0} for tenant {1}".format(dest_region, tenantId))

        try:
            tenant = Tenants.objects.get(tenant_id=tenantId)
            tenant_dest_region = TenantRegionInfo.objects.get(tenant_id=tenantId, region_name=dest_region)
            if not tenant_dest_region.is_active:
                msg = "region {0} for tenant {1} is not active".format(dest_region, tenant.tenant_name)
                logger.info("tenant.move", msg)
                return Response({"ok": False, "info": msg}, status=500)
        except Tenants.DoesNotExist:
            return Response({"ok": False, "info": "tenant match {0} not found".format(tenantId)}, status=400)
        except TenantRegionInfo.DoesNotExist, e:
            return Response({"ok": False, "info": "tenant_region not found: {0}".format(e.__str__())}, status=400)
        except Exception, e:
            logger.exception('tenant.move', e)
            return Response({"ok": False, "info": e.__str__()}, status=500)

        if tenant_dest_region.is_active:
            report = self.start_services(tenant, source_region, dest_region)
            if report['ok']:
                return Response(report, status=204)
            else:
                return Response(report, status=500)
        else:
            return Response({"ok": False, "info": "dest_region init is not ready"}, status=500)

    def start_services(self, tenant, source_region, dest_region):
        report = {"ok": True}
        moving_services = TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id, service_region=source_region)

        try:
            ids = map(lambda s: s.service_id, moving_services)
            service_relations = TenantServiceRelation.objects.filter(service_id__in=ids)
            dep_service_ids = set([s.dep_service_id for s in service_relations])
            start_at_end_ids = set(ids).difference(dep_service_ids)

            report.update({"dep_services": dep_service_ids, "starts_services": start_at_end_ids})
            for service_id in dep_service_ids:
                self.start(service_id, dest_region)

            for service_id in start_at_end_ids:
                self.start(service_id, dest_region)
        except Exception, e:
            logger.exception("tenant.move", e)
            report.update({"ok": False, "info": e.__str__()})

        return report

    def start(self, service_id, region):
        logger.info("tenant.move", "region {0}, try to start service {1}".format(region, service_id))
        service = TenantServiceInfo.objects.get(service_id=service_id)
        logger.info("tenant.move", "service category is {0}".format(service.category))
        if service.category == 'applacation':
            service.deploy_version = make_deploy_version()
            service.save()
            body = {
                "action": "upgrade",
                "deploy_version": service.deploy_version,
                "gitUrl": "--branch " + service.code_version + " --depth 1 " + service.clone_url
            }
            logger.info("tenant.move", "build task is {0}".format(body))

            regionClient.build_service(region, service_id, json.dumps(body))
            logger.info("tenant.move", "call regionapi for build_service {0}".format(service_id))
        else:
            service.deploy_version = make_deploy_version()
            service.save()
            body = {"deploy_version": service.deploy_version}
            regionClient.deploy(region, service_id, json.dumps(body))
            logger.info("tenant.move", "call regionapi for restart_service {0}".format(service_id))
        logger.info("tenant.move", "region {0}, started service {1}".format(region, service_id))


class TenantFollowUpView(APIView):

    '''
    后续处理: 复制域名,休眠,删除源区域的服务,更新服务region
    '''

    def post(self, request, tenantId, format=None):
        """
        后续处理
        ---
        serializer: TenantMoveSerializer
        """
        serializer = TenantMoveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        source_region = serializer.data.get('source_region')
        dest_region = serializer.data.get('dest_region')

        logger.info("tenant.move", "do follow-up works on region {0} for tenant {1}".format(dest_region, tenantId))

        try:
            tenant = Tenants.objects.get(tenant_id=tenantId)
            tenant_dest_region = TenantRegionInfo.objects.get(tenant_id=tenantId, region_name=dest_region)
            if not tenant_dest_region.is_active:
                msg = "region {0} for tenant {1} is not active".format(dest_region, tenant.tenant_name)
                logger.info("tenant.move", msg)
                return Response({"ok": False, "info": msg}, status=500)
        except Tenants.DoesNotExist:
            return Response({"ok": False, "info": "tenant match {0} not found".format(tenantId)}, status=400)
        except TenantRegionInfo.DoesNotExist, e:
            return Response({"ok": False, "info": "tenant_region not found: {0}".format(e.__str__())}, status=400)
        except Exception, e:
            logger.exception('tenant.move', e)
            return Response({"ok": False, "info": e.__str__()}, status=500)

        if tenant_dest_region.is_active:
            report = self.do_follow_up_works(tenant, source_region, dest_region)
            if report['ok']:
                return Response(report, status=204)
            else:
                return Response(report, status=500)
        else:
            return Response({"ok": False, "info": "dest_region init is not ready"}, status=500)

    def do_follow_up_works(self, tenant, source_region, tenant_dest_region):
        report = {"ok": True, "moved_services": []}
        moving_services = TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id, service_region=source_region)

        try:
            for service in moving_services:
                regionClient.delete(source_region, service.service_id)
                logger.info("tenant.move", "delete service {0} from source region {1}".format(service.service_id, source_region))

                service.service_region = tenant_dest_region.region_name
                service.save()
                report['moved_services'].append(service.service_id)
                logger.info("tenant.move", "set service {0} region = {1}".format(service.service_id, tenant_dest_region.region_name))

                service_domains = ServiceDomain.objects.filter(service_id=service.service_id)
                for domain in service_domains:
                    task = {
                        "service_id": service.service_id,
                        "new_domain": domain.domain_name,
                        "old_domain": tenant.tenant_name,
                        "pool_name": '{0}@{1}.Pool'.format(tenant.tenant_name, service.service_alias)
                    }
                    regionClient.addUserDomain(tenant_dest_region.region_name, json.dumps(task))

            if tenant_dest_region.service_status != 1:
                regionClient.pause(tenant_dest_region.region_name, tenant.tenant_id)
                logger.info("tenant.move", "pause tenant {0} == {1} on region {2}".format(
                    tenant.tenant_name, tenant.tenant_id, tenant_dest_region.region_name))
            if tenant_dest_region.service_status == 3:
                regionClient.systemPause(tenant_dest_region.region_name, tenant.tenant_id)
                logger.info("tenant.move", "systempause tenant {0} == {1} on region {2}".format(
                    tenant.tenant_name, tenant.tenant_id, tenant_dest_region.region_name))
        except Exception, e:
            logger.exception("tenant.move", e)
            report.update({"ok": False, "info": e.__str__()})

        return report


class TenantMoveUpdateView(APIView):

    """
    迁移后的属性更新
    """
    allowed_methods = ('PUT',)

    def put(self, request, tenantId, format=None):
        '''
        更新属性
        ---
        parameters:
            - name: default_region
              description: 默认区域
              required: true
              type: string
              paramType: form
        '''
        default_region = request.data.get('default_region')

        try:
            tenant = Tenants.objects.get(tenant_id=tenantId)
            tenant.region = default_region
            tenant.save()
            return Response({"ok": True}, status=200)
        except Tenants.DoesNotExist:
            return Response({"ok": False, "info": "tenant match {0} not found".format(tenantId)}, status=400)
