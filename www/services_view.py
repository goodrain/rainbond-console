# -*- coding: utf8 -*-
import logging
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.http import Http404

from share.manager.region_provier import RegionProviderManager
from www.models.main import TenantRegionPayModel, ServiceGroupRelation, ServiceCreateStep, ServiceAttachInfo, \
    TenantConsumeDetail
from www.views import BaseView, AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import (Users, ServiceInfo, TenantRegionInfo, TenantServiceInfo,
                        ServiceDomain, PermRelService, PermRelTenant,
                        TenantServiceRelation, TenantServicesPort, TenantServiceEnv,
                        TenantServiceEnvVar, TenantServiceMountRelation,
                        ServiceExtendMethod, TenantServiceVolume)
from www.region import RegionInfo
from service_http import RegionServiceApi
from django.conf import settings
from goodrain_web.custom_config import custom_config
from www.tenantservice.baseservice import BaseTenantService, TenantUsedResource, TenantAccountService, CodeRepositoriesService
from www.monitorservice.monitorhook import MonitorHook
from www.utils.url import get_redirect_url
from www.utils.md5Util import md5fun
import datetime

logger = logging.getLogger('default')
regionClient = RegionServiceApi()
monitorhook = MonitorHook()
tenantAccountService = TenantAccountService()
baseService = BaseTenantService()
tenantUsedResource = TenantUsedResource()
codeRepositoriesService = CodeRepositoriesService()
rpmManager = RegionProviderManager()

class TenantServiceAll(LeftSideBarMixin, AuthedView):

    def get_media(self):
        media = super(TenantServiceAll, self).get_media() + self.vendor(
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

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
            t_region, created = TenantRegionInfo.objects.get_or_create(tenant_id=self.tenant.tenant_id, region_name=self.response_region)
            self.tenant_region = t_region
        except Exception, e:
            logger.error(e)

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        self.check_region()
        context = self.get_context()
        try:
            self.response_tenant_name = self.tenant
            logger.debug('monitor.user', str(self.user.pk))
            tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region)
            context["tenantServiceList"] = tenantServiceList
            context["totalAppStatus"] = "active"
            context["totalFlow"] = 0
            context["totalAppNumber"] = len(tenantServiceList)
            context["tenantName"] = self.tenantName
            totalNum = PermRelTenant.objects.filter(tenant_id=self.tenant.ID).count()
            context["totalNum"] = totalNum
            context["curTenant"] = self.tenant
            context["tenant_balance"] = self.tenant.balance
            # params for prompt
            context["pay_type"] = self.tenant.pay_type
            # context["expired"] = tenantAccountService.isExpired(self.tenant,self.service)
            context["expired_time"] = self.tenant.expired_time
            status = tenantAccountService.get_monthly_payment(self.tenant, self.tenant.region)
            context["monthly_payment_status"] = status
            if status != 0:
                list = TenantRegionPayModel.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.tenant.region).order_by("-buy_end_time")
                context["buy_end_time"] = list[0].buy_end_time

            if self.tenant_region.service_status == 0:
                logger.debug("tenant.pause", "unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.unpause(self.response_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()
            elif self.tenant_region.service_status == 3:
                logger.debug("tenant.pause", "system unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.systemUnpause(self.response_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()
            # 获取组和服务的关系
            sgrs = ServiceGroupRelation.objects.filter(tenant_id=self.tenant.tenant_id, region_name=self.response_region)
            serviceGroupIdMap = {}
            for sgr in sgrs:
                serviceGroupIdMap[sgr.service_id] = sgr.group_id
            context["serviceGroupIdMap"] = serviceGroupIdMap

            serviceGroupNameMap = {}
            group_list = context["groupList"]
            for group in group_list:
                serviceGroupNameMap[group.ID] = group.group_name
            context["serviceGroupNameMap"] = serviceGroupNameMap

        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_my.html", context)


class TenantService(LeftSideBarMixin, AuthedView):

    def init_request(self, *args, **kwargs):
        fr = self.request.GET.get('fr', None)
        if fr is not None and fr == 'statistic':
            self.statistic = True
            self.statistic_type = self.request.GET.get('type', 'history')
        else:
            self.statistic = False

    def get_media(self):
        media = super(TenantService, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/style.css',
            'www/css/bootstrap-switch.min.css', 'www/css/bootstrap-editable.css',
            'www/css/style-responsive.css', 'www/js/jquery.cookie.js', 'www/js/service.js',
            'www/js/gr/basic.js', 'www/css/gr/basic.css', 'www/js/perms.js',
            'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js',
            'www/js/swfobject.js', 'www/js/web_socket.js', 'www/js/websoket-goodrain.js',
            'www/js/bootstrap-switch.min.js', 'www/js/bootstrap-editable.min.js', 'www/js/gr/multi_port.js'
        )
        if self.statistic:
            if self.statistic_type == 'history':
                append_media = (
                    'www/assets/nvd3/nv.d3.css', 'www/assets/nvd3/d3.min.js',
                    'www/assets/nvd3/nv.d3.min.js', 'www/js/gr/nvd3graph.js',
                )
            elif self.statistic_type == 'realtime':
                append_media = ('www/js/gr/ws_top.js',)
            media = media + self.vendor(*append_media)
        return media

    def get_context(self):
        context = super(TenantService, self).get_context()
        return context

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
        service_manager = {"deployed": False}
        if self.service.service_key == 'mysql':
            has_managers = TenantServiceInfo.objects.filter(
                tenant_id=self.tenant.tenant_id, service_region=self.service.service_region, service_key='phpmyadmin')
            if has_managers:
                service_manager['deployed'] = True
                manager = has_managers[0]
                service_manager[
                    'url'] = 'http://{0}.{1}{2}:{3}'.format(manager.service_alias, self.tenant.tenant_name, settings.WILD_DOMAINS[self.service.service_region], http_port_str)
            else:
                # 根据服务版本获取对应phpmyadmin版本,暂时解决方法,待优化
                app_version = '4.4.12'
                if self.service.version == "5.6.30":
                    app_version = '4.6.3'
                service_manager['url'] = '/apps/{0}/service-deploy/?service_key=phpmyadmin&app_version={1}'.format(self.tenant.tenant_name, app_version)
        return service_manager

    def memory_choices(self):
        memory_dict = {}
        memory_dict["128"] = '128M'
        memory_dict["256"] = '256M'
        memory_dict["512"] = '512M'
        memory_dict["1024"] = '1G'
        memory_dict["2048"] = '2G'
        memory_dict["4096"] = '4G'
        memory_dict["8192"] = '8G'
        memory_dict["16384"] = '16G'
        memory_dict["32768"] = '32G'
        memory_dict["65536"] = '64G'
        return memory_dict

    def extends_choices(self):
        extends_dict = {}
        extends_dict["state"] = u'有状态'
        extends_dict["stateless"] = u'无状态'
        extends_dict["state-expend"] = u'有状态可水平扩容'
        return extends_dict

    # 服务挂载卷类型下拉列表选项
    def mnt_share_choices(self):
        mnt_share_type = {}
        mnt_share_type["shared"] = u'共享'
        # mnt_share_type["exclusive"] = u'独享'
        return mnt_share_type

    # 获取所有的开放的http对外端口
    def get_outer_service_port(self):
        out_service_port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id, is_outer_service=True, protocol='http')
        return out_service_port_list

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
        service_attach_info.buy_start_time = datetime.datetime.now()
        service_attach_info.buy_end_time = datetime.datetime.now()
        service_attach_info.create_time = datetime.datetime.now()
        return service_attach_info

    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        self.response_region = self.service.service_region
        self.tenant_region = TenantRegionInfo.objects.get(tenant_id=self.service.tenant_id, region_name=self.service.service_region)
        context = self.get_context()
        context["tenantName"] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        fr = request.GET.get("fr", "deployed")
        context["fr"] = fr
        try:
            regionBo = rpmManager.get_work_region_by_name(self.response_region)
            memory_post_paid_price = regionBo.memory_trial_price  # 内存按需使用价格
            disk_post_paid_price = regionBo.disk_trial_price  # 磁盘按需使用价格
            net_post_paid_price = regionBo.net_trial_price  # 网络按需使用价格
            if self.service.category == "application":
                # forbidden blank page
                if self.service.code_version is None or self.service.code_version == "" or (self.service.git_project_id == 0 and self.service.git_url is None):
                    codeRepositoriesService.initRepositories(self.tenant, self.user, self.service, "gitlab_new", "", "", "master")
                    self.service = TenantServiceInfo.objects.get(service_id=self.service.service_id)

                if ServiceCreateStep.objects.filter(service_id=self.service.service_id,
                                                    tenant_id=self.tenant.tenant_id).count() > 0:
                    app_step = ServiceCreateStep.objects.get(service_id=self.service.service_id,
                                                             tenant_id=self.tenant.tenant_id).app_step
                    logger.debug("create service step" + str(app_step))
                    if app_step == 2:
                        codeRepositoriesService.codeCheck(self.service)
                        return self.redirect_to('/apps/{0}/{1}/app-waiting/'.format(self.tenant.tenant_name, self.service.service_alias))
                    if app_step == 3:
                        return self.redirect_to('/apps/{0}/{1}/app-setting/'.format(self.tenant.tenant_name, self.service.service_alias))
                    if app_step == 4:
                        return self.redirect_to('/apps/{0}/{1}/app-language/'.format(self.tenant.tenant_name, self.service.service_alias))

                # # no upload code
                # if self.service.language == "" or self.service.language is None:
                #     codeRepositoriesService.codeCheck(self.service)
                #     return self.redirect_to('/apps/{0}/{1}/app-waiting/'.format(self.tenant.tenant_name, self.service.service_alias))
                # if self.service.code_from not in ("image_manual"):
                #     tse = TenantServiceEnv.objects.get(service_id=self.service.service_id)
                #     if tse.user_dependency is None or tse.user_dependency == "":
                #         return self.redirect_to('/apps/{0}/{1}/app-waiting/'.format(self.tenant.tenant_name, self.service.service_alias))

            service_consume_detail_list = TenantConsumeDetail.objects.filter(tenant_id=self.tenant.tenant_id,
                                                                             service_id=self.service.service_id).order_by("-ID")
            last_hour_cost = None
            if len(service_consume_detail_list) > 0:
                last_hour_cost = service_consume_detail_list[0]
            if last_hour_cost is not None:
                last_hour_cost.memory_fee = round(
                    last_hour_cost.memory / 1024 * memory_post_paid_price * last_hour_cost.node_num, 2)
                last_hour_cost.disk_fee = round(last_hour_cost.disk / 1024 * disk_post_paid_price, 2)
                last_hour_cost.net_fee = round(last_hour_cost.net / 1024 * net_post_paid_price, 2)
                last_hour_cost.total_fee = last_hour_cost.disk_fee + last_hour_cost.memory_fee + last_hour_cost.net_fee
                context["last_hour_cost"] = last_hour_cost
            context['is_tenant_free'] = (self.tenant.pay_type == "free")

            context["tenantServiceInfo"] = self.service
            context["myAppStatus"] = "active"
            context["perm_users"] = self.get_user_perms()
            context["totalMemory"] = self.service.min_node * self.service.min_memory
            context["tenant"] = self.tenant
            context["region_name"] = self.service.service_region
            context["websocket_uri"] = settings.WEBSOCKET_URL[self.service.service_region]
            context["wild_domain"] = settings.WILD_DOMAINS[self.service.service_region]
            if ServiceGroupRelation.objects.filter(service_id=self.service.service_id).count() > 0:
                gid = ServiceGroupRelation.objects.get(service_id=self.service.service_id).group_id
                context["group_id"] = gid
            else:
                context["group_id"] = -1
            service_domain = False
            if TenantServicesPort.objects.filter(service_id=self.service.service_id, is_outer_service=True, protocol='http').exists():
                context["hasHttpServices"] = True
                service_domain = True

            http_port_str = settings.WILD_PORTS[self.response_region]
            context['http_port_str'] = ":" + http_port_str

            if fr == "deployed":
                if self.service.service_type == 'mysql':
                    service_manager = self.get_manage_app(http_port_str)
                    context['service_manager'] = service_manager

                # inner service
                innerPorts = {}
                tsps = TenantServicesPort.objects.filter(service_id=self.service.service_id, is_inner_service=True)
                for tsp in tsps:
                    innerPorts[tsp.container_port] = True

                if len(tsps) > 0:
                    context["hasInnerServices"] = True

                envMap = {}
                envVarlist = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, scope__in=("outer", "both"),is_change=False)
                if len(envVarlist) > 0:
                    for evnVarObj in envVarlist:
                        arr = envMap.get(evnVarObj.service_id)
                        if arr is None:
                            arr = []
                        arr.append(evnVarObj)
                        envMap[evnVarObj.service_id] = arr
                context["envMap"] = envMap

                containerPortList = []
                opend_service_port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id, is_inner_service=True)
                if len(opend_service_port_list) > 0:
                    for opend_service_port in opend_service_port_list:
                        containerPortList.append(opend_service_port.container_port)
                context["containerPortList"] = containerPortList
                
                if self.service.code_from != "image_manual":
                    baseservice = ServiceInfo.objects.get(service_key=self.service.service_key, version=self.service.version)
                    if baseservice.update_version != self.service.update_version:
                        context["updateService"] = True

                context["docker_console"] = settings.MODULES["Docker_Console"]
                context["publish_service"] = settings.MODULES["Publish_Service"]

                # get port type
                context["visit_port_type"] = self.service.port_type
                if self.service.port_type == "multi_outer":
                    context["http_outer_service_ports"] = self.get_outer_service_port()

            elif fr == "relations":
                # service relationships
                tsrs = TenantServiceRelation.objects.filter(service_id=self.service.service_id)
                relationsids = []
                if len(tsrs) > 0:
                    for tsr in tsrs:
                        relationsids.append(tsr.dep_service_id)
                context["serviceIds"] = relationsids
                # service map
                map = {}
                sids = [self.service.service_id]
                tenantServiceList = baseService.get_service_list(self.tenant.pk, self.user, self.tenant.tenant_id, region=self.response_region)
                for tenantService in tenantServiceList:
                    if TenantServicesPort.objects.filter(service_id=tenantService.service_id, is_inner_service=True).exists():
                        sids.append(tenantService.service_id)
                        map[tenantService.service_id] = tenantService
                    if tenantService.service_id in relationsids:
                        map[tenantService.service_id] = tenantService
                context["serviceMap"] = map
                # env map
                envMap = {}
                envVarlist = TenantServiceEnvVar.objects.filter(service_id__in=sids, scope__in=("outer", "both"))
                for evnVarObj in envVarlist:
                    arr = envMap.get(evnVarObj.service_id)
                    if arr is None:
                        arr = []
                    arr.append(evnVarObj)
                    envMap[evnVarObj.service_id] = arr
                context["envMap"] = envMap

                # add dir mnt
                mtsrs = TenantServiceMountRelation.objects.filter(service_id=self.service.service_id)
                mntsids = []
                if len(mtsrs) > 0:
                    for mnt in mtsrs:
                        mntsids.append(mnt.dep_service_id)
                context["mntsids"] = mntsids

            elif fr == "statistic":
                context['statistic_type'] = self.statistic_type
                if self.service.service_type in ('mysql',):
                    context['ws_topic'] = '{0}.{1}.statistic'.format(''.join(list(self.tenant.tenant_id)[1::2]), ''.join(list(self.service.service_id)[::2]))
                else:
                    context['ws_topic'] = '{0}.{1}.statistic'.format(self.tenant.tenant_name, self.service.service_alias)
            elif fr == "log":
                pass
            elif fr == "settings":
                nodeList = []
                memoryList = []
                try:
                    sem = ServiceExtendMethod.objects.get(service_key=self.service.service_key, app_version=self.service.version)
                    nodeList.append(sem.min_node)
                    next_node = sem.min_node + sem.step_node
                    while(next_node <= sem.max_node):
                        nodeList.append(next_node)
                        next_node = next_node + sem.step_node

                    num = 1
                    memoryList.append(str(sem.min_memory))
                    next_memory = sem.min_memory * pow(2, num)
                    while(next_memory <= sem.max_memory):
                        memoryList.append(str(next_memory))
                        num = num + 1
                        next_memory = sem.min_memory * pow(2, num)
                except Exception as e:
                    nodeList.append(1)
                    memoryList.append(str(self.service.min_memory))
                    memoryList.append("1024")
                    memoryList.append("2048")
                    memoryList.append("4096")
                    memoryList.append("8192")

                context["nodeList"] = nodeList
                context["memoryList"] = memoryList
                context["memorydict"] = self.memory_choices()
                context["extends_choices"] = self.extends_choices()
                context["add_port"] = settings.MODULES["Add_Port"]
                if custom_config.GITLAB_SERVICE_API :
                    context["git_tag"] = True
                else:
                    context["git_tag"] = False
                context["mnt_share_choices"] = self.mnt_share_choices()
                context["http_outer_service_ports"] = self.get_outer_service_port()
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
                if service_domain:
                    # service domain
                    # domain_num = ServiceDomain.objects.filter(service_id=self.service.service_id).count()
                    # if domain_num == 1:
                    #     domain = ServiceDomain.objects.get(service_id=self.service.service_id)
                    #     context["serviceDomain"] = domain
                    serviceDomainlist = ServiceDomain.objects.filter(service_id=self.service.service_id)
                    if len(serviceDomainlist) > 0:
                        data = {}
                        for domain in serviceDomainlist:
                            if data.get(domain.container_port) is None:
                                data[domain.container_port] = [domain.domain_name]
                            else:
                                data[domain.container_port].append(domain.domain_name)
                        context["serviceDomainDict"] = data

                port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id)
                outer_port_exist = reduce(lambda x, y: x or y, [t.is_outer_service for t in list(port_list)])
                context["ports"] = list(port_list)
                context["outer_port_exist"] = outer_port_exist
                # 付费用户或者免费用户的mysql,免费用户的docker
                context["outer_auth"] = self.tenant.pay_type != "free" or self.service.service_type == 'mysql' or self.service.language == "docker"
                # 付费用户,管理员的application类型服务可以修改port
                context["port_auth"] = (self.tenant.pay_type != "free" or self.user.is_sys_admin) and self.service.service_type == "application"
                context["envs"] = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id, scope__in=("inner", "both")).exclude(container_port= -1)

                # 获取挂载信息,查询
                volume_list = TenantServiceVolume.objects.filter(service_id=self.service.service_id)
                # result_list = []
                # for volume in list(volume_list):
                #     tmp_path = volume.volume_path
                # if tmp_path:
                #     volume.volume_path = tmp_path.replace("/app", "", 1)
                # result_list.append(volume)
                context["volume_list"] = volume_list

                if self.service.code_from is not None and self.service.code_from in ("image_manual"):
                    context["show_git"] = False
                else:
                    context["show_git"] = True

            elif fr == "cost":
                service_attach_info =None
                try:
                    service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                        service_id=self.service.service_id)
                except ServiceAttachInfo.DoesNotExist:
                    pass
                if service_attach_info is None:
                    service_attach_info = self.generate_service_attach_info()

                context["service_attach_info"] = service_attach_info

                service_consume_detail_list = TenantConsumeDetail.objects.filter(tenant_id=self.tenant.tenant_id,
                                                                                 service_id=self.service.service_id).order_by("-ID")

                regionBo = rpmManager.get_work_region_by_name(self.response_region)
                memory_pre_paid_price = regionBo.memory_package_price  # 内存预付费价格
                memory_post_paid_price = regionBo.memory_trial_price  # 内存按需使用价格
                disk_pre_paid_price = regionBo.disk_package_price  # 磁盘预付费价格
                disk_post_paid_price = regionBo.disk_trial_price  # 磁盘按需使用价格
                net_post_paid_price = regionBo.net_trial_price  # 网络按需使用价格

                last_hour_detail = None
                if len(list(service_consume_detail_list)) > 0:
                    last_hour_detail = list(service_consume_detail_list)[0]
                last_hour_detail.memory_fee = round(
                    last_hour_detail.memory / 1024 * memory_post_paid_price * last_hour_detail.node_num, 2)
                last_hour_detail.disk_fee = round(last_hour_detail.disk / 1024 * disk_post_paid_price, 2)
                last_hour_detail.net_fee = round(last_hour_detail.net / 1024 * net_post_paid_price, 2)
                context["last_hour_detail"] = last_hour_detail

                # 费用总计
                total_memory_price = 0
                total_disk_price = 0
                total_net_price = 0
                for service_consume in service_consume_detail_list:
                    service_consume.original_memory_unit_price = memory_post_paid_price
                    service_consume.original_disk_unit_price = disk_post_paid_price
                    service_consume.is_memory_pre_paid = False
                    service_consume.is_disk_pre_paid = False
                    # 未超出预付费期限
                    if service_attach_info.buy_start_time <= service_consume.time <= service_attach_info.buy_end_time:
                        # 如果内存为预付费
                        if service_attach_info.memory_pay_method == 'prepaid':
                            service_consume.memory_unit_price = memory_pre_paid_price
                            service_consume.is_memory_pre_paid = True
                        # 如果内存为后付费
                        else:
                            service_consume.memory_unit_price = memory_post_paid_price
                        # 如果磁盘为预付费
                        if service_attach_info.disk_pay_method == 'prepaid':
                            service_consume.disk_unit_price = disk_pre_paid_price
                            service_consume.is_disk_pre_paid = True
                        # 如果磁盘为后付费
                        else:
                            service_consume.disk_unit_price = disk_post_paid_price
                    # 超出预付费期限
                    else:
                        service_consume.disk_unit_price = disk_post_paid_price
                        service_consume.memory_unit_price = memory_post_paid_price


                    service_consume.net_unit_price = net_post_paid_price

                    # total_memory_price += service_consume.memory / 1024 * service_consume.memory_unit_price
                    # total_disk_price += service_consume.disk / 1024 * service_consume.disk_unit_price
                    # total_net_price += service_consume.net / 1024 * service_consume.net_unit_price
                    total_memory_price += float(service_consume.memory * memory_post_paid_price) / 1024
                    total_disk_price += float(service_consume.disk * disk_post_paid_price) / 1024
                    total_net_price += float(service_consume.net * net_post_paid_price) / 1024
                    # 费用
                    service_consume.memory_fee = round(float(service_consume.memory * memory_post_paid_price) / 1024, 2)
                    service_consume.disk_fee = round(float(service_consume.disk * disk_post_paid_price) / 1024, 2)
                    service_consume.net_fee = round(float(service_consume.net * net_post_paid_price) / 1024, 2)
                    if service_consume.is_memory_pre_paid:
                        service_consume.infact_memory_fee = 0
                        service_consume.infact_disk_fee = 0
                    else:
                        service_consume.infact_memory_fee = service_consume.memory_fee
                        service_consume.infact_disk_fee = service_consume.disk_fee
                    service_consume.one_hour_total = service_consume.infact_memory_fee+service_consume.infact_disk_fee+service_consume.net_fee

                    # 为了按G显示用
                    service_consume.memory = round(float(service_consume.memory) / 1024, 3)
                    service_consume.disk = round(float(service_consume.disk) / 1024, 3)
                    service_consume.net = round(float(service_consume.net) / 1024, 3)
                context['service_consume_detail_list'] = list(service_consume_detail_list)[:24]
                context['total_memory_price'] = round(total_memory_price, 2)
                context['total_disk_price'] = round(total_disk_price, 2)
                context['total_net_price'] = round(total_net_price, 2)
                context['buy_end_time'] = service_attach_info.buy_end_time
                context['service'] = self.service


            else:
                return self.redirect_to('/apps/{0}/{1}/detail/'.format(self.tenant.tenant_name, self.service.service_alias))

            if self.tenant_region.service_status == 0:
                logger.debug("tenant.pause", "unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.unpause(self.service.service_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()

            elif self.tenant_region.service_status == 3:
                logger.debug("tenant.pause", "system unpause tenant_id=" + self.tenant_region.tenant_id)
                regionClient.systemUnpause(self.service.service_region, self.tenant_region.tenant_id)
                self.tenant_region.service_status = 1
                self.tenant_region.save()
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_detail.html", context)


class ServiceGitHub(BaseView):

    @never_cache
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", "")
        state = request.GET.get("state", "")
        if code != "" and state != "" and int(state) == self.user.pk:
            result = codeRepositoriesService.get_gitHub_access_token(code)
            content = json.loads(result)
            token = content["access_token"]
            user = Users.objects.get(user_id=int(state))
            user.github_token = token
            user.save()
        tenantName = request.session.get("app_tenant")
        logger.debug(tenantName)
        return self.redirect_to("/apps/" + tenantName + "/app-create/?from=git")


class ServiceLatestLog(AuthedView):

    def get_media(self):
        media = super(ServiceLatestLog, self).get_media() + self.vendor('www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
                                                                        'www/js/jquery.cookie.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            data = {}
            data['number'] = 1000
            body = regionClient.latest_log(self.service.service_region, self.service.service_id, json.dumps(data))
            context["lines"] = body["lines"]
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_docker_log.html", context)


class ServiceHistoryLog(AuthedView):

    def get_media(self):
        media = super(ServiceHistoryLog, self).get_media() + self.vendor('www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
                                                                         'www/js/jquery.cookie.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            body = regionClient.history_log(self.service.service_region, self.service.service_id)
            context["log_paths"] = body["log_path"]
            context["tenantService"] = self.service
            context["log_domain"] = settings.LOG_DOMAIN[self.service.service_region]
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/service_history_log.html", context)


class ServiceDockerContainer(AuthedView):

    def get_media(self):
        media = super(ServiceDockerContainer, self).get_media()
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        response = redirect(get_redirect_url("/apps/{0}/{1}/detail/".format(self.tenantName, self.serviceAlias), request))
        try:
            docker_c_id = request.COOKIES.get('docker_c_id', '')
            docker_h_id = request.COOKIES.get('docker_h_id', '')
            docker_s_id = request.COOKIES.get('docker_s_id', '')
            if docker_c_id != "" and docker_h_id != "" and docker_s_id != "" and docker_s_id == self.service.service_id:
                t_docker_h_id = docker_h_id.lower()
                context["tenant_id"] = self.service.tenant_id
                context["service_id"] = docker_s_id
                context["ctn_id"] = docker_c_id
                context["host_id"] = t_docker_h_id
                context["md5"] = md5fun(self.service.tenant_id + "_" + docker_s_id + "_" + docker_c_id)
                pro = settings.DOCKER_WSS_URL.get("type", "ws")
                if pro == "ws":
                    context["wss"] = pro + "://" + settings.DOCKER_WSS_URL[self.service.service_region] + "/ws?nodename=" + t_docker_h_id
                else:
                    context["wss"] = pro + "://" + settings.DOCKER_WSS_URL[self.service.service_region] + "/ws?nodename=" + t_docker_h_id

                response = TemplateResponse(self.request, "www/console.html", context)
            response.delete_cookie('docker_c_id')
            response.delete_cookie('docker_h_id')
            response.delete_cookie('docker_s_id')
        except Exception as e:
            logger.exception(e)
        return response
