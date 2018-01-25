# -*- coding: utf8 -*-
import datetime
from decimal import Decimal

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

import www.utils.sn as sn
from goodrain_web.custom_config import custom_config
from goodrain_web.tools import JuncheePaginator
from share.manager.region_provier import RegionProviderManager
from www.db import svc_grop_repo
from www.decorator import perm_required
from www.models import *
from www.region import RegionInfo
from www.tenantservice.baseservice import BaseTenantService, CodeRepositoriesService, TenantAccountService, \
    ServicePluginResource
from www.views import AuthedView, LeftSideBarMixin, Http404
from www.views.ajax import RechargeTypeMap, RegionInvokeApi
from www.services import plugin_svc

rpmManager = RegionProviderManager()
codeRepositoriesService = CodeRepositoriesService()
baseService = BaseTenantService()
tenantAccountService = TenantAccountService()
servicePluginResource = ServicePluginResource()

import logging

logger = logging.getLogger("default")

region_api = RegionInvokeApi()


class ServiceDetailView(AuthedView):
    def __init__(self, *args, **kwargs):
        super(ServiceDetailView, self).__init__(*args, **kwargs)
        self.response_region = self.service.service_region
        fr = self.request.GET.get('fr', None)
        if fr and fr == 'statistic':
            self.statistic = True
            self.statistic_type = self.request.GET.get('type', 'history')
        else:
            self.statistic = False

    def get_user_perms(self):
        perm_users = []
        perm_template = {
            'name': None,
            'adminCheck': False,
            'developerCheck': False,
            'developerDisable': False,
            'viewerCheck': False,
            'viewerDisable': False,
        }
        identities = PermRelService.objects.filter(service_id=self.service.pk)
        user_id_list = [x.user_id for x in identities]
        user_list = Users.objects.filter(pk__in=user_id_list)
        user_map = {x.user_id: x for x in user_list}

        for i in identities:
            user_perm = perm_template.copy()
            user_info = user_map.get(i.user_id)
            if user_info is None:
                continue
            user_perm['name'] = user_info.nick_name
            if i.user_id == self.user.user_id:
                user_perm['selfuser'] = True
            user_perm['email'] = user_info.email
            if i.identity == 'admin':
                user_perm.update({
                    'adminCheck': True,
                    'developerCheck': True,
                    'developerDisable': True,
                    'viewerCheck': True,
                    'viewerDisable': True,
                })
            elif i.identity == 'developer':
                user_perm.update({
                    'developerCheck': True,
                    'viewerCheck': True,
                    'viewerDisable': True,
                })
            elif i.identity == 'viewer':
                user_perm.update({'viewerCheck': True, 'viewerDisable': True})

            perm_users.append(user_perm)

        return perm_users

    def get_manage_app(self, http_port_str):
        logger.debug("get_manage_app ")
        service_manager = {"deployed": False}
        if self.service.service_key == 'mysql' or self.service.service_type == "mysql":
            has_managers = TenantServiceInfo.objects.filter(
                tenant_id=self.tenant.tenant_id, service_region=self.service.service_region, service_key='phpmyadmin'
            )
            if has_managers:
                service_manager['deployed'] = True
                manager = has_managers[0]
                if self.service.port_type == "one_outer":
                    service_manager['url'] = 'http://{0}.{1}{2}:{3}'.format(
                        manager.service_alias, self.tenant.tenant_name,
                        settings.WILD_DOMAINS[self.service.service_region],
                        http_port_str
                    )
                else:
                    service_manager['url'] = 'http://80.{0}.{1}{2}:{3}'.format(
                        manager.service_alias, self.tenant.tenant_name,
                        settings.WILD_DOMAINS[self.service.service_region],
                        http_port_str
                    )
            else:
                # 根据服务版本获取对应phpmyadmin版本,暂时解决方法,待优化
                app_version = '4.4.12'
                key = "phpmyadmin"
                if self.service.version == "5.6.30":
                    app_version = '4.6.3'
                    key = "f3a5fcc551a7990315bd70f139412d25"
                service_manager['url'] = '/apps/{0}/service-deploy/?service_key={1}&app_version={2}'.format(
                    self.tenant.tenant_name, key, app_version
                )
        return service_manager

    def memory_choices(self):
        memory_dict = {
            "128": '128M', "256": '256M', "512": '512M', "1024": '1G', "2048": '2G', "4096": '4G',
            "8192": '8G', "16384": '16G', "32768": '32G', "65536": '64G'
        }
        return memory_dict

    def extends_choices(self):
        extends_dict = {"state": u'有状态', "stateless": u'无状态', "state-expend": u'有状态可水平扩容'}
        return extends_dict

    # 端口开放下拉列表选项
    def multi_port_choices(self):
        multi_port = {"one_outer": u'单一端口开放', "multi_outer": u'多端口开放'}
        # multi_port["dif_protocol"] = u'按协议开放'
        return multi_port

    # 服务挂载卷类型下拉列表选项
    def mnt_share_choices(self):
        mnt_share_type = {"shared": u'共享'}
        # mnt_share_type["exclusive"] = u'独享'
        return mnt_share_type

    # 获取所有的开放的http对外端口
    def get_outer_service_port(self):
        return TenantServicesPort.objects.filter(
            service_id=self.service.service_id, is_outer_service=True, protocol='http'
        )

    def get_service_attach_info(self):
        try:
            return ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id, service_id=self.service.service_id)
        except ServiceAttachInfo.DoesNotExist:
            return self.generate_service_attach_info()

    def generate_service_attach_info(self):
        """为先前的服务创建服务附加信息"""
        service_attach_info = ServiceAttachInfo()
        service_attach_info.tenant_id = self.tenant.tenant_id
        service_attach_info.service_id = self.service.service_id
        service_attach_info.memory_pay_method = "postpaid"
        service_attach_info.disk_pay_method = "postpaid"
        service_attach_info.min_memory = self.service.min_memory
        service_attach_info.min_node = self.service.min_node
        service_attach_info.disk = 0
        service_attach_info.pre_paid_period = 0
        service_attach_info.pre_paid_money = 0
        now = datetime.now().strftime("%Y-%m-%d %H:00:00")
        service_attach_info.buy_start_time = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        service_attach_info.buy_end_time = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        service_attach_info.create_time = datetime.now()
        service_attach_info.region = self.response_region
        service_attach_info.save()
        return service_attach_info

    def get_ws_url(self, default_url, ws_type):
        if default_url != "auto":
            return "{0}/{1}".format(default_url, ws_type)
        host = self.request.META.get('HTTP_HOST').split(':')[0]
        return "ws://{0}:6060/{1}".format(host, ws_type)

    def get_deployed_details(self, context, http_port):
        if self.service.service_type == 'mysql':
            service_manager = self.get_manage_app(http_port)
            context['service_manager'] = service_manager

        inner_ports = {}
        tsps = TenantServicesPort.objects.filter(service_id=self.service.service_id, is_inner_service=True)
        for tsp in tsps:
            inner_ports[tsp.container_port] = True
        if len(tsps) > 0:
            context["hasInnerServices"] = True

        env_map = {}
        env_var_list = TenantServiceEnvVar.objects.filter(
            service_id=self.service.service_id, scope__in=("outer", "both"), is_change=False
        )
        if len(env_var_list) > 0:
            for env_var in env_var_list:
                arr = env_map.get(env_var.service_id)
                if arr is None:
                    arr = []
                arr.append(model_to_dict(env_var))
                env_map[env_var.service_id] = arr
        context["envMap"] = env_map

        container_port_list = []
        opend_service_port_list = TenantServicesPort.objects.filter(
            service_id=self.service.service_id, is_inner_service=True
        )
        if len(opend_service_port_list) > 0:
            for opend_service_port in opend_service_port_list:
                container_port_list.append(opend_service_port.container_port)
        context["containerPortList"] = container_port_list

        if self.service.code_from != "image_manual":
            baseservice = ServiceInfo.objects.get(
                service_key=self.service.service_key, version=self.service.version
            )
            if baseservice.update_version != self.service.update_version:
                context["updateService"] = True

        context["docker_console"] = settings.MODULES["Docker_Console"]
        context["publish_service"] = settings.MODULES["Publish_Service"]

        context["visit_port_type"] = self.service.port_type
        if self.service.port_type == "multi_outer":
            context["http_outer_service_ports"] = [model_to_dict(p) for p in self.get_outer_service_port()]

        context["is_sys_admin"] = self.user.is_sys_admin
        context["port_domain_map"] = self.get_port_domain_map()

    def get_port_domain_map(self):
        serviceDomainlist = ServiceDomain.objects.filter(service_id=self.service.service_id)
        port_domain_map = {}
        for domain in serviceDomainlist:
            tmp_domain_list = self.get_domain_name_with_protocol(domain)
            if port_domain_map.get(domain.container_port) is None:
                port_domain_map[domain.container_port] = tmp_domain_list
            else:
                port_domain_map[domain.container_port][0:0] = tmp_domain_list

        return port_domain_map

    def get_port_details(self, context):
        context["port_changeable"] = self.service.code_from
        service_domain = False
        if TenantServicesPort.objects.filter(
                service_id=self.service.service_id, is_outer_service=True, protocol='http').exists():
            context["hasHttpServices"] = True
            service_domain = True
        if service_domain:
            serviceDomainlist = ServiceDomain.objects.filter(service_id=self.service.service_id)
            data = {}
            for domain in serviceDomainlist:
                tmp_domain_list = self.get_domain_name_with_protocol(domain)
                if data.get(domain.container_port) is None:
                    data[domain.container_port] = tmp_domain_list
                else:
                    data[domain.container_port][0:0] = tmp_domain_list
            context["serviceDomainDict"] = data
        port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id)
        context["ports"] = [model_to_dict(p) for p in port_list]

    def get_domain_name_with_protocol(self, domain):
        rt_domains = []
        if domain.protocol == "https" or domain.protocol == "httptohttps":
            rt_domains.append("https://" + domain.domain_name)
        elif domain.protocol == "httpandhttps":
            rt_domains.append("http://" + domain.domain_name)
            rt_domains.append("https://" + domain.domain_name)
        else:
            rt_domains.append("http://" + domain.domain_name)
        return rt_domains

    def get_dependeny_details(self, context):
        tsrs = TenantServiceRelation.objects.filter(service_id=self.service.service_id)
        relation_ids = [sr.dep_service_id for sr in tsrs]
        context["serviceIds"] = relation_ids

        map = {}
        sids = []
        tenantServiceList = baseService.get_service_list(
            self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region
        )
        for tenantService in tenantServiceList:
            if TenantServicesPort.objects.filter(
                    service_id=tenantService.service_id, is_inner_service=True
            ).exists():
                sids.append(tenantService.service_id)
                if tenantService.service_id != self.service.service_id:
                    map[tenantService.service_id] = model_to_dict(tenantService)
            if tenantService.service_id in relation_ids:
                map[tenantService.service_id] = model_to_dict(tenantService)
        context["serviceMap"] = map

        envMap = {}
        envVarlist = TenantServiceEnvVar.objects.filter(service_id__in=sids, scope__in=("outer", "both"))
        for envVarObj in envVarlist:
            if envVarObj.service_id in envMap:
                envMap[envVarObj.service_id].append(model_to_dict(envVarObj))
            else:
                envMap[envVarObj.service_id] = [model_to_dict(envVarObj)]
        context["envMap"] = envMap

        # 当前服务的连接信息
        currentEnvMap = {}
        currentEnvVarlist = TenantServiceEnvVar.objects.filter(
            service_id=self.service.service_id, scope__in=("outer", "both"), is_change=False
        )
        if len(currentEnvVarlist) > 0:
            for envVarObj in currentEnvVarlist:
                if envVarObj.service_id in currentEnvMap:
                    currentEnvMap[envVarObj.service_id].append(model_to_dict(envVarObj))
                else:
                    currentEnvMap[envVarObj.service_id] = [model_to_dict(envVarObj)]
        context["currentEnvMap"] = currentEnvMap

        opend_service_port_list = TenantServicesPort.objects.filter(
            service_id=self.service.service_id, is_inner_service=True
        )
        context["containerPortList"] = [port.container_port for port in opend_service_port_list]
        context["is_sys_admin"] = self.user.is_sys_admin
        context["is_private"] = sn.instance.is_private()
        context['cloud_assistant'] = sn.instance.cloud_assistant

    def get_mount_details(self, context):
        mnt_mount_relations = TenantServiceMountRelation.objects.filter(service_id=self.service.service_id)
        mounted_dependencies = []
        logger.debug('mnt_mount_rels:' + str(mnt_mount_relations.count()))
        if mnt_mount_relations.count() > 0:
            for mount in mnt_mount_relations:
                dep_service = TenantServiceInfo.objects.get(service_id=mount.dep_service_id)
                svc_group_rel = svc_grop_repo.get_rel_region(
                    dep_service.service_id, self.tenant.tenant_id, self.service.service_region
                )
                svc_group = None
                if svc_group_rel:
                    svc_group = ServiceGroup.objects.get(pk=svc_group_rel.group_id)
                logger.debug('mnt name is {0}, dep service id is {1}'.format(mount.mnt_name, mount.dep_service_id))
                dep_volume = baseService.get_volume_by_name(mount.mnt_name, mount.dep_service_id)
                logger.debug("dep mnt volume is none: {0}".format('Yes' if dep_volume is None else 'No'))
                if dep_volume:
                    mounted_dependencies.append({
                        "local_vol_path": mount.mnt_dir,
                        "dep_vol_name": dep_volume.volume_name,
                        "dep_vol_path": dep_volume.volume_path,
                        "dep_vol_type": dep_volume.volume_type,
                        "dep_app_name": dep_service.service_cname,
                        "dep_app_group": svc_group.group_name if svc_group else '未分组',
                        "dep_vol_id": dep_volume.ID
                    })
        context["mounted_apps"] = mounted_dependencies
        context["is_sys_admin"] = self.user.is_sys_admin
        volume_list = TenantServiceVolume.objects.filter(service_id=self.service.service_id)
        context["volume_list"] = [model_to_dict(volume) for volume in volume_list]

    def get_expansion_details(self, context):
        nodeList = []
        memoryList = []
        port_changeable = self.service.code_from
        context["port_changeable"] = port_changeable
        try:
            if self.service.service_key == "0000":
                sem = ServiceExtendMethod.objects.get(
                    service_key=self.service.service_key
                )
            else:
                sem = ServiceExtendMethod.objects.get(
                    service_key=self.service.service_key, app_version=self.service.version
                )
            nodeList.append(sem.min_node)
            next_node = sem.min_node + sem.step_node
            while (next_node <= sem.max_node):
                nodeList.append(next_node)
                next_node = next_node + sem.step_node

            num = 1
            memoryList.append(str(sem.min_memory))
            next_memory = sem.min_memory * pow(2, num)
            while (next_memory <= sem.max_memory):
                memoryList.append(str(next_memory))
                num = num + 1
                next_memory = sem.min_memory * pow(2, num)
        except Exception as e:
            nodeList.append(1)
            memoryList.append(str(self.service.min_memory))
            memoryList.append("256")
            memoryList.append("512")
            memoryList.append("1024")
            memoryList.append("2048")
            memoryList.append("4096")
            memoryList.append("8192")
        context["nodeList"] = nodeList
        context["extends_choices"] = self.extends_choices()
        context["memoryList"] = memoryList
        context["memorydict"] = self.memory_choices()
        context["is_private"] = sn.instance.is_private()
        port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id)
        context["ports"] = [model_to_dict(p) for p in port_list]

    def get_service_plugins(self, context):
        try:
            pluginList = [plugin_info.plugin_id
                          for plugin_info in plugin_svc.get_tenant_plugins(region=self.response_region, tenant=self.tenant)]
            relations = plugin_svc.get_tenant_service_plugin_relation(service_id=self.service.service_id)
            relationList = [relation_info.plugin_id for relation_info in relations]
            pluginList = list(set(pluginList).difference(set(relationList)))
            unRelationDict = []
            relationDict = []
            if pluginList > 0:
                for plugin_id in pluginList:
                    plugin_version = plugin_svc.get_tenant_plugin_newest_versions(self.response_region, self.tenant, plugin_id)
                    if len(plugin_version)  == 0:
                        continue
                    plugin_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, plugin_id)
                    pi = {}
                    pi["plugin_id"] = plugin_id
                    pi["is_switch"] = False
                    pi["plugin_info"] = model_to_dict(plugin_info)
                    pi["version_info"]= model_to_dict(plugin_version[0])
                    unRelationDict.append(pi)
            if relationList > 0:
                for r in relationList:
                    _plugin_version = plugin_svc.get_tenant_service_plugin_relation_by_plugin(self.service.service_id, r)
                    if len(_plugin_version) == 0:
                        continue
                    _plugin_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, r)
                    _pi = {}
                    _pi["plugin_id"] = r
                    _pi["is_switch"] = _plugin_version[0].plugin_status
                    _pi["plugin_info"] = model_to_dict(_plugin_info)
                    _pi["version_info"] = model_to_dict(_plugin_version[0])
                    _plugin_newest_version = plugin_svc.get_tenant_plugin_newest_versions(self.response_region, self.tenant, r)
                    if len(_plugin_newest_version) != 0:
                        if _plugin_version[0].build_version != _plugin_newest_version[0].build_version:
                            _pi["version_new"] = "has_newest"
                    relationDict.append(_pi)
            logger.debug("plugin.relation", "relationList is {0}, unrelationList is {1}".format(relationDict, unRelationDict))
            context["un_relations"] = unRelationDict
            context["relations"] = relationDict
        except Exception, e:
            logger.error("plugin.relation", e)
            context["un_relations"] = []
            context["relations"] = []

    def get_advanced_setting_details(self, context):
        context["git_tag"] = True if custom_config.GITLAB_SERVICE_API else False
        context["mnt_share_choices"] = self.mnt_share_choices()
        context["http_outer_service_ports"] = [model_to_dict(p) for p in self.get_outer_service_port()]
        # service git repository
        try:
            context["httpGitUrl"] = codeRepositoriesService.showGitUrl(self.service)
            if self.service.code_from == "gitlab_manual":
                href_url = self.service.git_url
                if href_url.startswith('git@'):
                    href_url = "http://" + href_url.replace(":", "/")[4:]
                context["href_url"] = href_url
        except Exception as e:
            pass

        context["envs"] = [model_to_dict(env) for env in TenantServiceEnvVar.objects.filter(
            service_id=self.service.service_id, scope__in=("inner", "both")
        ).exclude(container_port=-1)]

        if self.service.code_from is not None and self.service.code_from in ("image_manual"):
            context["show_git"] = False
        else:
            context["show_git"] = True

        sgrs = ServiceGroupRelation.objects.filter(
            tenant_id=self.tenant.tenant_id, region_name=self.response_region
        )
        context["serviceGroupIdMap"] = {sg.service_id: sg.group_id for sg in sgrs}
        context["serviceGroupNameMap"] = {g.ID: g.group_name for g in self.get_group_list()}
        # cloud_assistant为goodrain表示为公有云
        context['cloud_assistant'] = sn.instance.cloud_assistant
        # is_private表示为私有云
        context["is_private"] = sn.instance.is_private()
        context["team_invite"] = settings.MODULES["Team_Invite"]
        port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id)
        context["ports"] = [model_to_dict(p) for p in port_list]
        context["serviceCreateTime"] = self.service.create_time

    def get_cost_details(self, context, service_attach_info):
        context["service_attach_info"] = model_to_dict(service_attach_info)
        context["total_buy_memory"] = service_attach_info.min_memory * service_attach_info.min_node
        context["service"] = model_to_dict(self.service) if self.service else ''
        service_consume_list = ServiceConsume.objects.filter(
            tenant_id=self.tenant.tenant_id, service_id=self.service.service_id
        ).order_by("-ID")
        context["last_hour_consume"] = model_to_dict(service_consume_list[0]) if service_consume_list else None
        service_total_memory_fee = Decimal(0)
        service_total_disk_fee = Decimal(0)
        service_total_net_fee = Decimal(0)
        consume_list = list(service_consume_list)
        for service_consume in consume_list:
            service_consume.memory_pay_method = "postpaid"
            service_consume.disk_pay_method = "postpaid"
            if service_attach_info.buy_start_time <= service_consume.time <= service_attach_info.buy_end_time:
                if service_attach_info.memory_pay_method == "prepaid":
                    service_consume.memory_pay_method = "prepaid"
                if service_attach_info.disk_pay_method == "prepaid":
                    service_consume.disk_pay_method = "prepaid"
            service_total_memory_fee += service_consume.memory_money
            service_total_disk_fee += service_consume.disk_money
            service_total_net_fee += service_consume.net_money
        context["service_consume_list"] = [model_to_dict(consume) for consume in consume_list[:24]]
        context["service_total_memory_fee"] = service_total_memory_fee
        context["service_total_disk_fee"] = service_total_disk_fee
        context["service_total_net_fee"] = service_total_net_fee

    def get_service_list(self):
        services = baseService.get_service_list(
            self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region
        )
        services = list(services)
        for s in list(services):
            if s.service_alias == self.serviceAlias:
                s.is_selected = True
                services.insert(0, s)
                services.remove(s)
                break
        return [model_to_dict(s) for s in services]

    def get_group_list(self):
        grouplist = ServiceGroup.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region)
        return grouplist

    def get_user_tenant(self, user_id):
        """根据用户的ID获取当前用户的所有租户信息"""
        prt_list = PermRelTenant.objects.filter(user_id=user_id)
        tenant_id_list = [x.tenant_id for x in prt_list]
        # 查询租户信息
        tenant_list = Tenants.objects.filter(pk__in=tenant_id_list)
        return tenant_list

    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        tenant_region = TenantRegionInfo.objects.get(
            tenant_id=self.service.tenant_id, region_name=self.service.service_region
        )
        context = {
            'tenantName': self.tenantName,
            "tenant_pay_type": self.tenant.pay_type,
            'serviceAlias': self.serviceAlias,
            'tenantServiceList': self.get_service_list(),
            "groupList": [model_to_dict(group) for group in self.get_group_list()],
            "tenant_list": [model_to_dict(user) for user in self.get_user_tenant(self.user.pk)],
            "actions": {
                "tenant_actions": list(self.user.actions.tenant_actions),
                "service_actions": list(self.user.actions.service_actions)
            }
        }
        fr = request.GET.get("fr", "deployed")
        context["fr"] = fr
        # 判断是否社区版云帮
        context["community"] = True if sn.instance.is_private() else False
        context["is_public_cloud"] = (sn.instance.cloud_assistant == "goodrain" and (not sn.instance.is_private()))
        try:
            regionBo = rpmManager.get_work_region_by_name(self.response_region)
            memory_post_paid_price = regionBo.memory_trial_price  # 内存按需使用价格
            disk_post_paid_price = regionBo.disk_trial_price  # 磁盘按需使用价格
            net_post_paid_price = regionBo.net_trial_price  # 网络按需使用价格

            context['is_tenant_free'] = (self.tenant.pay_type == "free")
            context["tenantServiceInfo"] = model_to_dict(self.service) if self.service else ''
            context["myAppStatus"] = "active"
            context["perm_users"] = self.get_user_perms()
            plugin_memory = servicePluginResource.get_service_plugin_resource(self.service.service_id)
            context["totalMemory"] = self.service.min_node * (self.service.min_memory+plugin_memory)
            context["tenant"] = model_to_dict(self.tenant)
            context["region_name"] = self.service.service_region
            context["event_websocket_uri"] = self.get_ws_url(
                settings.EVENT_WEBSOCKET_URL[self.service.service_region], "event_log"
            )
            ws_type = "monitor_message"
            tenant_service_relations = plugin_svc.get_tenant_service_plugin_relation(self.service.service_id)
            for re in tenant_service_relations:
                plugin = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, re.plugin_id)
                if plugin.category == "analyst-plugin:perf" or plugin.category == "performance_analysis":
                    ws_type = "new_monitor_message"

            context["monitor_websocket_uri"] = self.get_ws_url(
                settings.EVENT_WEBSOCKET_URL[self.service.service_region], ws_type
            )

            context["wild_domain"] = settings.WILD_DOMAINS[self.service.service_region]
            if ServiceGroupRelation.objects.filter(service_id=self.service.service_id).count() > 0:
                gid = ServiceGroupRelation.objects.get(service_id=self.service.service_id).group_id
                context["group_id"] = gid
            else:
                context["group_id"] = -1
            service_domain = False
            if TenantServicesPort.objects.filter(
                    service_id=self.service.service_id, is_outer_service=True, protocol='http'
            ).exists():
                context["hasHttpServices"] = True
                service_domain = True
            is_public_cloud = (sn.instance.cloud_assistant == "goodrain" and (not sn.instance.is_private()))
            # 如果不为公有,则取cloudbang的值
            http_port_str = settings.WILD_PORTS["cloudbang"] if not is_public_cloud \
                else settings.WILD_PORTS[self.response_region]
            context['http_port_str'] = ":" + http_port_str

            service_attach_info = self.get_service_attach_info()
            now = datetime.now()
            if service_attach_info.buy_end_time < now:
                if service_attach_info.memory_pay_method == "prepaid" or service_attach_info.disk_pay_method == "prepaid":
                    service_attach_info.disk_pay_method = "postpaid"
                    service_attach_info.memory_pay_method = "postpaid"
                    service_attach_info.min_memory = self.service.min_memory
                    service_attach_info.min_node = self.service.min_node
                    service_attach_info.save()
            if fr == "deployed":
                self.get_deployed_details(context, http_port_str)
            elif fr == "ports":
                self.get_port_details(context)
            elif fr == "relations":
                self.get_dependeny_details(context)
            elif fr == "mnt":
                self.get_mount_details(context)
            elif fr == "expansion":
                self.get_expansion_details(context)
            elif fr == "statistic":
                context['statistic_type'] = self.statistic_type
                if self.service.service_type in ('mysql',):
                    context['ws_topic'] = '{0}.{1}.statistic'.format(self.tenant.tenant_id[-12:],
                                                                     self.service.service_id[-12:])
                else:
                    if self.service.port_type == "multi_outer":
                        context['ws_topic'] = '{0}.{1}.statistic'.format(self.tenant.tenant_name,
                                                                         self.service.service_alias)
                    else:
                        context['ws_topic'] = '{0}.{1}.statistic'.format(self.tenant.tenant_name,
                                                                         self.service.service_alias)
                service_port_list = TenantServicesPort.objects.filter(tenant_id=self.tenant.tenant_id,
                                                                      service_id=self.service.service_id)
                has_outer_port = False
                for p in service_port_list:
                    if (p.is_outer_service and p.protocol == "http") or self.service.service_type == 'mysql':
                        has_outer_port = True
                        break
                context["has_outer_port"] = has_outer_port
            elif fr == "settings":
                self.get_advanced_setting_details(context)
            elif fr == "cost":
                self.get_cost_details(context, service_attach_info)
            elif fr == "log":
                context["is_private"] = sn.instance.is_private()
            elif fr == "plugin":
                self.get_service_plugins(context)
            context['success'] = True
            return JsonResponse(data=context, status=200, safe=False)
        except Exception as e:
            logger.exception(e)
            return JsonResponse(data={'message': e.message, 'success': False}, status=500)


class AppServiceInfo(AuthedView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        context = {
            "community": True if sn.instance.is_private() else False,
            "service": model_to_dict(self.service),
            "monitor_control": settings.MODULES["Monitor_Control"]
        }
        return JsonResponse(data=context, status=200)


class ServiceListView(LeftSideBarMixin, AuthedView):
    def check_region(self):
        region = self.request.GET.get('region', None)
        if region is not None:
            if region in RegionInfo.region_names():
                if region == 'aws-bj-1' and self.tenant.region != 'aws-bj-1':
                    raise Http404
                self.response_region = region
            else:
                raise Http404

        if self.cookie_region == 'aws-bj-1':
            self.response_region == 'ali-sh'

        try:
            t_region, created = TenantRegionInfo.objects.get_or_create(tenant_id=self.tenant.tenant_id,
                                                                       region_name=self.response_region)
            self.tenant_region = t_region
        except Exception, e:
            logger.error(e)

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        self.check_region()
        context = {}
        tenant_service_list = baseService.get_service_list(
            self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region
        )
        service_group_name_map = {group.ID: group.group_name for group in self.get_group_list()}
        sgrs = ServiceGroupRelation.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region)
        service_group_id_map = {sgr.service_id: sgr.group_id for sgr in sgrs}
        sorted_service_list = []
        unsorted_service_list = []

        tenant_service_list = [model_to_dict(ts) for ts in tenant_service_list]

        for tenant_service in tenant_service_list:
            group_id = service_group_id_map.get(tenant_service["service_id"], None)
            if group_id is None:
                group_id = -1
            group_name = service_group_name_map.get(group_id, None)
            if group_name is None:
                group_name = "未分组"
            tenant_service["group_name"] = group_name
            if tenant_service["group_name"] == "未分组":
                unsorted_service_list.append(tenant_service)
            else:
                sorted_service_list.append(tenant_service)

        context["sorted_service_list"] = sorted(sorted_service_list,
                                                key=lambda service: (service["group_name"], service["service_cname"]))
        context["unsorted_service_list"] = sorted(unsorted_service_list, key=lambda service: service["service_cname"])
        return JsonResponse(data=context, status=200)


class ServiceOverView(LeftSideBarMixin, AuthedView):
    def check_region(self):
        region = self.request.GET.get('region', None)
        if region is not None:
            if region in RegionInfo.region_names():
                if region == 'aws-bj-1' and self.tenant.region != 'aws-bj-1':
                    raise Http404
                self.response_region = region
            else:
                raise Http404

        if self.cookie_region == 'aws-bj-1':
            self.response_region == 'ali-sh'

        try:
            t_region, created = TenantRegionInfo.objects.get_or_create(tenant_id=self.tenant.tenant_id,
                                                                       region_name=self.response_region)
            self.tenant_region = t_region
        except Exception, e:
            logger.error(e)

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        self.check_region()
        context = {
            "pay_type": self.tenant.pay_type,
            "tenant_balance": self.tenant.balance,
            "tenant_name": self.tenantName,
            "expired_time": self.tenant.expired_time,
        }
        status = tenantAccountService.get_monthly_payment(self.tenant, self.tenant.region)
        context["monthly_payment_status"] = status
        if status != 0:
            list = TenantRegionPayModel.objects.filter(
                tenant_id=self.tenant.tenant_id, region_name=self.tenant.region
            ).order_by("-buy_end_time")
            context["buy_end_time"] = list[0].buy_end_time

        tenantServiceList = baseService.get_service_list(
            self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region
        )
        context["total_app_number"] = len(tenantServiceList)
        totalNum = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).count()
        context["totalNum"] = totalNum

        return JsonResponse(data=context, status=200)


class ServiceTeamView(LeftSideBarMixin, AuthedView):
    def get_user_perms(self):
        perm_users = []
        perm_template = {
            'name': None,
            'adminCheck': False,
            'developerCheck': False, 'developerDisable': False,
            'viewerCheck': False, 'viewerDisable': False
        }

        identities = PermRelTenant.objects.filter(tenant_id=self.tenant.pk)

        user_id_list = [x.user_id for x in identities]
        user_list = Users.objects.filter(pk__in=user_id_list)
        user_map = {x.user_id: x for x in user_list}

        for i in identities:
            user_perm = perm_template.copy()
            user_info = user_map.get(i.user_id)
            if user_info is None:
                continue
            user_perm['name'] = user_info.nick_name
            if i.user_id == self.user.user_id:
                user_perm['selfuser'] = True
            if i.identity == 'admin':
                user_perm.update({
                    'adminCheck': True,
                    'developerCheck': True,
                    'developerDisable': True,
                    'viewerCheck': True,
                    'viewerDisable': True
                })
            elif i.identity == 'developer':
                user_perm.update({
                    'developerCheck': True,
                    'viewerCheck': True,
                    'viewerDisable': True
                })
            elif i.identity == 'viewer':
                user_perm.update({
                    'viewerCheck': True
                })
            perm_users.append(user_perm)
        return perm_users

    @perm_required('tenant_access')
    def get(self, request, *args, **kwargs):
        context = {
            "actions": {
                "tenant_actions": list(self.user.actions.tenant_actions),
                "service_actions": list(self.user.actions.service_actions)
            },
            "team_invite": settings.MODULES["Team_Invite"],
            "tenant_name": self.tenantName,
            "team_users": self.get_user_perms()
        }
        return JsonResponse(data=context, status=200)


class ServiceRechargeView(LeftSideBarMixin, AuthedView):
    @never_cache
    def get(self, request, *args, **kwargs):
        context = {
            "tenant_name": self.tenantName,
            "balance": self.tenant.balance,
            "myFinanceRecharge": "active",
            "myFinanceStatus": "active"
        }
        return JsonResponse(data=context, status=200)


class ServiceCostView(LeftSideBarMixin, AuthedView):
    @never_cache
    def get(self, request, *args, **kwargs):
        context = {
            "tenant_name": self.tenantName,
            "myFinanceRecharge": "active",
            "myFinanceStatus": "active"
        }
        return JsonResponse(data=context, status=200)


class ServiceBatchRenewalView(LeftSideBarMixin, AuthedView):
    @never_cache
    def get(self, request, *args, **kwargs):
        context = {
            "tenant_name": self.tenantName,
            "batch_renew": "active",
            "myFinanceRecharge": "active",
            "myFinanceStatus": "active"
        }
        return JsonResponse(data=context, status=200)

    @never_cache
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        result = {}
        sid = None
        try:
            regionBo = rpmManager.get_work_region_by_name(self.response_region)
            pre_paid_memory_price = regionBo.memory_package_price
            pre_paid_disk_price = regionBo.disk_package_price

            json_data = request.POST.get("data", "")
            if not json_data:
                result["result"] = False
                result["status"] = "params_error"
                result['message'] = "参数错误"
                return JsonResponse(result, status=400)

            data = json.loads(json_data)
            id_extendTime_map = {elem["service_id"]: elem["month_num"] for elem in data}
            service_id_list = id_extendTime_map.keys()
            renew_attach_infos = ServiceAttachInfo.objects.filter(service_id__in=service_id_list)
            renew_attach_infos = list(renew_attach_infos)
            total_money = Decimal(0)
            create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            bills = []
            for ps in renew_attach_infos:
                renew_money = Decimal(0)
                if ps.memory_pay_method == "prepaid":
                    memory_fee = (int(ps.min_memory) * int(ps.min_node)) / 1024.0 * float(pre_paid_memory_price)
                    renew_money += Decimal(memory_fee)
                if ps.disk_pay_method == "prepaid":
                    disk_fee = ps.disk / 1024.0 * float(pre_paid_disk_price)
                    renew_money += Decimal(disk_fee)
                extend_time = id_extendTime_map.get(ps.service_id)
                service_renew_money = renew_money * 24 * int(extend_time) * 30

                bill = ServiceFeeBill(tenant_id=self.tenant.tenant_id,
                                      service_id=ps.service_id,
                                      prepaid_money=service_renew_money,
                                      pay_status="payed",
                                      cost_type="renew",
                                      node_memory=ps.min_memory,
                                      node_num=ps.min_node,
                                      disk=ps.disk,
                                      buy_period=int(extend_time) * 24 * 30,
                                      create_time=create_time,
                                      pay_time=create_time)
                bills.append(bill)
                total_money += service_renew_money
            total_money = Decimal(str(round(total_money, 2)))
            # 如果钱不够
            if total_money > self.tenant.balance:
                result["result"] = False
                result["status"] = "not_enough"
                result['message'] = "账户余额不足以批量续费"
                return JsonResponse(result, status=200)
            sid = transaction.savepoint()
            ServiceFeeBill.objects.bulk_create(bills)
            for ps in renew_attach_infos:
                extend_time = int(id_extendTime_map.get(ps.service_id))
                ps.buy_end_time = ps.buy_end_time + datetime.timedelta(
                    days=extend_time * 30)
                ps.save()
            self.tenant.balance -= total_money
            self.tenant.save()
            transaction.savepoint_commit(sid)
            result["result"] = True
            result["status"] = "success"
            result['message'] = "续费成功"

        except Exception as e:
            if sid:
                transaction.savepoint_rollback(sid)
            logger.exception(e)
            result["result"] = False
            result["status"] = "internal_erro"
            result['message'] = "系统异常"
        return JsonResponse(result, status=200)


class SerivceAccountRechargesView(AuthedView):
    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        context = {
            "tenantName": self.tenantName,
            'serviceAlias': self.serviceAlias
        }
        date_scope = request.GET.get("datescope", "7")
        per_page = request.GET.get("perpage", "10")
        page = request.GET.get("page", "1")
        context["date_scope"] = date_scope
        context["curpage"] = page
        context["per_page"] = per_page
        try:
            tenant_id = self.tenant.tenant_id
            diffDay = int(date_scope)
            if diffDay > 0:
                end = datetime.datetime.now()
                endTime = end.strftime("%Y-%m-%d %H:%M:%S")
                start = datetime.date.today() - datetime.timedelta(days=int(date_scope))
                startTime = start.strftime('%Y-%m-%d') + " 00:00:00"
                recharges = TenantRecharge.objects.filter(
                    tenant_id=self.tenant.tenant_id, time__range=(startTime, endTime)
                )
            else:
                recharges = TenantRecharge.objects.filter(tenant_id=self.tenant.tenant_id)
            paginator = JuncheePaginator(recharges, int(per_page))
            tenantRecharges = paginator.page(int(page))
            context["rechargeTypeMap"] = RechargeTypeMap
            context["tenantRecharges"] = [model_to_dict(tr) for tr in tenantRecharges]
        except Exception as e:
            logger.exception(e)
        return JsonResponse(context, status=200)


class ServiceDeductionsView(AuthedView):
    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        context = {}
        query_day = request.GET.get("query_day", None)
        cookie_region = self.request.COOKIES.get('region', None)
        response_region = self.tenant.region if cookie_region is None else cookie_region
        now = datetime.now()
        try:
            if query_day:
                query_day += " 00:00:00"
                logger.debug("tenant {0} query consume records,query day is {1}".format(self.tenantName, query_day))
            else:
                query_day = now.strftime("%Y-%m-%d 00:00:00")
            start_time = datetime.strptime(query_day, "%Y-%m-%d 00:00:00")
            end_time_str = (start_time + datetime.timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
            start_time_str = start_time.strftime("%Y-%m-%d 00:00:00")

            service_consume_list = ServiceConsume.objects.filter(
                tenant_id=self.tenant.tenant_id, region=response_region, time__range=(start_time_str, end_time_str)
            )
            time_list = service_consume_list.values_list("time", flat=True).distinct()
            result_map = {}
            total_money = Decimal(0.00)
            for time_val in time_list[1:25]:
                current_hour_total_money = Decimal(0.00)
                for service_consume in service_consume_list:
                    if service_consume.time == time_val:
                        if TenantServiceInfo.objects.filter(service_id=service_consume.service_id).exists():
                            current_hour_total_money += service_consume.pay_money
                result_map[time_val] = current_hour_total_money
                total_money += current_hour_total_money
            result = sorted(result_map.iteritems(), reverse=True)
            context["length"] = len(result)
            context["result_map"] = result
            context["total_money"] = total_money
        except Exception as e:
            logger.error(e)
        return JsonResponse(context, status=200)


class ServiceDepMnt(AuthedView):
    @perm_required('tenant_account')
    def get(self, request, *args, **kwargs):
        page = request.GET.get('pageNumber', 1)
        page_size = request.GET.get('pageSize', 10)
        services = baseService.get_service_list(
            self.tenant.pk, self.user, self.tenant.tenant_id, self.service.service_region
        )
        service_ids = services.values_list('service_id', flat=True)

        dep_mnt_names = TenantServiceMountRelation.objects.filter(
            service_id=self.service.service_id
        ).values_list('mnt_name', flat=True)

        logger.debug('get shared volumes, service ids:{0}'.format(service_ids))
        shared_volumes = TenantServiceVolume.objects.filter(
            volume_type=TenantServiceVolume.SHARE, service_id__in=service_ids
        ).exclude(service_id=self.service.service_id).exclude(volume_name__in=dep_mnt_names)

        paginator = Paginator(shared_volumes, page_size)
        try:
            volumes = paginator.page(page)
        except PageNotAnInteger:
            volumes = paginator.page(1)
        except EmptyPage:
            volumes = paginator.page(paginator.num_pages)

        data = {'data': {
            'bean': '', 'list': [], 'total': len(shared_volumes), 'pageNumber': int(page), 'pageSize': int(page_size)},
            'code': '0000'
        }

        for vol in volumes:
            logger.debug('get service group rel,svc_id:{0},tenant_id:{1},region_name:{2},vol_name:{3}'.format(
                vol.service_id, self.tenant.tenant_id, self.service.service_region, vol.volume_name
            ))
            svc_group_rel = svc_grop_repo.get_rel_region(
                vol.service_id, self.tenant.tenant_id, self.service.service_region
            )
            svc_group = None
            if svc_group_rel:
                svc_group = ServiceGroup.objects.get(pk=svc_group_rel.group_id)
            data['data']['list'].append({
                "dep_app_name": services.get(service_id=vol.service_id).service_cname,
                "dep_app_group": svc_group.group_name if svc_group else '未分组',
                "dep_vol_name": vol.volume_name,
                "dep_vol_path": vol.volume_path,
                "dep_vol_type": vol.volume_type,
                "dep_vol_id": vol.ID
            })
        return JsonResponse(data=data, status=200)
