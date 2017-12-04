# -*- coding:utf-8 -*-

import logging
import threading

from django.db.models import Count
from django.http import JsonResponse

from www.apiclient.regionapi import RegionInvokeApi
from www.models import TenantServiceMountRelation, TenantServiceVolume, TenantServiceInfo, Tenants
from www.tenantservice.baseservice import BaseTenantService
from www.views import AuthedView
from www.utils.crypt import make_uuid

logger = logging.getLogger('default')
region_api = RegionInvokeApi()
base_service = BaseTenantService()


class DepVolSyncApiView(AuthedView):
    def _get_vol(self, service_id, path):
        try:
            return TenantServiceVolume.objects.get(service_id=service_id, volume_path=path)
        except TenantServiceVolume.DoesNotExist:
            return None

    def _get_tenant(self, tenant_id):
        try:
            return Tenants.objects.get(tenant_id=tenant_id)
        except Tenants.DoesNotExist:
            return None

    def _get_service(self, service_id):
        try:
            return TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            return None

    def _dep_sync(self):
        mnt_rels = TenantServiceMountRelation.objects.all()
        logger.debug('total mnt relations:{0}'.format(mnt_rels.count()))
        for rel in mnt_rels:
            service = self._get_service(rel.service_id)
            if not service:
                logger.debug('get tenant service failed, service id:{0}'.format(rel.service_id))
                continue

            logger.debug(
                'tenant service exist,regioin:{0},alias:{1}'.format(service.service_region, service.service_alias)
            )

            if service.service_region not in ['ali-sh', 'ali-hz']:
                logger.debug('tenant service region [{0}] not in region sh/hz'.format(service.service_region))
                continue

            logger.debug('get tenant {0}'.format(service.tenant_id))
            tenant = self._get_tenant(service.tenant_id)

            if not tenant:
                logger.debug('tenant not exist,tenant id:{0}'.format(service.tenant_id))
                continue

            logger.debug('get region dep volumes,region:{0},tenant name:{1},svc alias:{2}'.format(
                service.service_region, tenant.tenant_name, service.service_alias
            ))
            try:
                res, body = region_api.get_service_dep_volumes(
                    service.service_region, tenant.tenant_name, service.service_alias,tenant.enterprise_id
                )
                if not res:
                    logger.debug('get region dep volumes failed,tenant id:{0},service id:{1}'.format(
                        service.service_id, tenant.tenant_id
                    ))
                    continue
                for dep in body['list']:
                    dep_service_id = dep['dep_service_id']
                    dep_vol_path = dep['volume_path']

                    logger.debug('get dep volume,svc id:{0},vol name:{1}'.format(dep_service_id, dep['ID']))
                    created_dep_vol = self._get_vol(dep_service_id, dep_vol_path)
                    if not created_dep_vol:
                        logger.debug(
                            'dep volume not exist svc id:{0},mnt name:{1}'.format(dep_service_id, dep_vol_path)
                        )

                        logger.debug('get dep tenant service,service id:{0}'.format(dep_service_id))
                        dep_service = self._get_service(dep_service_id)

                        logger.debug(
                            'create dep service volume,service id:{0},category:{1},vol name:{2},vol path:{3}'
                                .format(dep_service.service_id, dep_service.category, dep['ID'], dep_vol_path)
                        )

                        dep_vol, msg = base_service.add_volume_v2(
                            tenant, dep_service, make_uuid()[:7], dep_vol_path, TenantServiceVolume.SHARE
                        )
                        if not dep_vol:
                            logger.debug('add volume failed,msg:{0},tenant name:{1},path:{2}'.format(
                                msg, tenant.tenant_name, dep_vol_path)
                            )
                            continue

                        logger.debug('get service mnt relation,svc id:{0},dep svc id:{1},mnt name:{2}'.format(
                            service.service_id, dep_service.service_id, dep_vol_path
                        ))
                        service_mnt_rel = TenantServiceMountRelation.objects.get(
                            service_id=service.service_id, dep_service_id=dep_service.service_id, mnt_name=dep_vol_path
                        )
                        service_mnt_rel.mnt_name = dep_vol.volume_name
                        service_mnt_rel.mnt_dir = dep_vol.volume_path
                        service_mnt_rel.save()
                    else:
                        logger.debug('dep volume exist,svc id:{0},mnt name:{1}'.format(dep_service_id, dep['ID']))
                        logger.debug('get service mnt relation,svc id:{0},dep svc id:{1},mnt name:{2}'.format(
                            service.service_id, dep_service_id, dep_vol_path
                        ))
                        service_mnt_rel = TenantServiceMountRelation.objects.get(
                            service_id=service.service_id, dep_service_id=dep_service_id, mnt_name=dep_vol_path
                        )
                        service_mnt_rel.mnt_name = created_dep_vol.volume_name
                        service_mnt_rel.mnt_dir = created_dep_vol.volume_path
                        service_mnt_rel.save()
            except Exception:
                logger.debug('get region service dep vols failed,region:{0},tenant_name:{1},svc alias:{2}'.format(
                    service.service_region, tenant.tenant_name, service.service_alias
                ))
                continue
        logger.debug('finished sync old service mnt vols data')

    def get(self, request):
        self._dep_sync()
        return JsonResponse(data={'msg': 'sync task done'}, status=200)


class VolSyncApiView(AuthedView):
    def _get_vol(self, service_id, volume_path):
        try:
            return TenantServiceVolume.objects.get(service_id=service_id, volume_path=volume_path)
        except TenantServiceVolume.DoesNotExist:
            return None

    def _get_tenant(self, tenant_id):
        try:
            return Tenants.objects.get(tenant_id=tenant_id)
        except Tenants.DoesNotExist:
            return None

    def _sync(self):
        logger.debug('get all service ids of TenantServiceVolume')
        services = TenantServiceVolume.objects.all().distinct().values('service_id') \
            .annotate(cnt=Count('service_id'))
        logger.debug('total service ids:{0}'.format(services.count()))
        try:
            vols = []
            for svc in services:
                service_id = svc['service_id']

                logger.debug('get tenant service,service id:{0}'.format(service_id))
                tenant_service = TenantServiceInfo.objects.get(service_id=service_id)

                if tenant_service.service_region not in ['ali-sh', 'ali-hz']:
                    logger.debug(
                        'tenant is not sh or hz datacenter then continue,{0}'.format(tenant_service.service_region)
                    )
                    continue

                logger.debug('get tenant,tenant id:{0}'.format(tenant_service.tenant_id))
                tenant = self._get_tenant(tenant_service.tenant_id)
                if not tenant:
                    logger.debug('tenant not exist, tenant id:{0}'.format(tenant_service.tenant_id))
                    continue

                logger.debug('get region service volumes,region:{0},tenant name:{1},service alias:{2}'.format(
                    tenant_service.service_region, tenant.tenant_name, tenant_service.service_alias
                ))
                try:
                    res, body = region_api.get_service_volumes(
                        tenant_service.service_region, tenant.tenant_name, tenant_service.service_alias,tenant.enterprise_id
                    )
                    if not res:
                        logger.debug(
                            'get region service volumes failed,region:{0},tenant name:{1},service alias:{2}'.format(
                                tenant_service.service_region, tenant.tenant_name, tenant_service.service_alias
                            ))
                        continue
                    vols.append(body['list'])
                    for vol in body['list']:
                        vol_type = vol['volume_type']
                        vol_path = vol['volume_path']
                        vol_id = vol['ID']
                        vol_name = vol['volume_name']

                        if vol_id == 0:
                            logger.debug('volume ID is 0')
                            continue

                        logger.debug(
                            'get service volume,service id:{0},volume path:{1}'.format(service_id, vol_path))
                        volume = self._get_vol(service_id, vol_path)
                        if not volume:
                            logger.debug(
                                'get service volume failed,service id:{0},volume path:{1}'.format(service_id, vol_path)
                            )
                            continue

                        logger.debug('update service volume, category:{0},name:{1},type:{2}'.format(
                            tenant_service.category, vol_name, vol_type
                        ))
                        volume.volume_name = vol_name
                        volume.volume_type = vol_type
                        volume.save()
                    logger.debug('finished sync tenant {0} service {1} volumes'.format(tenant.tenant_name, service_id))
                except Exception as e:
                    logger.debug(
                        'get region service volumes failed,region:{0},tenant name:{1},service alias:{2},err:{3}'.format(
                            tenant_service.service_region, tenant.tenant_name, tenant_service.service_alias, e.message
                        ))
                    continue
            logger.debug('finished sync old service volumes')
            return vols
        except Exception as e:
            logger.debug('sync failed:{0}'.format(e.message))
            return None

    def get(self, request):
        t = threading.Thread(target=self._sync)
        t.start()
        return JsonResponse(data={'message': 'sync task is running'})


class TenantVolsView(AuthedView):
    def get(self, request):
        try:
            tenant_name = request.GET.get('name')
            service_alias = request.GET.get('alias')
            logger.debug('get tenant vols, name:{0},alias:{1}'.format(tenant_name, service_alias))
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            tenant_service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_alias)
            res, body = region_api.get_service_volumes(tenant_service.service_region, tenant.tenant_name, service_alias,tenant.enterprise_id)
            return JsonResponse(data={'vols': body['list']}, status=200)
        except Exception as e:
            return JsonResponse(data={'msg': e.message}, status=500)


class TenantDepVolsView(AuthedView):
    def get(self, request):
        tenant_name = request.GET.get('name')
        service_alias = request.GET.get('alias')
        logger.debug('get tenant vols, name:{0},alias:{1}'.format(tenant_name, service_alias))
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)
            tenant_service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_alias)
            res, body = region_api.get_service_dep_volumes(tenant_service.service_region, tenant_name, service_alias, tenant.enterprise_id)
            return JsonResponse(data={'dep_vols': body['list']}, status=200)
        except Exception as e:
            return JsonResponse(data={'msg': e.message}, status=500)
