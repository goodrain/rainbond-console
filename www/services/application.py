# -*- coding: utf8 -*-
from console.repositories.app import service_source_repo
from console.repositories.group import group_repo, tenant_service_group_repo
from console.services.market_app_service import template_transform_service
from www.models import *
from www.monitorservice.monitorhook import MonitorHook
from www.region import RegionInfo
from www.utils.status_translate import get_status_info_map
from www.apiclient.marketclient import MarketOpenAPI
import logging
import json
from django.conf import settings
import datetime
from django.forms.models import model_to_dict
from console.services.app import app_service
from console.repositories.app_config import extend_repo
from console.services.group_service import group_service
from console.services.app_config import env_var_service, port_service, volume_service, label_service, probe_service
from www.apiclient.regionapi import RegionInvokeApi
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid
from console.services.region_services import region_services
from console.models.main import RainbondCenterApp
from console.services.app_config.app_relation_service import AppServiceRelationService
from console.services.app_actions import app_manage_service

logger = logging.getLogger('default')
baseService = BaseTenantService()
monitorhook = MonitorHook()
region_api = RegionInvokeApi()
market_api = MarketOpenAPI()
app_relation_service = AppServiceRelationService()

app_log_template = """
        service: {0}
        extend : {1}
        envs   : {2}
        port   : {3}
        volume : {4}
        deps   : {5}
"""


class ApplicationService(object):
    """
    应用服务接口，提供应用生命周期的所有操作
    """

    def get_service_by_id(self, service_id):
        try:
            return TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            return None

    def get_service_status(self, tenant, service):
        try:
            body = region_api.check_service_status(service.service_region, tenant.tenant_name,
                                                   service.service_alias,
                                                   tenant.enterprise_id)
            status = body["bean"]['cur_status']

        except Exception, e:
            logger.debug(service.service_region + "-" + service.service_id + " check_service_status is error")
            logger.exception(e)
            status = 'failure'

        return get_status_info_map(status)

    def delete_service(self, tenant, service):
        try:
            logger.debug("service_id - {0} - service_name {1} ".format(service.service_id, service.service_cname))
            try:
                region_api.delete_service(service.service_region, tenant.tenant_name, service.service_alias,
                                          tenant.enterprise_id)
            except Exception as e:
                success = False
                logger.error("region delete service error! ")
                logger.exception(e)
                return success

            TenantServiceInfo.objects.get(service_id=service.service_id).delete()
            # env/auth/domain/relationship/envVar/volume delete
            TenantServiceEnv.objects.filter(service_id=service.service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service.service_id).delete()
            ServiceDomain.objects.filter(service_id=service.service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service.service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service.service_id).delete()
            TenantServiceMountRelation.objects.filter(service_id=service.service_id).delete()
            TenantServicesPort.objects.filter(service_id=service.service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service.service_id).delete()
            ServiceGroupRelation.objects.filter(service_id=service.service_id,
                                                tenant_id=self.tenant_id).delete()
            ServiceAttachInfo.objects.filter(service_id=service.service_id).delete()
            ServiceCreateStep.objects.filter(service_id=service.service_id).delete()
            events = ServiceEvent.objects.filter(service_id=service.service_id)
            deleteEventID = []
            if events:
                for event in events:
                    deleteEventID.append(event.event_id)
            if len(deleteEventID) > 0:
                region_api.deleteEventLog(service.service_region,
                                          json.dumps({"event_ids": deleteEventID}))

            ServiceEvent.objects.filter(service_id=service.service_id).delete()

            monitorhook.serviceMonitor(self.nick_name, service, 'app_delete', True)
        except Exception as e:
            logger.error("back service delete error!")
            logger.exception(e)
            return False


class ApplicationGroupService(object):
    def get_app_service_group_by_unique(self, group_key, group_version):
        try:
            return AppServiceGroup.objects.get(group_share_id=group_key, group_version=group_version)
        except AppServiceGroup.DoesNotExist:
            return None

    def is_app_service_group_existed(self, group_key, group_version):
        query = AppServiceGroup.objects.filter(group_share_id=group_key, group_version=group_version)
        if not query.exists():
            return False

        app_service_group = query.first()

        rels = PublishedGroupServiceRelation.objects.filter(group_pk=app_service_group.ID)
        for rel in rels:
            if not ServiceInfo.objects.filter(service_key=rel.service_key, version=rel.version).exists():
                return False

        return True

    def list_app_service_group(self, source='remote'):
        return AppServiceGroup.objects.filter(source=source)

    def download_app_service_group_from_market(self, tenant_id, group_key, group_version):
        if self.is_app_service_group_existed(group_key, group_version):
            logger.debug('local group template existed, ignore.')
            return self.get_app_service_group_by_unique(group_key=group_key, group_version=group_version)

        # 如果本地模板不存在, 从云市下载一份
        try:
            data = market_api.get_service_group_detail(tenant_id, group_key, group_version)
            if not data:
                return None

            # 先根据云市模板配置关系清理本地应用组关系
            # self.__delete_app_service_group(data['group_key'],
            #                                 data['group_version'],
            #                                 [(app['service_key'], app['version']) for app in data['apps']])
            # 根据云市模板生成新的本地应用组
            app_service_group = self.__create_app_service_group(data, 'remote')
            return app_service_group
        except Exception as e:
            logger.exception(e)
            logger.error('download app_group[{0}-{1}] from market failed!'.format(group_key, group_version))
            return None

    def get_app_templates(self, tenant_id, group_key, group_version,template_version):
        app = self.get_local_app_templates(group_key, group_version)
        if app and app.is_complete:
            logger.debug('local group template existed, ignore.')
            logger.debug("======> {0}".format(app.app_template))
            # 字符串
            return app.app_template
        try:
            app_templates = market_api.get_service_group_detail(tenant_id, group_key, group_version,template_version)
            if not app_templates:
                return None
            if app_templates["template_version"] == "v1":
                v2_template = template_transform_service.v1_to_v2(app_templates)
                data = json.dumps(v2_template)
            else:
                v2_template = app_templates
                data = v2_template["template_content"]
            logger.debug("======>  {0}".format(data))
            return data
        except Exception as e:
            logger.exception(e)
            logger.error('download app_group[{0}-{1}] from market failed!'.format(group_key, group_version))
            return None

    def get_local_app_templates(self,group_key, group_version):
        apps = RainbondCenterApp.objects.filter(group_key=group_key,version=group_version)
        if apps:
            return apps[0]
        return None

    def import_app_service_group_from_file(self, tenant_id, file_path):
        pass

    def delete_app_service_group(self, group_key, group_version):
        """
        依赖应用组的关系删除本地应用模板
        :param group_key: 
        :param group_version: 
        :return: 
        """
        groups = AppServiceGroup.objects.filter(group_share_id=group_key, group_version=group_version)
        for group in groups:
            relations = PublishedGroupServiceRelation.objects.filter(group_pk=group.ID)
            service_relations = [(r.service_key, r.version) for r in relations]
            self.__delete_app_service_group(group.group_share_id, group.group_version, service_relations)

    def __delete_app_service_group(self, group_key, group_version, service_relations):
        for service_key, version in service_relations:
            # AppService.objects.filter(service_key=service_key, app_version=version).delete()
            ServiceInfo.objects.filter(service_key=service_key, version=version).delete()
            AppServiceEnv.objects.filter(service_key=service_key, app_version=version).delete()
            AppServicePort.objects.filter(service_key=service_key, app_version=version).delete()
            ServiceExtendMethod.objects.filter(service_key=service_key, app_version=version).delete()
            AppServiceRelation.objects.filter(service_key=service_key, app_version=version).delete()
            AppServiceVolume.objects.filter(service_key=service_key, app_version=version).delete()

        groups = AppServiceGroup.objects.filter(group_share_id=group_key, group_version=group_version)
        for group in groups:
            relations = PublishedGroupServiceRelation.objects.filter(group_pk=group.ID)
            relations.delete()
            group.delete()

    def __create_app_service_group(self, data, source):
        app_log_list = list()
        for app in data.get('apps', []):
            try:
                base_info = ServiceInfo.objects.get(service_key=app.get("service_key"), version=app.get("version"))
            except ServiceInfo.DoesNotExist:
                base_info = ServiceInfo()
            base_info.service_key = app.get("service_key")
            base_info.version = app.get("version")
            base_info.service_name = app.get("service_name")
            base_info.publisher = app.get("publisher")
            base_info.status = app.get("status")
            # 下载模版后在本地应用市场安装
            if base_info.service_key != "application":
                base_info.status = "published"
            base_info.category = app.get("category") or "app_publish"
            base_info.is_service = app.get("is_service")
            base_info.is_web_service = app.get("is_web_service")
            base_info.update_version = app.get("update_version")
            base_info.image = app.get("image")
            base_info.slug = app.get("slug")
            base_info.extend_method = app.get("extend_method")
            base_info.cmd = app.get("cmd")
            base_info.setting = app.get("setting")
            base_info.env = app.get("env")
            base_info.dependecy = app.get("dependecy")
            base_info.min_node = app.get("min_node")
            base_info.min_cpu = app.get("min_cpu")
            base_info.min_memory = app.get("min_memory")
            base_info.inner_port = app.get("inner_port")
            base_info.volume_mount_path = app.get("volume_mount_path")
            base_info.service_type = app.get("service_type")
            base_info.is_init_accout = app.get("is_init_accout")
            base_info.namespace = app.get("namespace")
            base_info.save()

            # 保存环境变量
            AppServiceEnv.objects.filter(service_key=app.get("service_key"), app_version=app.get("version")).delete()
            env_data = [AppServiceEnv(service_key=env.get("service_key"),
                                      app_version=env.get("app_version"),
                                      name=env.get("name"),
                                      attr_name=env.get("attr_name"),
                                      attr_value=env.get("attr_value"),
                                      scope=env.get("scope"),
                                      is_change=env.get("is_change"),
                                      container_port=env.get("container_port"))
                        for env in app.get('envs', [])]
            if len(env_data) > 0:
                AppServiceEnv.objects.bulk_create(env_data)

            # 端口信息
            AppServicePort.objects.filter(service_key=app.get("service_key"), app_version=app.get("version")).delete()
            port_data = [AppServicePort(service_key=port.get("service_key"),
                                        app_version=port.get("app_version"),
                                        container_port=port.get("container_port"),
                                        protocol=port.get("protocol"),
                                        port_alias=port.get("port_alias"),
                                        is_inner_service=port.get("is_inner_service"),
                                        is_outer_service=port.get("is_outer_service"))
                         for port in app.get('ports', [])]
            if len(port_data) > 0:
                AppServicePort.objects.bulk_create(port_data)

            # 扩展信息
            ServiceExtendMethod.objects.filter(service_key=app.get("service_key"),
                                               app_version=app.get("version")).delete()
            extend_data = [
                ServiceExtendMethod(service_key=extend.get("service_key"),
                                    app_version=extend.get("app_version"),
                                    min_node=extend.get("min_node"),
                                    max_node=extend.get("max_node"),
                                    step_node=extend.get("step_node"),
                                    min_memory=extend.get("min_memory"),
                                    max_memory=extend.get("max_memory"),
                                    step_memory=extend.get("step_memory"),
                                    is_restart=extend.get("is_restart"))
                for extend in app.get('extends', [])]
            if len(extend_data) > 0:
                ServiceExtendMethod.objects.bulk_create(extend_data)

            # 服务依赖关系
            AppServiceRelation.objects.filter(service_key=app.get("service_key"),
                                              app_version=app.get("version")).delete()
            relation_data = [
                AppServiceRelation(service_key=relation.get("service_key"),
                                   app_version=relation.get("app_version"),
                                   app_alias=relation.get("app_alias"),
                                   dep_service_key=relation.get("dep_service_key"),
                                   dep_app_version=relation.get("dep_app_version"),
                                   dep_app_alias=relation.get("dep_app_alias"))
                for relation in app.get('dep_relations', [])
            ]
            if len(relation_data) > 0:
                AppServiceRelation.objects.bulk_create(relation_data)

            # 服务持久化记录
            AppServiceVolume.objects.filter(service_key=app.get("service_key"), app_version=app.get("version")).delete()
            volume_data = [
                AppServiceVolume(service_key=app_volume.get("service_key"),
                                 app_version=app_volume.get("app_version"),
                                 category=app_volume.get("category"),
                                 volume_path=app_volume.get("volume_path"))
                for app_volume in app.get('volumes', [])]
            if len(volume_data) > 0:
                AppServiceVolume.objects.bulk_create(volume_data)

            app_log_list.append(app_log_template.format(base_info.to_dict(),
                                                        [extend.to_dict() for extend in extend_data],
                                                        [env.to_dict() for env in env_data],
                                                        [port.to_dict() for port in port_data],
                                                        [volume.to_dict() for volume in volume_data],
                                                        [rel.to_dict() for rel in relation_data]))

        try:
            group_info = AppServiceGroup.objects.get(group_share_id=data.get('group_key'),
                                                     group_version=data.get('group_version'))
            if group_info.source != 'remote' and group_info.is_market and group_info.is_publish_to_market:
                group_info.source = 'remote'
                group_info.save()
                logger.debug('====>update')
        except AppServiceGroup.DoesNotExist:
            group_info = AppServiceGroup()
            group_info.tenant_id = ''
            group_info.group_share_alias = data.get('group_name')
            group_info.group_share_id = data.get('group_key')
            group_info.group_version = data.get('group_version')
            group_info.group_id = 0
            group_info.service_ids = ""
            group_info.is_market = True
            group_info.source = source
            group_info.enterprise_id = 0
            group_info.publish_type = 'services_group'
            group_info.share_scope = 'market'
            group_info.is_publish_to_market = 1
            group_info.desc = data.get('desc', '')
            group_info.is_success = 1
            group_info.save()
            logger.debug('====>create')

        logger.debug(group_info.to_dict())
        # 创建应用组与应用关系
        for app in data.get("apps", []):
            rels = PublishedGroupServiceRelation.objects.filter(group_pk=group_info.ID,
                                                                service_key=app.get("service_key"),
                                                                version=app.get("version"))
            if not rels.exists():
                rel = PublishedGroupServiceRelation.objects.create(group_pk=group_info.ID,
                                                                   service_id="",
                                                                   service_key=app.get("service_key"),
                                                                   version=app.get("version")
                                                                   )
                logger.debug('====>create rel')
                logger.debug(rel.to_dict())
            logger.debug('====>ignore rel')

        for app_log in app_log_list:
            logger.debug(app_log)
        return group_info

    def __create_tenant_service_group(self, tenant, app_service_group, region_name):
        group_name = self.__generator_group_name('gr')
        tenant_service_group = TenantServiceGroup(tenant_id=tenant.tenant_id,
                                                  group_name=group_name,
                                                  group_alias=app_service_group.group_share_alias,
                                                  group_key=app_service_group.group_share_id,
                                                  group_version=app_service_group.group_version,
                                                  region_name=region_name)
        tenant_service_group.save()
        return tenant_service_group

    def install_tenant_service_group(self, user, tenant, region_name, app_service_group, service_origin):
        logger.debug('install [{}] ==> [{},{}]'.format(app_service_group.group_share_alias,
                                                       app_service_group.group_share_id,
                                                       app_service_group.group_version))
        # 先创建一个本地的租户应用组
        tenant_group = self.__create_tenant_service_group(tenant, app_service_group, region_name)
        logger.debug('create tenant_service_group: {}'.format(tenant_group.ID))

        # 根据模板创建本地运行应用信息, 这个操作应该是事物性的, 如果没有成功, 整体清理
        installed_services = list()
        try:
            # 查询分享组中的服务模板信息
            service_info_list = self.__get_service_info(app_service_group.ID)
            # 依据服务模板创建租户服务
            self.__create_tenant_services(user, tenant, region_name, tenant_group, service_info_list,
                                          installed_services, service_origin)

            # 创建服务依赖
            self.__create_dep_service(installed_services)
        except Exception as copy_exc:
            logger.exception(copy_exc)
            self.__clear_install_context(tenant_group, installed_services, tenant)
            return False, 'create tenant_services failed!', tenant_group, installed_services

        # 根据分享组模板生成此应用组对应的分类, 并将这些安装的应用放置到此分类下
        category_group = self.__create_category_group(tenant.tenant_id, region_name,
                                                      app_service_group.group_share_alias,
                                                      installed_services)
        tenant_group.service_group_id = category_group.pk
        tenant_group.save()

        return True, 'success', tenant_group, installed_services

    def install_market_apps_directly(self, user, tenant, region_name, app_service_json_str, service_origin ):
        app_templates = json.loads(app_service_json_str)
        apps = app_templates["apps"]

        service_list = []
        service_key_dep_key_map = {}
        key_service_map = {}
        tenant_service_group = None
        new_group = None
        try:
            # 生成分类
            group_name = self.__generator_group_name(app_templates["group_name"])
            new_group = group_repo.add_group(tenant.tenant_id, region_name, group_name)
            group_id = new_group.ID
            tenant_service_group = self.__generate_tenant_service_group(region_name, tenant.tenant_id, new_group.ID,
                                                                        app_templates["group_key"],
                                                                        app_templates["group_version"],
                                                                        app_templates["group_name"])
            for app in apps:
                ts = self.__init_market_app(tenant, region_name, user, app, tenant_service_group.ID,service_origin)
                group_service.add_service_to_group(tenant, region_name, group_id, ts.service_id)

                # 先保存env,再保存端口，因为端口需要处理env
                code, msg = self.__save_env(tenant, ts, app["service_env_map_list"],
                                            app["service_connect_info_map_list"])
                if code != 200:
                    raise Exception(msg)
                code, msg = self.__save_port(tenant, ts, app["port_map_list"])
                if code != 200:
                    raise Exception(msg)
                code, msg = self.__save_volume(tenant, ts, app["service_volume_map_list"])
                if code != 200:
                    raise Exception(msg)

                # 保存应用探针信息
                probe_infos = app.get("probes", None)
                if probe_infos:
                    for prob_data in probe_infos:
                        code, msg, probe = probe_service.add_service_probe(tenant, ts, prob_data)
                        if code != 200:
                            logger.exception(msg)

                self.__save_extend_info(ts, app["extend_method_map"])

                dep_apps_key = app.get("dep_service_map_list", None)
                if dep_apps_key:
                    service_key_dep_key_map[ts.service_key] = dep_apps_key
                key_service_map[ts.service_key] = ts
                service_list.append(ts)
            # 保存依赖关系，需要等应用都创建完成才能使用
            self.__save_service_deps(tenant, service_key_dep_key_map, key_service_map)
            # 数据中心创建应用
            for service in service_list:
                new_service = app_service.create_region_service(tenant, service, user.nick_name)
                logger.debug("build service ===> {0}  success".format(service.service_cname))
                # 为服务添加探针
                self.__create_service_probe(tenant, new_service)

                # 添加服务有无状态标签
                label_service.update_service_state_label(tenant, new_service)

            return True, "success", tenant_service_group, service_list
        except Exception as e:
            logger.exception(e)
            # 回滚数据
            if tenant_service_group:
                tenant_service_group_repo.delete_tenant_service_group_by_pk(tenant_service_group.ID)
            if new_group:
                group_repo.delete_group_by_pk(new_group.ID)
            for service in service_list:
                try:
                    app_manage_service.truncate_service(tenant, service)
                except Exception as delete_error:
                    logger.exception(delete_error)
            return False, "create tenant_services from market directly failed !", None, service_list

    def __update_service_extend_method(self, tenant, tenant_service):
        try:
            logger.debug('extend_method: {}'.format(tenant_service.extend_method))

            service_status = 'state' if tenant_service.extend_method == 'state' else 'stateless'
            logger.debug('region_extend_method: {}'.format(service_status))
            data = {
                'label_values': '无状态的应用' if service_status == 'stateless' else '有状态的应用',
                'enterprise_id': tenant.enterprise_id
            }
            region_api.update_service_state_label(tenant_service.service_region, tenant.tenant_name,
                                                  tenant_service.service_alias, data)
        except Exception as e:
            logger.exception(e)

    def __create_service_probe(self, tenant, service):
        try:
            if ServiceProbe.objects.filter(service_id=service.service_id, mode='readiness').exists():
                return

            tenant_ports = TenantServicesPort.objects.filter(tenant_id=tenant.tenant_id, service_id=service.service_id,
                                                             is_outer_service=1).exclude(protocol='udp')
            if not tenant_ports:
                return

            port = tenant_ports.first().container_port
            is_used = 1
            # 特殊处理小强数据库
            if service.service_key == "66ee1676270f74b76e2a431671e8f320":
                is_used = 0
            service_probe = ServiceProbe(service_id=service.service_id,
                                         scheme='tcp', path='', http_header='', cmd='',
                                         port=port,
                                         initial_delay_second=2,
                                         period_second=3, timeout_second=30, failure_threshold=3, success_threshold=1,
                                         is_used=is_used,
                                         probe_id=make_uuid(),
                                         mode='readiness')

            json_data = model_to_dict(service_probe)
            is_used = 1 if json_data["is_used"] else 0
            json_data.update({"is_used": is_used})
            json_data["enterprise_id"] = tenant.enterprise_id
            res, body = region_api.add_service_probe(service.service_region, tenant.tenant_name,
                                                     service.service_alias, json_data)

            if 400 <= res.status <= 600:
                logger.error('set service [{}] probe to region failed!')
            else:
                service_probe.save()
                logger.debug(service_probe)
        except Exception as e:
            logger.exception(e)

    def __create_tenant_services(self, user, tenant, region_name, tenant_group, sorted_service,
                                 installed_services, service_origin):
        for service_info in sorted_service:
            service_id = make_uuid(service_info.service_key)
            service_alias = "gr" + service_id[-6:]

            new_tenant_service = baseService.create_service(service_id, tenant.tenant_id, service_alias,
                                                            service_info.service_name, service_info, user.user_id,
                                                            region=region_name, tenant_service_group_id=tenant_group.ID,
                                                            service_origin=service_origin)
            # new_tenant_service.expired_time = tenant.expired_time
            new_tenant_service.save()
            logger.debug(
                'create tenant_service: [{}:{}] ==> {}'.format(service_info.service_name, service_alias, service_id))
            monitorhook.serviceMonitor(tenant.tenant_name, new_tenant_service, 'create_service', True)

            # 环境变量
            logger.debug("===> create service env!")
            self.__copy_envs(service_info, new_tenant_service, tenant)
            # 端口信息
            logger.debug("===> create service port!")
            self.__copy_ports(service_info, new_tenant_service)
            # 持久化目录
            logger.debug("===> create service volumn!")
            self.__copy_volumes(service_info, new_tenant_service)

            installed_services.append(new_tenant_service)

    def __clear_install_context(self, tenant_group, installed_services, tenant):
        tenant_id = tenant.tenant_id
        installed_service_ids = [s.service_id for s in installed_services]
        logger.debug("===> del count: {}".format(len(installed_service_ids)))
        logger.debug("===> del service_ids: {}".format(installed_service_ids))

        TenantServiceAuth.objects.filter(service_id__in=installed_service_ids).delete()
        ServiceDomain.objects.filter(service_id__in=installed_service_ids).delete()
        TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id__in=installed_service_ids).delete()
        TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id__in=installed_service_ids).delete()
        TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id__in=installed_service_ids).delete()
        TenantServiceVolume.objects.filter(service_id__in=installed_service_ids).delete()
        ServiceProbe.objects.filter(service_id__in=installed_service_ids).delete()
        ServiceGroupRelation.objects.filter(service_id__in=installed_service_ids).delete()
        TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_id__in=installed_service_ids).delete()

        sgr = ServiceGroupRelation.objects.filter(group_id=tenant_group.service_group_id)
        if sgr.count() == 0:
            ServiceGroup.objects.filter(pk=tenant_group.service_group_id).delete()

        if tenant_group:
            tenant_group.delete()
        logger.debug("===> clear installed_services done!")

    def __generator_group_name(self, group_name):
        return '_'.join([group_name, make_uuid()[-4:]])

    def __is_group_name_exist(self, group_name, tenant_id, region_name):
        return ServiceGroup.objects.filter(tenant_id=tenant_id, region_name=region_name,
                                           group_name=group_name).exists()

    def __create_category_group(self, tenant_id, region_name, group_name, installed_services=[]):
        """
        在指定团队数据中心生成应用分类，如果分类名存在则自动生成分类名, 并将安装的应用放置于此分类之下
        :return: 分类
        """
        while True:
            if self.__is_group_name_exist(group_name, tenant_id, region_name):
                group_name = self.__generator_group_name(group_name)
            else:
                group = ServiceGroup.objects.create(tenant_id=tenant_id, region_name=region_name,
                                                    group_name=group_name)
                break

        for service_info in installed_services:
            ServiceGroupRelation.objects.create(service_id=service_info.service_id, group_id=group.pk,
                                                tenant_id=tenant_id,
                                                region_name=region_name)
        return group

    def __get_service_info(self, group_id):
        result = []
        pgsr_list = PublishedGroupServiceRelation.objects.filter(group_pk=group_id)
        for pgsr in pgsr_list:
            service = ServiceInfo.objects.filter(service_key=pgsr.service_key, version=pgsr.version).order_by(
                '-ID').first()
            if service:
                result.append(service)
        return result

    def __topological_sort(self, graph):
        is_visit = dict((node, False) for node in graph)
        li = []

        def dfs(graph, start_node):
            for end_node in graph[start_node]:
                if not is_visit[end_node]:
                    is_visit[end_node] = True
                    dfs(graph, end_node)
            li.append(start_node)

        for start_node in graph:
            if not is_visit[start_node]:
                is_visit[start_node] = True
                dfs(graph, start_node)
        return li

    def __sort_service(self, publish_service_list, reverse=False):
        # publish_service_list 包含此次部署的所有应用
        service_map = {s.service_key: s for s in publish_service_list}

        # 根据此次部署中所有应用之间的关系记录, 构建应用部署顺序树
        key_app_map = {}
        for app in publish_service_list:
            dep_services = AppServiceRelation.objects.filter(service_key=app.service_key, app_version=app.version)
            if dep_services:
                key_app_map[app.service_key] = [ds.dep_service_key for ds in dep_services]
            else:
                key_app_map[app.service_key] = []

        # service_keys 中包含此次已排序部署应用顺序
        service_keys = self.__topological_sort(key_app_map)

        # 从未排序的publish_service_list根据key的排序结果重新组织部署应用列表
        result = []
        for key in service_keys:
            service = service_map.get(key)
            result.append(service)

        if reverse:
            result.reverse()

        return result

    def __create_dep_service(self, installed_services):
        logger.debug("===> create service dependency!")
        service_map = {service.service_key: service for service in installed_services}
        for tenant_service in installed_services:
            # 根据当前安装应用依赖的模板key获得其依赖信息
            dep_service_rel_list = AppServiceRelation.objects.filter(service_key=tenant_service.service_key,
                                                                     app_version=tenant_service.version)

            if not dep_service_rel_list:
                logger.debug("rel: [{}] ===> []".format(tenant_service.service_cname))
                continue

            # 根据依赖关系查找当前安装服务依赖的服务
            dep_services = list()
            for dep_svc_rel in dep_service_rel_list:
                dep_service = service_map.get(dep_svc_rel.dep_service_key)

                has_rel = False
                if dep_service:
                    has_rel = True
                    dep_services.append(dep_service)
                logger.debug('rel: [{}] ==> [{}] {}'.format(dep_svc_rel.app_alias, dep_svc_rel.dep_app_alias, has_rel))

            dep_order = 0
            for dep_service in dep_services:
                tsr = TenantServiceRelation()
                tsr.tenant_id = tenant_service.tenant_id
                tsr.service_id = tenant_service.service_id
                tsr.dep_service_id = dep_service.service_id
                tsr.dep_order = dep_order
                tsr.dep_service_type = dep_service.service_type
                tsr.save()
                dep_order += 1

                logger.debug(
                    "create rel: {0} ==> {1}: {2} ".format(tsr.service_id, tsr.dep_service_id, dep_order))

    def __copy_ports(self, source_service, current_service):
        AppPorts = AppServicePort.objects.filter(service_key=current_service.service_key,
                                                 app_version=current_service.version)
        for port in AppPorts:
            baseService.addServicePort(current_service, source_service.is_init_accout,
                                       container_port=port.container_port, protocol=port.protocol,
                                       port_alias=port.port_alias,
                                       is_inner_service=port.is_inner_service, is_outer_service=port.is_outer_service)

    def __copy_envs(self, service_info, tenant_service, tenant):
        envs = AppServiceEnv.objects.filter(service_key=service_info.service_key, app_version=service_info.version)
        outer_ports = AppServicePort.objects.filter(service_key=service_info.service_key,
                                                    app_version=service_info.version,
                                                    is_outer_service=True,
                                                    protocol='http')
        for env in envs:
            # 对需要特殊处理的应用增加额外的环境变量
            if env.attr_name in ('SITE_URL', 'TRUSTED_DOMAIN'):
                port = RegionInfo.region_port(tenant_service.service_region)
                domain = RegionInfo.region_domain(tenant_service.service_region)
                env.options = "direct_copy"
                if len(outer_ports) > 0:
                    if env.attr_name == 'SITE_URL':
                        env.attr_value = 'http://{}.{}.{}{}:{}'.format(outer_ports[0].container_port,
                                                                       tenant_service.service_alias, tenant.tenant_name,
                                                                       domain, port)
                    else:
                        env.attr_value = '{}.{}.{}{}:{}'.format(outer_ports[0].container_port,
                                                                tenant_service.service_alias, tenant.tenant_name,
                                                                domain, port)
                logger.debug("env: {} = {} options = {}".format(env.attr_name, env.attr_value, env.options))

            baseService.saveServiceEnvVar(tenant_service.tenant_id, tenant_service.service_id, env.container_port,
                                          env.name,
                                          env.attr_name, env.attr_value, env.is_change, env.scope)

        # # 处理模板隐含环境变量
        # inner_envs = service_info.env.split(',') if service_info.env else []
        # logger.debug("service.env: {}".format(inner_envs))
        # for env in inner_envs:
        #     if not env:
        #         continue
        #     env_name, env_value = env.split('=')
        #     baseService.saveServiceEnvVar(tenant_service.tenant_id, tenant_service.service_id, -1,
        #                                   env_name, env_name, env_value, False, 'inner')

        # 处理模板SLUG包地址
        if service_info.slug:
            baseService.saveServiceEnvVar(tenant_service.tenant_id, tenant_service.service_id, -1,
                                          'SLUG_PATH', 'SLUG_PATH', service_info.slug, False, 'inner')

    def __copy_volumes(self, source_service, tenant_service):
        volumes = AppServiceVolume.objects.filter(service_key=source_service.service_key,
                                                  app_version=source_service.version)
        for volume in volumes:
            baseService.add_volume_with_type(tenant_service, volume.volume_path, volume.volume_type,
                                             volume.volume_name)

        if tenant_service.volume_mount_path:
            if not volumes.filter(volume_path=tenant_service.volume_mount_path).exists():
                baseService.add_volume_with_type(tenant_service, tenant_service.volume_mount_path,
                                                 TenantServiceVolume.SHARE, make_uuid()[:7])

    def get_app_group_by_id(self, group_id):
        """
        获取发布的服务组最新的版本
        """
        app_service_groups = AppServiceGroup.objects.filter(group_id=group_id).order_by("-ID")
        if app_service_groups:
            return app_service_groups[0]
        else:
            return None

    def update_app_group_service(self, app_group_service, **params):
        for k, v in params.items():
            setattr(app_group_service, k, v)
        app_group_service.save(update_fields=params.keys())
        app_group_service.update_time = datetime.datetime.now()
        app_group_service.save()
        return app_group_service

    def create_app_group_service(self, **params):
        app_service_group = AppServiceGroup(**params)
        app_service_group.save()
        return app_service_group

    def get_app_group_by_pk(self, pk):
        """
        通过主键获取应用组模板信息
        :param pk: 
        :return: 
        """
        try:
            return AppServiceGroup.objects.get(pk=pk)
        except AppServiceGroup.DoesNotExist:
            return None

    def get_tenant_service_group_by_pk(self, pk, is_cascade=False, is_query_status=False, is_query_consume=False):
        """
        通过主键获取租户已安装应用组信息
        :param pk: 
        :param is_cascade: 是否级联查询租户与关联应用
        :param is_query_status: 是否查询应用组运行状态
        :param is_query_consume: 是否查询应用组运行资源
        :return: 
        """
        try:
            group = TenantServiceGroup.objects.get(pk=pk)
        except TenantServiceGroup.DoesNotExist:
            return None

        if is_cascade:
            group.tenant = Tenants.objects.get(tenant_id=group.tenant_id)
            group.service_list = TenantServiceInfo.objects.filter(tenant_service_group_id=group.pk) or list()
            for service in group.service_list:
                service.access_url = self.get_tenant_service_access_url(group.tenant, service)

        if is_query_consume:
            group.memory, group.net, group.disk = self.get_tenant_group_consume(group)

        if is_query_status:
            group.status = self.__get_tenant_group_status(group)

        return group

    def list_tenant_service_group_by_region(self, tenant, region_name, is_cascade=False, is_query_status=False,
                                            is_query_consume=False):
        """
        查询指定租户数据中心下的应用组信息
        :param tenant: 租户
        :param region_name: 数据中心名称
        :param is_cascade: 是否级联查询租户与关联应用
        :param is_query_status: 是否查询应用组运行状态
        :param is_query_consume: 是否查询应用组运行资源
        :return: 
        """
        if not tenant:
            return []

        group_list = TenantServiceGroup.objects.filter(tenant_id=tenant.tenant_id, region_name=region_name)
        if not group_list:
            return []

        for group in group_list:
            if is_cascade:
                group.tenant = tenant
                group.service_list = TenantServiceInfo.objects.filter(tenant_service_group_id=group.pk) or list()
                for service in group.service_list:
                    service.access_url = self.get_tenant_service_access_url(group.tenant, service)

            if is_query_consume:
                group.memory, group.net, group.disk = self.get_tenant_group_consume(group)

            if is_query_status:
                group.status = self.__get_tenant_group_status(group)

        return group_list

    def get_tenant_group_consume(self, group):
        """
        通过应用组获取应用组的资源消耗
        :param group: 应用组对象 
        :return: 
        """
        total_memory = 0
        total_net = 0
        total_disk = 0

        tenant = group.tenant if hasattr(group, 'tenant') else Tenants.objects.get(tenant_id=group.tenant_id)
        service_list = group.service_list if hasattr(group, 'service_list') else \
            TenantServiceInfo.objects.filter(tenant_service_group_id=group.pk)

        for service in service_list:
            tss = TenantServiceStatics.objects.filter(service_id=service.service_id,
                                                      tenant_id=tenant.tenant_id).order_by("-ID")[:1]
            if tss:
                ts = tss[0]
                memory, disk, net = ts.node_memory, ts.storage_disk, ts.flow
            else:
                memory, disk, net = service.min_memory, 0, 0

            total_memory += memory
            total_net += net
            total_disk += disk

        return total_memory, total_disk, total_net

    def __get_tenant_group_status(self, group):
        """
        通过应用组获取应用组的资源消耗
        :param group: 应用组对象 
        :return: 
        """
        tenant = group.tenant or Tenants.objects.get(tenant_id=group.tenant_id)
        service_list = group.service_list or TenantServiceInfo.objects.filter(tenant_service_group_id=group.pk)

        service_ids = [s.service_id for s in service_list]
        service_status_map = self.__map_region_service_status(tenant.enterprise_id, group.region_name, tenant.tenant_name, service_ids)

        for service in service_list:
            if service.service_id in service_status_map:
                service.status = service_status_map[service.service_id]
            else:
                service.status = 'undeploy'

        list_status = [service.status for service in service_list]
        return self.__compute_group_service_status(list_status)

    def __get_tenant_service_status(self, tenant, service):
        try:
            body = region_api.check_service_status(service.service_region, tenant.tenant_name,
                                                   service.service_alias,
                                                   tenant.enterprise_id)
            status = body["bean"]['cur_status']

        except region_api.CallApiError as e:
            if e.status == 404:
                status = 'undeploy'
            else:
                logger.debug(service.service_region + "-" + service.service_id + " check_service_status is error")
                logger.exception(e)
                status = 'failure'

        return get_status_info_map(status)['status']

    def __compute_group_service_status(self, services_status):
        if not services_status:
            return 'unknow'

        running_count = 0
        closed_count = 0
        starting_count = 0
        undeploy_count = 0
        upgrade_count = 0
        abnormal_count = 0
        stopping_count = 0
        for status in services_status:
            runtime_status = status
            if runtime_status == 'closed':
                closed_count += 1
            elif runtime_status == 'running':
                running_count += 1
            elif runtime_status == 'starting':
                starting_count += 1
            elif runtime_status == 'undeploy':
                undeploy_count += 1
            elif runtime_status == 'upgrade':
                upgrade_count += 1
            elif runtime_status == 'abnormal':
                abnormal_count += 1
            elif runtime_status == 'stopping':
                stopping_count += 1

        service_count = len(services_status)
        if service_count == 0:
            group_status = 'closed'
        elif undeploy_count > 0:
            group_status = 'undeploy'
        elif starting_count > 0:
            group_status = 'starting'
        elif upgrade_count > 0:
            group_status = 'upgrade'
        elif abnormal_count > 0:
            group_status = 'abnormal'
        elif running_count > 0 and running_count == service_count:
            group_status = 'running'
        elif closed_count > 0 and closed_count == service_count:
            group_status = 'closed'
        elif stopping_count > 0:
            group_status = 'stopping'
        else:
            group_status = 'unknow'

        return group_status

    def get_service_http_port(self, service_id):
        return TenantServicesPort.objects.filter(
            service_id=service_id, protocol='http', is_outer_service=True
        )

    def get_tenant_by_pk(self, tenant_id):
        try:
            return Tenants.objects.get(tenant_id=tenant_id)
        except Tenants.DoesNotExist:
            return None

    def get_user_by_eid(self, e_id):
        try:
            return Users.objects.get(enterprise_id=e_id)
        except Users.DoesNotExist:
            return None

    def get_tenant_service_access_url(self, tenant, service):
        tenant_ports = TenantServicesPort.objects.filter(tenant_id=tenant.tenant_id, service_id=service.service_id,
                                                         is_outer_service=1, protocol='http')
        if not tenant_ports:
            return ''

        # 如果有多个对外端口，取第一个
        tenant_port = tenant_ports[0]
        wild_domain = region_services.get_region_httpdomain(service.service_region)

        access_url = "http://{0}.{1}.{2}.{3}".format(tenant_port.container_port, service.service_alias,
                                                     tenant.tenant_name,
                                                     wild_domain)

        return access_url

    def is_tenant_service_group_installed(self, tenant, region_name, group_key, group_version):
        """
        在指定租户的指定数据中心下, 指定类型应用组是否已安装过
        :param tenant: 租户信息
        :param region_name: 数据中心名称
        :param group_key: 应用组模板key
        :param group_version: 应用组模板version
        :return: 
        """
        return TenantServiceGroup.objects.filter(tenant_id=tenant.tenant_id, region_name=region_name,
                                                 group_key=group_key,
                                                 group_version=group_version).exists()

    def build_tenant_service_group(self, user, group_id):
        group = self.get_tenant_service_group_by_pk(group_id, True, True)
        logger.debug('prepare deploy service_group ==> [{}-{}:{}]'.format(group.group_alias, group_id, group.status))
        if not group:
            return False, '应用组不存在'

        tenant = group.tenant

        if group.status not in ['undeploy', 'closed']:
            return False, '应用正在{}无需构建'.format(group.status)

        # 运行到这里, 云帮的应用已经都准备就绪了, 根据应用的关系, 向数据中心发部署请求
        sorted_services = self.__sort_service(group.service_list)
        logger.debug(
            'build order ==> {}'.format([tenant_service.service_cname for tenant_service in sorted_services]))

        try:
            for s in sorted_services:
                app_manage_service.deploy(tenant, s, user)
        except Exception as deploy_error:
            logger.exception(deploy_error)

        return True, '构建应用成功'

    def restart_tenant_service_group(self, user, group_id):
        group = self.get_tenant_service_group_by_pk(group_id, True)
        if not group:
            return False, '应用组不存在'

        tenant = group.tenant

        # 将应用组中应用排序, 并逐一启动
        sorted_services = self.__sort_service(group.service_list)
        logger.debug(
            'restart order ==> {}'.format([tenant_service.service_cname for tenant_service in sorted_services]))
        for service in sorted_services:
            try:
                app_manage_service.start(tenant, service, user)
            except Exception as e:
                logger.exception(e)
                logger.error(
                    'restart {0}[{1}]:{2} failed!'.format(service.service_cname, service.service_alias,
                                                          service.service_id))
                return False, '启动应用组失败'
        return True, '启动应用组成功'

    def stop_tenant_service_group(self, user, group_id):
        group = self.get_tenant_service_group_by_pk(group_id, True)
        if not group:
            return False, '应用组不存在'

        tenant = group.tenant

        # 将应用组中应用排序, 并逐一启动
        sorted_services = self.__sort_service(group.service_list)
        logger.debug(
            'stop order ==> {}'.format([tenant_service.service_cname for tenant_service in sorted_services]))
        for service in sorted_services:
            try:
                app_manage_service.stop(tenant, service, user)
            except Exception as e:
                logger.exception(e)
                return False, '停止应用组失败'

        return True, '停止应用组成功'

    def delete_tenant_service_group(self, group_id):
        group = self.get_tenant_service_group_by_pk(group_id, True)
        if not group:
            return True, '删除成功'

        region_name = group.region_name
        tenant = group.tenant
        logger.debug('==> prepare del group: {}'.format(group.to_dict()))

        # 将应用组中的应用反向排序, 然后再逐一删除
        region_delete = True
        sorted_services = self.__sort_service(group.service_list, True)
        logger.debug(
            'delete order ==> {}'.format([tenant_service.service_cname for tenant_service in sorted_services]))
        for tenant_service in sorted_services:
            try:
                region_api.delete_service(region_name, tenant.tenant_name, tenant_service.service_alias,
                                          tenant.enterprise_id)
            except region_api.CallApiError as delete_exc:
                if delete_exc.status == 404:
                    continue

                logger.exception(delete_exc)
                logger.error('delete {0}[{1}]:{2} failed!'.format(tenant_service.service_cname,
                                                                  tenant_service.service_alias,
                                                                  tenant_service.service_id))
                region_delete = False

        if not region_delete:
            return False, '删除数据中心应用失败, 请重试!'

        self.__clear_install_context(group, sorted_services, tenant)
        return True, '删除应用组成功'

    def list_group_service_by_ids(self, group_id_list):
        """
        获取任意应用组id列表的应用组信息
        :param group_id_list: 
        :return: 
        """
        group_list = list()
        for group_id in group_id_list:
            tenant_group = self.get_tenant_service_group_by_pk(int(group_id), True)
            if tenant_group:
                group_list.append(tenant_group)

        query_map = dict()
        service_map = dict()
        for tenant_group in group_list:
            # 按租户+数据中心给应用分组
            query_key = ':'.join(
                [tenant_group.tenant.enterprise_id, tenant_group.region_name, tenant_group.tenant.tenant_name])
            if query_key not in query_map:
                query_map[query_key] = list()

            query_map[query_key].extend(tenant_group.service_list)
            service_map.update({s.service_id: s for s in tenant_group.service_list})

        # 同一数据中心,租户下的应用一次性查询出来
        for key, service_list in query_map.items():
            enterprise_id, region, tenant_name = key.split(':')
            service_ids = [s.service_id for s in service_list]
            service_status_map = self.__map_region_service_status(enterprise_id, region, tenant_name, service_ids)

            for service in service_list:
                if service.service_id in service_status_map:
                    service.status = service_status_map[service.service_id]
                else:
                    service.status = 'undeploy'

        # 将所有组下应用的状态汇总成为应用组状态
        for tenant_group in group_list:
            list_service_status = [service.status for service in tenant_group.service_list]
            tenant_group.status = self.__compute_group_service_status(list_service_status)

        return group_list

    def __map_region_service_status(self, enterprise_id, region, tenant_name, service_ids):
        try:
            data = {
                "service_ids": service_ids,
                "enterprise_id": enterprise_id
            }
            ret_data = region_api.service_status(region, tenant_name, data)
            services_status = ret_data.get("list") or list()
            return {status_map["service_id"]: status_map['status'] for status_map in services_status}
        except Exception as e:
            logger.exception(e)
            return {service_id: 'failure' for service_id in service_ids}

    def __generate_tenant_service_group(self, region, tenant_id, group_id, group_key, group_version, group_alias):
        group_name = self.__generator_group_name("gr")
        params = {
            "tenant_id": tenant_id,
            "group_name": group_name,
            "group_alias": group_alias,
            "group_key": group_key,
            "group_version": group_version,
            "region_name": region,
            "service_group_id": 0 if group_id == -1 else group_id
        }
        return tenant_service_group_repo.create_tenant_service_group(**params)

    def __init_market_app(self, tenant, region, user, app, tenant_service_group_id, service_origin):
        """
        初始化应用市场创建的应用默认数据
        """
        is_slug = bool(
            app["image"].startswith('goodrain.me/runner') and app["language"] not in ("dockerfile", "docker"))

        tenant_service = TenantServiceInfo()
        tenant_service.tenant_id = tenant.tenant_id
        tenant_service.service_id = make_uuid()
        tenant_service.service_cname = app_service.generate_service_cname(tenant, app["service_cname"], region)
        tenant_service.service_alias = "gr" + tenant_service.service_id[-6:]
        tenant_service.creater = user.pk
        if is_slug:
            tenant_service.image = app["image"]
        else:
            tenant_service.image = app.get("share_image", app["image"])
        tenant_service.cmd = app.get("cmd", "")
        tenant_service.service_region = region
        tenant_service.service_key = app["service_key"]
        tenant_service.desc = "market app "
        tenant_service.category = "app_publish"
        tenant_service.setting = ""
        tenant_service.extend_method = app["extend_method"]
        tenant_service.env = ","
        tenant_service.min_node = app["extend_method_map"]["min_node"]
        tenant_service.min_memory = app["extend_method_map"]["min_memory"]
        tenant_service.min_cpu = baseService.calculate_service_cpu(region, tenant_service.min_memory)
        tenant_service.inner_port = 0
        tenant_service.version = app["version"]
        if is_slug:
            if app.get("service_slug", None):
                tenant_service.namespace = app["service_slug"]["namespace"]
        else:
            if app.get("service_image", None):
                tenant_service.namespace = app["service_image"]["namespace"]
        tenant_service.update_version = 1
        tenant_service.port_type = "multi_outer"
        tenant_service.create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenant_service.deploy_version = ""
        tenant_service.git_project_id = 0
        tenant_service.service_type = "application"
        tenant_service.total_memory = tenant_service.min_node * tenant_service.min_memory
        tenant_service.volume_mount_path = ""
        tenant_service.host_path = ""
        tenant_service.code_from = ""
        tenant_service.language = ""
        tenant_service.service_source = "market"
        tenant_service.create_status = "creating"
        tenant_service.service_origin = service_origin
        tenant_service.tenant_service_group_id = tenant_service_group_id
        self.__init_service_source(tenant_service, app)
        # 存储并返回
        tenant_service.save()
        return tenant_service

    def __init_service_source(self, ts, app):
        is_slug = bool(ts.image.startswith('goodrain.me/runner') and app["language"] not in ("dockerfile", "docker"))
        if is_slug:
            extend_info = app["service_slug"]
            extend_info["slug_path"] = app.get("share_slug_path", "")
        else:
            extend_info = app["service_image"]

        service_source_params = {
            "team_id": ts.tenant_id,
            "service_id": ts.service_id,
            "user_name": "",
            "password": "",
            "extend_info": json.dumps(extend_info)
        }
        service_source_repo.create_service_source(**service_source_params)

    def __save_service_deps(self, tenant, service_key_dep_key_map, key_service_map):
        if service_key_dep_key_map:
            for service_key in service_key_dep_key_map.keys():
                ts = key_service_map[service_key]
                dep_keys = service_key_dep_key_map[service_key]
                for dep_key in dep_keys:
                    dep_service = key_service_map[dep_key["dep_service_key"]]
                    code, msg, d = app_relation_service.add_service_dependency(tenant, ts,
                                                                               dep_service.service_id)
                    if code != 200:
                        logger.error("compose add service error {0}".format(msg))
                        return code, msg
        return 200, "success"

    def __save_env(self, tenant, service, inner_envs, outer_envs):
        if not inner_envs and not outer_envs:
            return 200, "success"
        for env in inner_envs:
            code, msg, env_data = env_var_service.add_service_env_var(tenant, service, 0, env["name"], env["attr_name"],
                                                                      env["attr_value"], env["is_change"],
                                                                      "inner")
            if code != 200:
                logger.error("save market app env error {0}".format(msg))
                return code, msg
        for env in outer_envs:
            container_port = env.get("container_port", 0)
            if container_port == 0:
                if env["attr_value"] == "**None**":
                    env["attr_value"] = service.service_id[:8]
                code, msg, env_data = env_var_service.add_service_env_var(tenant, service, container_port,
                                                                          env["name"], env["attr_name"],
                                                                          env["attr_value"], env["is_change"],
                                                                          "outer")
                if code != 200:
                    logger.error("save market app env error {0}".format(msg))
                    return code, msg
        return 200, "success"

    def __save_port(self, tenant, service, ports):
        if not ports:
            return 200, "success"
        for port in ports:
            code, msg, port_data = port_service.add_service_port(tenant, service,
                                                                 int(port["container_port"]),
                                                                 port["protocol"],
                                                                 port["port_alias"],
                                                                 port["is_inner_service"],
                                                                 port["is_outer_service"])
            if code != 200:
                logger.error("save market app port error".format(msg))
                return code, msg
        return 200, "success"

    def __save_volume(self, tenant, service, volumes):
        if not volumes:
            return 200, "success"
        for volume in volumes:
            code, msg, volume_data = volume_service.add_service_volume(tenant, service, volume["volume_path"],
                                                                       volume["volume_type"], volume["volume_name"])
            if code != 200:
                logger.error("save market app volume error".format(msg))
                return code, msg
        return 200, "success"

    def __save_extend_info(self, service, extend_info):
        if not extend_info:
            return 200, "success"
        params = {
            "service_key": service.service_key,
            "app_version": service.version,
            "min_node": extend_info["min_node"],
            "max_node": extend_info["max_node"],
            "step_node": extend_info["step_node"],
            "min_memory": extend_info["min_memory"],
            "max_memory": extend_info["max_memory"],
            "step_memory": extend_info["step_memory"],
            "is_restart": extend_info["is_restart"]
        }
        extend_repo.create_extend_method(**params)
