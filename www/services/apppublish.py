# -*- coding: utf8 -*-
import json
import logging

from django.forms.models import model_to_dict

from www.apiclient.marketclient import MarketOpenAPI
from www.models import TenantServicesPort, TenantServiceRelation, TenantServiceInfo, \
    TenantServiceEnvVar, TenantServiceVolume, AppService, AppServicePort, AppServiceEnv, AppServiceShareInfo, \
    ServiceExtendMethod, AppServiceVolume, AppServiceRelation, PublishedGroupServiceRelation, ServiceGroupRelation
from www.monitorservice.monitorhook import MonitorHook
from www.utils import sn
from www.utils.crypt import make_uuid

logger = logging.getLogger('default')
monitorhook = MonitorHook()


class PublishAppService(object):
    """服务发布数据获取接口"""

    def get_service_ports_by_ids(self, service_ids):
        """
        根据多个服务ID查询服务的端口信息
        :param service_ids: 应用ID列表
        :return: {"service_id":TenantServicesPort[object]}
        """
        port_list = TenantServicesPort.objects.filter(service_id__in=service_ids)
        service_port_map = {}
        for port in port_list:
            service_id = port.service_id
            tmp_list = []
            if service_id in service_port_map.keys():
                tmp_list = service_port_map.get(service_id)
            tmp_list.append(port)
            service_port_map[service_id] = tmp_list
        return service_port_map

    def get_service_dependencys_by_ids(self, service_ids):
        """
        根据多个服务ID查询服务的依赖服务信息
        :param service_ids:应用ID列表
        :return: {"service_id":TenantServiceInfo[object]}
        """
        relation_list = TenantServiceRelation.objects.filter(service_id__in=service_ids)
        dep_service_map = {}
        for dep_service in relation_list:
            service_id = dep_service.service_id
            tmp_list = []
            if service_id in dep_service_map.keys():
                tmp_list = dep_service_map.get(service_id)
            dep_service_info = TenantServiceInfo.objects.filter(service_id=dep_service.dep_service_id)[0]
            tmp_list.append(dep_service_info)
            dep_service_map[service_id] = tmp_list
        return dep_service_map

    def get_service_env_by_ids(self, service_ids):
        """
        获取应用env
        :param service_ids: 应用ID列表
        :return: 可修改的环境变量service_env_change_map，不可修改的环境变量service_env_nochange_map
        """
        env_list = TenantServiceEnvVar.objects.filter(service_id__in=service_ids, container_port__lte=0)
        env_change_list = [x for x in env_list if x.is_change]
        env_nochange_list = [x for x in env_list if not x.is_change]
        service_env_change_map = {}
        for env in env_change_list:
            service_id = env.service_id
            tmp_list = []
            if service_id in service_env_change_map.keys():
                tmp_list = service_env_change_map.get(service_id)
            tmp_list.append(env)
            service_env_change_map[service_id] = tmp_list
        service_env_nochange_map = {}
        for env in env_nochange_list:
            service_id = env.service_id
            tmp_list = []
            if service_id in service_env_nochange_map.keys():
                tmp_list = service_env_nochange_map.get(service_id)
            tmp_list.append(env)
            service_env_nochange_map[service_id] = tmp_list
        return service_env_change_map, service_env_nochange_map

    def get_service_volume_by_ids(self, service_ids):
        volume_list = TenantServiceVolume.objects.filter(service_id__in=service_ids)
        service_volume_map = {}
        for volume in volume_list:
            service_id = volume.service_id
            tmp_list = []
            if service_id in service_volume_map.keys():
                tmp_list = service_volume_map.get(service_id)
            tmp_list.append(volume)
            service_volume_map[service_id] = tmp_list
        return service_volume_map

    def get_app_service_by_ids(self, service_ids):
        return AppService.objects.filter(service_id__in=service_ids)

    def get_app_service_by_unique(self, service_key, app_version):
        try:
            return AppService.objects.get(service_key=service_key, app_version=app_version)
        except AppService.DoesNotExist:
            return None

    def is_published(self, service_id, region):
        """
            根据service_id判断服务是否发布过
            :param service_id: 服务 ID
            :return: 是否发布, 发布的服务对象
        """
        result = True
        rt_app = None
        service = TenantServiceInfo.objects.get(service_region=region, service_id=service_id)
        if service.category != "app_publish":
            result = False
        else:
            app_list = AppService.objects.filter(service_key=service.service_key).order_by("-ID")
            if app_list:
                rt_app = app_list[0]
            else:
                result = False

        return result, rt_app

    def add_app_service(self, service, user, app_alias, app_version, app_content, is_init_accout, is_outer, is_private,
                        show_assistant, show_cloud):

        # 获取表单信息
        app_service_list = AppService.objects.filter(service_id=service.service_id).order_by('-ID')[:1]
        app_service = AppService()
        if len(app_service_list) == 1:
            app_service = list(app_service_list)[0]
            app_service.update_version += 1
        else:
            namespace = sn.instance.username
            if service.language == "docker":
                namespace = sn.instance.cloud_assistant
            app_service.tenant_id = service.tenant_id
            app_service.service_id = service.service_id
            app_service.service_key = make_uuid(service.service_alias)
            app_service.creater = user.pk
            app_service.status = ''
            app_service.category = "app_publish"
            app_service.is_service = service.is_service
            app_service.is_web_service = service.is_web_service
            app_service.image = service.image
            app_service.namespace = namespace
            app_service.slug = ''
            app_service.extend_method = service.extend_method
            app_service.cmd = service.cmd
            app_service.env = service.env
            app_service.min_node = service.min_node
            app_service.min_cpu = service.min_cpu
            app_service.min_memory = service.min_memory
            app_service.inner_port = service.inner_port
            app_service.volume_mount_path = service.volume_mount_path
            # todo 这里需要注意分享应用为application类型
            app_service.service_type = 'application'
            app_service.show_category = ''
            app_service.is_base = False
            app_service.publisher = user.email
            app_service.is_ok = 0
            if service.is_slug():
                app_service.slug = '/app_publish/{0}/{1}.tgz'.format(app_service.service_key, app_version)
                # 更新status、show_app、show_assistant
        app_service.app_alias = app_alias
        app_service.app_version = app_version
        app_service.info = app_content
        app_service.is_init_accout = is_init_accout
        app_service.is_outer = is_outer
        if is_private:
            app_service.status = "private"
        app_service.show_app = show_cloud
        app_service.show_assistant = show_assistant
        app_service.save()
        return app_service

    def add_app_port(self, service, service_key, app_version):
        logger.debug("group.publish",
                     u'group.share.service. now add group shared service port for service {0} ok'.format(
                         service.service_id))
        # query all port
        port_list = TenantServicesPort.objects.filter(tenant_id=service.tenant_id,
                                                      service_id=service.service_id)
        container_port_list = [x.container_port for x in port_list]
        # 删除app_service_port中不存在的port
        AppServicePort.objects.filter(service_key=service_key, app_version=app_version).exclude(
            container_port__in=container_port_list).delete()
        port_data = []
        for port in list(port_list):
            try:
                app_port = AppServicePort.objects.get(service_key=service_key, app_version=app_version,
                                                      container_port=port.container_port)
                app_port.protocol = port.protocol
                app_port.port_alias = port.port_alias
                app_port.is_inner_service = port.is_inner_service
                app_port.is_outer_service = port.is_outer_service
                app_port.save()
            except AppServicePort.DoesNotExist as e:
                app_port = AppServicePort(service_key=service_key,
                                          app_version=app_version,
                                          container_port=port.container_port,
                                          protocol=port.protocol,
                                          port_alias=port.port_alias,
                                          is_inner_service=port.is_inner_service,
                                          is_outer_service=port.is_outer_service)
                port_data.append(app_port)
        if len(port_data) > 0:
            AppServicePort.objects.bulk_create(port_data)
        return port_list

    def add_app_env(self, service, service_key, app_version, port_list):

        logger.debug("group.publish",
                     u'group.share.service. now add group shared service env for service {0} ok'.format(
                         service.service_id))
        # 排除端口参数
        exclude_port = [x.container_port for x in port_list]
        env_list = TenantServiceEnvVar.objects.filter(service_id=service.service_id) \
            .exclude(container_port__in=exclude_port) \
            .values('ID', 'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        attr_name_list = [x["attr_name"] for x in env_list]
        # 删除未保留参数
        AppServiceEnv.objects.filter(service_key=service_key, app_version=app_version).exclude(
            attr_name__in=attr_name_list).delete()
        # 获取参数类型
        share_info_list = AppServiceShareInfo.objects.filter(service_id=service.service_id) \
            .values("tenant_env_id", "is_change")
        share_info_map = {x["tenant_env_id"]: x["is_change"] for x in list(share_info_list)}

        env_data = []
        for env in list(env_list):
            is_change = env["is_change"]
            if env["ID"] in share_info_map.keys():
                is_change = share_info_map.get(env["ID"])
            try:
                app_env = AppServiceEnv.objects.get(service_key=service_key,
                                                    app_version=app_version,
                                                    attr_name=env["attr_name"])

                app_env.app_env = env["name"]
                app_env.attr_value = env["attr_value"]
                app_env.scope = env["scope"]
                app_env.is_change = is_change
                app_env.container_port = env["container_port"]
                app_env.save()
            except AppServiceEnv.DoesNotExist:
                app_env = AppServiceEnv(service_key=service_key,
                                        app_version=app_version,
                                        name=env["name"],
                                        attr_name=env["attr_name"],
                                        attr_value=env["attr_value"],
                                        scope=env["scope"],
                                        is_change=is_change,
                                        container_port=env["container_port"])
                env_data.append(app_env)

        if len(env_data) > 0:
            AppServiceEnv.objects.bulk_create(env_data)

    def add_app_extend_info(self, service, service_key, app_version):

        logger.debug("group.publish",
                     u'group.share.service. now add group shared service extend method for service {0} ok'.format(
                         service.service_id))
        count = ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version).count()
        if count == 0:
            extend_method = ServiceExtendMethod(
                service_key=service_key,
                app_version=app_version,
                min_node=service.min_node,
                max_node=20,
                step_node=1,
                min_memory=service.min_memory,
                max_memory=65536,
                step_memory=128,
                is_restart=False)
            extend_method.save()
        else:
            ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version) \
                .update(min_node=service.min_node, min_memory=service.min_memory)

    def add_app_volume(self, service, service_key, app_version):
        logger.debug("group.publish",
                     u'group.share.service. now add group share service volume for service {0} ok'.format(
                         service.service_id))
        # if service.category == "application":
        volume_list = TenantServiceVolume.objects.filter(service_id=service.service_id)
        volume_path_list = [x.volume_path for x in volume_list]
        AppServiceVolume.objects.filter(service_key=service_key,
                                        app_version=app_version) \
            .exclude(volume_path__in=volume_path_list).delete()

        volume_data = []
        for volume in list(volume_list):
            count = AppServiceVolume.objects.filter(service_key=service_key,
                                                    app_version=app_version,
                                                    volume_path=volume.volume_path).count()
            if count == 0:
                app_volume = AppServiceVolume(service_key=service_key,
                                              app_version=app_version,
                                              category=volume.category,
                                              volume_path=volume.volume_path,
                                              volume_name=volume.volume_name,
                                              volume_type=volume.volume_type)
                volume_data.append(app_volume)
        if len(volume_data) > 0:
            AppServiceVolume.objects.bulk_create(volume_data)

    def add_app_relation(self, service, service_key, app_version, app_alias):
        logger.debug("group.publish",
                     "service_id {0} service_key {1} app_service {2} app_alias {3}".format(service.service_id,
                                                                                           service_key, app_version,
                                                                                           app_alias))
        relation_list = TenantServiceRelation.objects.filter(service_id=service.service_id)
        dep_service_ids = [x.dep_service_id for x in list(relation_list)]
        if len(dep_service_ids) == 0:
            return None
        # 依赖服务的信息
        logger.debug("group.publish", "depended service are {}".format(dep_service_ids))

        try:
            dep_service_list = TenantServiceInfo.objects.filter(service_id__in=dep_service_ids)
            app_relation_list = []
            if len(dep_service_list) > 0:
                for dep_service in dep_service_list:
                    dep_app_service = None
                    # 不为源码构建的应用
                    if dep_service.service_key != "application" and (dep_service.language is None):
                        dep_app_list = AppService.objects.filter(service_key=dep_service.service_key,
                                                                 app_version=dep_service.version).order_by("-ID")
                        if not dep_app_list:
                            dep_app_list = AppService.objects.filter(service_key=dep_service.service_key).order_by(
                                "-ID")
                            if dep_app_list:
                                dep_app_service = dep_app_list[0]
                            else:
                                dep_app_list = AppService.objects.filter(service_id=dep_service.service_id).order_by(
                                    "-ID")
                        else:
                            dep_app_service = dep_app_list[0]
                    else:
                        dep_app_list = AppService.objects.filter(service_id=dep_service.service_id).order_by("-ID")
                        dep_app_service = dep_app_list[0]

                    if not dep_app_service:
                        return 404

                    # 检查是否存在对应的app_relation
                    relation_count = AppServiceRelation.objects.filter(service_key=service_key,
                                                                       app_version=app_version,
                                                                       dep_service_key=dep_app_service.service_key,
                                                                       dep_app_version=dep_app_service.app_version).count()
                    if relation_count == 0:
                        app_relation = AppServiceRelation(service_key=service_key,
                                                          app_version=app_version,
                                                          app_alias=app_alias,
                                                          dep_service_key=dep_app_service.service_key,
                                                          dep_app_version=dep_app_service.app_version,
                                                          dep_app_alias=dep_app_service.app_alias)
                        app_relation_list.append(app_relation)
                # 批量添加发布依赖
                if len(app_relation_list) > 0:
                    AppServiceRelation.objects.bulk_create(app_relation_list)
            else:
                # 依赖服务的实力已经被删除,理论上不存在这种情况
                return 400
        except Exception as e:
            logger.exception("group.publish", e)
            logger.error("group.publish",
                         "add app relation error service_key {0},app_version {1},app_alias {2}".format(service_key,
                                                                                                       app_version,
                                                                                                       app_alias))

    def get_app_service_port(self, service_key, app_version):
        return AppServicePort.objects.filter(service_key=service_key,
                                             app_version=app_version)

    def get_app_service_env(self, service_key, app_version):
        return AppServiceEnv.objects.filter(service_key=service_key,
                                            app_version=app_version)

    def get_app_service_volume(self, service_key, app_version):
        return AppServiceVolume.objects.filter(service_key=service_key,
                                               app_version=app_version)

    def get_app_service_pre_dep(self, service_key, app_version):
        return []
        # 这个实现有问题, 先不处理
        # return AppServiceRelation.objects.filter(dep_service_key=service_key,
        #                                          dep_app_version=app_version)

    def get_app_service_suf_dep(self, service_key, app_version):
        return AppServiceRelation.objects.filter(service_key=service_key,
                                                 app_version=app_version)

    def get_app_service_extend_method(self, service_key, app_version):
        return ServiceExtendMethod.objects.filter(service_key=service_key,
                                                  app_version=app_version)

    def update_or_create_group_service_relation(self, app_service_map, app_service_group):
        for s_id, app in app_service_map.items():
            pgsr_list = PublishedGroupServiceRelation.objects.filter(group_pk=app_service_group.ID,
                                                                     service_id=s_id)
            if not pgsr_list:
                PublishedGroupServiceRelation.objects.create(group_pk=app_service_group.ID, service_id=s_id,
                                                             service_key=app.service_key,
                                                             version=app.app_version)
            else:
                PublishedGroupServiceRelation.objects.filter(group_pk=app_service_group.ID,
                                                             service_id=s_id).update(
                    service_key=app.service_key,
                    version=app.app_version)

    def delete_group_service_relation_by_group_pk(self, group_pk):
        PublishedGroupServiceRelation.objects.filter(group_pk=group_pk).delete()

    def list_published_group_app_services(self, pk):
        pgsrs = PublishedGroupServiceRelation.objects.filter(group_pk=pk)
        apps = []
        for item in pgsrs:
            app = AppService.objects.get(service_key=item.service_key, app_version=item.version)
            apps.append(app)
        return apps

    def upate_app_service_by_key_and_version(self, service_key, app_version, data):
        app = AppService.objects.get(service_key=service_key, app_version=app_version)
        if not app.dest_yb:
            app.dest_yb = data["DestYB"]
        if not app.dest_ys:
            app.dest_ys = data["DestYS"]
        isok = False
        # 如果发布到云市而且云市云帮都成功
        if app.is_outer and app.dest_yb and app.dest_ys:
            isok = True
        # 如果只发到云帮
        if not app.is_outer and app.dest_yb:
            isok = True

        slug = data["Slug"]
        if slug != "" and not slug.startswith("/"):
            slug = "/" + slug
        app.is_ok = isok  # 发布成功
        if slug != "":
            app.slug = slug
        image = data["Image"]
        if image != "":
            app.image = image
        app.save()

    def send_group_service_data_to_market(self, app_service_group, tenant, region, groupId, param_data={}, url_map={}):
        # 发送数据到云市
        service_list = self.__get_tenant_group_service_by_group_id(tenant, region, groupId)

        service_category_map = {x.service_id: "self" if (
                x.category == "application" or (x.category == "app_publish" and x.language is not None)) else "other"
                                for x
                                in service_list}

        pgsrs = PublishedGroupServiceRelation.objects.filter(group_pk=app_service_group.ID)
        apps = []
        service_extra_data = []
        for item in pgsrs:
            app_service = self.get_app_service_by_unique(item.service_key, item.version)
            owner = service_category_map.get(app_service.service_id, "other")
            service_map = {"service_key": app_service.service_key,
                           "version": app_service.app_version,
                           "owner": owner}
            service_extra_data.append(service_map)
            preview_url = url_map.get(item.service_key, "")
            app_service_env = self.get_app_service_env(item.service_key, item.version)
            app_service_port = self.get_app_service_port(item.service_key, item.version)
            app_service_volume = self.get_app_service_volume(item.service_key, item.version)
            app_service_extend_method = self.get_app_service_extend_method(item.service_key, item.version)
            app_service_pre_dep = self.get_app_service_pre_dep(item.service_key, item.version)
            app_service_suf_dep = self.get_app_service_suf_dep(item.service_key, item.version)

            app_data = {
                'pre_list': map(lambda x: model_to_dict(x), app_service_pre_dep),
                'suf_list': map(lambda x: model_to_dict(x), app_service_suf_dep),
                'env_list': map(lambda x: model_to_dict(x), app_service_env),
                'port_list': map(lambda x: model_to_dict(x), app_service_port),
                'extend_list': map(lambda x: model_to_dict(x), app_service_extend_method),
                'volume_list': map(lambda x: model_to_dict(x), app_service_volume),
                'service': app_service.to_dict(),
                "preview_url": preview_url
            }
            apps.append(app_data)

        group_dict = app_service_group.to_dict()
        group_dict["tenant_id"] = tenant.tenant_id
        group_dict["data"] = service_extra_data
        group_dict["group_apps"] = apps

        group_dict.update(param_data)
        self.__send_all_group_data(tenant, group_dict)
        app_service_group.is_publish_to_market = True
        app_service_group.source = 'remote'
        app_service_group.save()

    def __send_all_group_data(self, tenant, data):
        logger.debug("GROUP DATA START".center(90, "-"))
        logger.debug(json.dumps(data))
        logger.debug("GROUP DATA START".center(90, "-"))
        appClient = MarketOpenAPI()
        appClient.publish_all_service_group_data(tenant.tenant_id, data)

    def __get_tenant_group_service_by_group_id(self, tenant, region, group_id):
        """
        获取租户指定的组下的所有服务
        """
        svc_relations = ServiceGroupRelation.objects.filter(tenant_id=tenant.tenant_id, group_id=group_id,
                                                            region_name=region)
        if not svc_relations:
            return list()

        svc_ids = [svc_rel.service_id for svc_rel in svc_relations]
        return TenantServiceInfo.objects.filter(service_id__in=svc_ids)
