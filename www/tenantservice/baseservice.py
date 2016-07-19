# -*- coding: utf8 -*-
import datetime
import json

from www.db import BaseConnection
from www.models import Users, TenantServiceInfo, PermRelTenant, Tenants, \
    TenantServiceRelation, TenantServiceAuth, TenantServiceEnvVar, \
    TenantRegionInfo, TenantServicesPort, TenantServiceMountRelation, \
    TenantServiceVolume
from www.service_http import RegionServiceApi
from django.conf import settings
from www.monitorservice.monitorhook import MonitorHook
from www.gitlab_http import GitlabApi
from www.github_http import GitHubApi
from www.utils.giturlparse import parse as git_url_parse

import logging
logger = logging.getLogger('default')

monitorhook = MonitorHook()
regionClient = RegionServiceApi()
gitClient = GitlabApi()
gitHubClient = GitHubApi()


class BaseTenantService(object):

    def get_service_list(self, tenant_pk, user, tenant_id, region):
        user_pk = user.pk
        if user.is_sys_admin:
            services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region)
        else:
            my_tenant_identity = PermRelTenant.objects.get(tenant_id=tenant_pk, user_id=user_pk).identity
            if my_tenant_identity in ('admin', 'developer', 'viewer', 'gray'):
                services = TenantServiceInfo.objects.filter(tenant_id=tenant_id, service_region=region).order_by('service_alias')
            else:
                dsn = BaseConnection()
                query_sql = '''
                    select s.* from tenant_service s, service_perms sp where s.tenant_id = "{tenant_id}"
                    and sp.user_id = {user_id} and sp.service_id = s.ID and s.service_region = "{region}" order by s.service_alias
                    '''.format(tenant_id=tenant_id, user_id=user_pk, region=region)
                services = dsn.query(query_sql)
        return services

    def getMaxPort(self, tenant_id, service_key, service_alias):
        cur_service_port = 0
        dsn = BaseConnection()
        query_sql = '''select max(service_port) as service_port from tenant_service where tenant_id="{tenant_id}" and service_key="{service_key}" and service_alias !="{service_alias}";
            '''.format(tenant_id=tenant_id, service_key=service_key, service_alias=service_alias)
        data = dsn.query(query_sql)
        logger.debug(data)
        if data is not None:
            temp = data[0]["service_port"]
            if temp is not None:
                cur_service_port = int(temp)
        return cur_service_port
    
    def getInnerServicePort(self, tenant_id, service_key):
        cur_service_port = 0
        dsn = BaseConnection()
        query_sql = '''select max(service_port) as service_port from tenant_service where tenant_id="{tenant_id}" and service_key="{service_key}";
            '''.format(tenant_id=tenant_id, service_key=service_key)
        data = dsn.query(query_sql)
        logger.debug(data)
        if data is not None:
            temp = data[0]["service_port"]
            if temp is not None:
                cur_service_port = int(temp)
        return cur_service_port

    def prepare_mapping_port(self, service, container_port):
        port_list = TenantServicesPort.objects.filter(tenant_id=service.tenant_id, mapping_port__gt=container_port).values_list(
            'mapping_port', flat=True).order_by('mapping_port')

        port_list = list(port_list)
        port_list.insert(0, container_port)
        max_port = reduce(lambda x, y: y if (y - x) == 1 else x, port_list)
        return max_port + 1
    
    def create_service(self, service_id, tenant_id, service_alias, service, creater, region):
        tenantServiceInfo = {}
        tenantServiceInfo["service_id"] = service_id
        tenantServiceInfo["tenant_id"] = tenant_id
        tenantServiceInfo["service_key"] = service.service_key
        tenantServiceInfo["service_alias"] = service_alias
        tenantServiceInfo["service_region"] = region
        tenantServiceInfo["desc"] = service.desc
        tenantServiceInfo["category"] = service.category
        tenantServiceInfo["image"] = service.image
        tenantServiceInfo["cmd"] = service.cmd
        tenantServiceInfo["setting"] = service.setting
        tenantServiceInfo["extend_method"] = service.extend_method
        tenantServiceInfo["env"] = service.env
        tenantServiceInfo["min_node"] = service.min_node
        tenantServiceInfo["min_cpu"] = service.min_cpu
        tenantServiceInfo["min_memory"] = service.min_memory
        tenantServiceInfo["inner_port"] = service.inner_port
        tenantServiceInfo["version"] = service.version
        tenantServiceInfo["namespace"] = service.namespace
        tenantServiceInfo["update_version"] = service.update_version
        volume_path = ""
        host_path = ""
        if bool(service.volume_mount_path):
            volume_path = service.volume_mount_path
            logger.debug("region:{0} and service_type:{1}".format(region, service.service_type))
            if (region == "ucloud-bj-1" or region == "ali-sh") and service.service_type == "mysql":
                host_path = "/app-data/tenant/" + tenant_id + "/service/" + service_id
            else:
                host_path = "/grdata/tenant/" + tenant_id + "/service/" + service_id
        tenantServiceInfo["volume_mount_path"] = volume_path
        tenantServiceInfo["host_path"] = host_path
        if service.service_key == 'application':
            tenantServiceInfo["deploy_version"] = ""
        else:
            tenantServiceInfo["deploy_version"] = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        tenantServiceInfo["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tenantServiceInfo["git_project_id"] = 0
        tenantServiceInfo["service_type"] = service.service_type
        tenantServiceInfo["creater"] = creater
        tenantServiceInfo["total_memory"] = service.min_node * service.min_memory
        newTenantService = TenantServiceInfo(**tenantServiceInfo)
        newTenantService.save()
        return newTenantService
    
    def create_region_service(self, newTenantService, domain, region, nick_name, do_deploy=True):
        data = {}
        data["tenant_id"] = newTenantService.tenant_id
        data["service_id"] = newTenantService.service_id
        data["service_key"] = newTenantService.service_key
        data["comment"] = newTenantService.desc
        data["image_name"] = newTenantService.image
        data["container_cpu"] = newTenantService.min_cpu
        data["container_memory"] = newTenantService.min_memory
        data["volume_path"] = "vol" + newTenantService.service_id[0:10]
        data["volume_mount_path"] = newTenantService.volume_mount_path
        data["host_path"] = newTenantService.host_path
        data["extend_method"] = newTenantService.extend_method
        data["status"] = 0
        data["replicas"] = newTenantService.min_node
        data["service_alias"] = newTenantService.service_alias
        data["service_version"] = newTenantService.version
        data["container_env"] = newTenantService.env
        data["container_cmd"] = newTenantService.cmd
        data["node_label"] = ""
        data["deploy_version"] = newTenantService.deploy_version if do_deploy else None
        data["domain"] = domain
        data["category"] = newTenantService.category
        data["operator"] = nick_name
        data["service_type"] = newTenantService.service_type
        data["extend_info"] = {"ports": [], "envs": []}
        data["namespace"] = newTenantService.namespace
    
        ports_info = TenantServicesPort.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        if ports_info:
            data["extend_info"]["ports"] = list(ports_info)
    
        envs_info = TenantServiceEnvVar.objects.filter(service_id=newTenantService.service_id).values(
            'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if envs_info:
            data["extend_info"]["envs"] = list(envs_info)
    
        logger.debug(newTenantService.tenant_id + " start create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        regionClient.create_service(region, newTenantService.tenant_id, json.dumps(data))
        logger.debug(newTenantService.tenant_id + " end create_service:" + datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
    
    def create_service_dependency(self, tenant_id, service_id, dep_service_id, region):
        dependS = TenantServiceInfo.objects.get(service_id=dep_service_id)
        task = {}
        task["dep_service_id"] = dep_service_id
        task["tenant_id"] = tenant_id
        task["dep_service_type"] = dependS.service_type
        regionClient.createServiceDependency(region, service_id, json.dumps(task))
        tsr = TenantServiceRelation()
        tsr.tenant_id = tenant_id
        tsr.service_id = service_id
        tsr.dep_service_id = dep_service_id
        tsr.dep_service_type = dependS.service_type
        tsr.dep_order = 0
        tsr.save()
    
    def cancel_service_dependency(self, tenant_id, service_id, dep_service_id, region):
        task = {}
        task["dep_service_id"] = dep_service_id
        task["tenant_id"] = tenant_id
        task["dep_service_type"] = "v"
        regionClient.cancelServiceDependency(region, service_id, json.dumps(task))
        TenantServiceRelation.objects.get(service_id=service_id, dep_service_id=dep_service_id).delete()
    
    def create_service_env(self, tenant_id, service_id, region):
        tenantServiceEnvList = TenantServiceEnvVar.objects.filter(service_id=service_id)
        data = {}
        for tenantServiceEnv in tenantServiceEnvList:
            data[tenantServiceEnv.attr_name] = tenantServiceEnv.attr_value
        task = {}
        task["tenant_id"] = tenant_id
        task["attr"] = data
        task["scope"] = "outer"
        service = TenantServiceInfo.objects.get(service_id=service_id)
        task["container_port"] = service.inner_port
        regionClient.createServiceEnv(region, service_id, json.dumps(task))
    
    def cancel_service_env(self, tenant_id, service_id, region):
        task = {}
        task["tenant_id"] = tenant_id
        task["attr"] = {}
        regionClient.createServiceEnv(region, service_id, json.dumps(task))
    
    def saveServiceEnvVar(self, tenant_id, service_id, container_port, name, attr_name, attr_value, isChange, scope="outer"):
        tenantServiceEnvVar = {}
        tenantServiceEnvVar["tenant_id"] = tenant_id
        tenantServiceEnvVar["service_id"] = service_id
        tenantServiceEnvVar['container_port'] = container_port
        tenantServiceEnvVar["name"] = name
        tenantServiceEnvVar["attr_name"] = attr_name
        tenantServiceEnvVar["attr_value"] = attr_value
        tenantServiceEnvVar["is_change"] = isChange
        tenantServiceEnvVar["scope"] = scope
        TenantServiceEnvVar(**tenantServiceEnvVar).save()
    
    def addServicePort(self, service, is_init_account, container_port=0, protocol='', port_alias='', is_inner_service=False, is_outer_service=False):
        port = TenantServicesPort(tenant_id=service.tenant_id, service_id=service.service_id, container_port=container_port,
                                  protocol=protocol, port_alias=port_alias, is_inner_service=is_inner_service,
                                  is_outer_service=is_outer_service)
        try:
            env_prefix = port_alias.upper() if bool(port_alias) else service.service_key.upper()
            if is_inner_service:
                mapping_port = self.prepare_mapping_port(service, container_port)
                port.mapping_port = mapping_port
                self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"连接地址", env_prefix + "_HOST", "127.0.0.1", False, scope="outer")
                self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"端口", env_prefix + "_PORT", mapping_port, False, scope="outer")
            if is_init_account:
                password = service.service_id[:8]
                TenantServiceAuth.objects.create(service_id=service.service_id, user="admin", password=password)
                self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"用户名", env_prefix + "_USER", "admin", False, scope="both")
                self.saveServiceEnvVar(service.tenant_id, service.service_id, container_port, u"密码", env_prefix + "_PASS", password, False, scope="both")
            port.save()
        except Exception, e:
            logger.exception(e)
    
    def is_user_click(self, region, service_id):
        is_ok = True
        data = regionClient.getLatestServiceEvent(region, service_id)
        if data.get("event") is not None:
            event = data.get("event")
            if len(event) > 0:
                lastTime = event.get("time")
                curTime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                diffsec = int(curTime) - int(lastTime)
                if event.status == "start" and diffsec <= 180:
                    is_ok = False
        return is_ok
    
    def create_service_mnt(self, tenant_id, service_id, dep_service_alias, region):
        dependS = TenantServiceInfo.objects.get(tenant_id=tenant_id, service_alias=dep_service_alias)
        task = {}
        task["dep_service_id"] = dependS.service_id
        task["tenant_id"] = tenant_id
        task["mnt_name"] = "/mnt/" + dependS.service_alias
        task["mnt_dir"] = dependS.host_path
        regionClient.createServiceMnt(region, service_id, json.dumps(task))
        tsr = TenantServiceMountRelation()
        tsr.tenant_id = tenant_id
        tsr.service_id = service_id
        tsr.dep_service_id = dependS.service_id
        tsr.mnt_name = "/mnt/" + dependS.service_alias
        tsr.mnt_dir = dependS.host_path
        tsr.dep_order = 0
        tsr.save()
    
    def cancel_service_mnt(self, tenant_id, service_id, dep_service_alias, region):
        dependS = TenantServiceInfo.objects.get(tenant_id=tenant_id, service_alias=dep_service_alias)
        task = {}
        task["dep_service_id"] = dependS.service_id
        task["tenant_id"] = tenant_id
        task["mnt_name"] = "v"
        task["mnt_dir"] = "v"
        regionClient.cancelServiceMnt(region, service_id, json.dumps(task))
        TenantServiceMountRelation.objects.get(service_id=service_id, dep_service_id=dependS.service_id).delete()

    def create_service_volume(self, service, volume_path):
        service_type = service.service_type
        region = service.service_region
        tenant_id = service.tenant_id
        service_id = service.service_id
        persistent = TenantServiceVolume(service_id=service_id,
                                         service_type=service_type)
        # 确定host_path
        if (region == "ucloud-bj-1" or region == "ali-sh") and service.service_type == "mysql":
            host_path = "/app-data/tenant/{0}/service/{1}{2}".format(tenant_id, service_id, volume_path)
        else:
            host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant_id, service_id, volume_path)
        persistent.host_path = host_path
        persistent.volume_path = volume_path
        persistent.save()
        # 发送到region进行处理
        res, body = regionClient.createServiceVolume(region, service_id, json.dumps(persistent))
        if res.status == 200:
            return True
        else:
            TenantServiceVolume.objects.filter(pk=persistent.ID).delete()
            return False

    def cancel_service_volume(self, service, volume_id):
        # 发送到region进行删除
        region = service.service_region
        service_id = service.service_id
        try:
            persistent = TenantServiceVolume.objects.get(pk=volume_id)
        except TenantServiceVolume.DoesNotExist:
            return True
        res, body = regionClient.cancelServiceVolume(region, service_id, json.dumps(persistent))
        if res.status == 200:
            TenantServiceVolume.objects.filter(pk=volume_id).delete()
            return True
        else:
            return False


class TenantUsedResource(object):

    def __init__(self):
        self.feerule = settings.REGION_RULE
        self.MODULES = settings.MODULES
    
    def calculate_real_used_resource(self, tenant):
        totalMemory = 0
        tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=True)
        running_data = {}
        for tenant_region in tenant_region_list:
            logger.debug(tenant_region.region_name)
            temp_data = regionClient.getTenantRunningServiceId(tenant_region.region_name, tenant_region.tenant_id)
            logger.debug(temp_data)
            if len(temp_data["data"]) > 0:
                running_data.update(temp_data["data"])
        logger.debug(running_data)
        dsn = BaseConnection()
        query_sql = '''
            select service_id, (s.min_node * s.min_memory) as apply_memory, total_memory  from tenant_service s where s.tenant_id = "{tenant_id}"
            '''.format(tenant_id=tenant.tenant_id)
        sqlobjs = dsn.query(query_sql)
        if sqlobjs is not None and len(sqlobjs) > 0:
            for sqlobj in sqlobjs:
                service_id = sqlobj["service_id"]
                apply_memory = sqlobj["apply_memory"]
                total_memory = sqlobj["total_memory"]
                disk_storage = total_memory - int(apply_memory)
                if disk_storage < 0:
                    disk_storage = 0
                real_memory = running_data.get(service_id)
                if real_memory is not None and real_memory != "":
                    totalMemory = totalMemory + int(apply_memory) + disk_storage
                else:
                    totalMemory = totalMemory + disk_storage
        return totalMemory

    def calculate_guarantee_resource(self, tenant):
        memory = 0
        if tenant.pay_type == "company":
            cur_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            dsn = BaseConnection()
            query_sql = "select region_name,sum(buy_memory) as buy_memory,sum(buy_disk) as buy_disk, sum(buy_net) as buy_net  from tenant_region_pay_model where tenant_id='" + \
                tenant.tenant_id + "' and buy_end_time <='" + cur_time + "' group by region_name"
            sqlobjs = dsn.query(query_sql)
            if sqlobjs is not None and len(sqlobjs) > 0:
                for sqlobj in sqlobjs:
                    memory = memory + int(sqlobj["buy_memory"])
        return memory

    def predict_next_memory(self, tenant, cur_service, newAddMemory, ischeckStatus):
        result = True
        rt_type = "memory"
        if self.MODULES["Memory_Limit"]:
            result = False
            if ischeckStatus:
                newAddMemory = newAddMemory + self.curServiceMemory(cur_service)
            if tenant.pay_type == "free":
                tm = self.calculate_real_used_resource(tenant) + newAddMemory
                logger.debug(tenant.tenant_id + " used memory " + str(tm))
                if tm <= tenant.limit_memory:
                    result = True
            elif tenant.pay_type == "payed":
                tm = self.calculate_real_used_resource(tenant) + newAddMemory
                guarantee_memory = self.calculate_guarantee_resource(tenant)
                logger.debug(tenant.tenant_id + " used memory:" + str(tm) + " guarantee_memory:" + str(guarantee_memory))
                if tm - guarantee_memory <= 102400:
                    ruleJson = self.feerule[cur_service.service_region]
                    unit_money = 0
                    if tenant.pay_level == "personal":
                        unit_money = float(ruleJson['personal_money'])
                    elif tenant.pay_level == "company":
                        unit_money = float(ruleJson['company_money'])
                    total_money = unit_money * (tm * 1.0 / 1024)
                    logger.debug(tenant.tenant_id + " use memory " + str(tm) + " used money " + str(total_money))
                    if tenant.balance >= total_money:
                        result = True
                    else:
                        rt_type = "money"
            elif tenant.pay_type == "unpay":
                result = True
        return rt_type, result
    
    def curServiceMemory(self, cur_service):
        memory = 0
        try:
            body = regionClient.check_service_status(cur_service.service_region, cur_service.service_id)
            status = body[cur_service.service_id]
            if status != "running":
                memory = cur_service.min_node * cur_service.min_memory
        except Exception:
            pass
        return memory


class TenantAccountService(object):
    def __init__(self):
        self.MODULES = settings.MODULES
        
    def isOwnedMoney(self, tenant, region_name):
        if self.MODULES["Owned_Fee"]:
            tenant_region = TenantRegionInfo.objects.get(tenant_id=tenant.tenant_id, region_name=region_name)
            if tenant_region.service_status == 2 and tenant.pay_type == "payed":
                return True
        return False


class TenantRegionService(object):

    def init_for_region(self, region, tenant_name, tenant_id, user):
        success = True
        tenantRegion = TenantRegionInfo.objects.get(tenant_id=tenant_id, region_name=region)
        if not tenantRegion.is_init:
            api = RegionServiceApi()
            logger.info("account.register", "create tenant {0} with tenant_id {1} on region {2}".format(tenant_name, tenant_id, region))
            try:
                res, body = api.create_tenant(region, tenant_name, tenant_id)
            except api.CallApiError, e:
                logger.error("account.register", "create tenant {0} failed".format(tenant_name))
                logger.exception("account.register", e)
                success = False
            if success:
                tenantRegion.is_active = True
                tenantRegion.is_init = True
                tenantRegion.save()
            tenant = Tenants()
            tenant.tenant_id = tenant_id
            tenant.tenant_name = tenant_name
            monitorhook.tenantMonitor(tenant, user, "init_tenant", success)
        return success


class CodeRepositoriesService(object):
    
    def __init__(self):
        self.MODULES = settings.MODULES
    
    def initRepositories(self, tenant, user, service, service_code_from, code_url, code_id, code_version):
        if service_code_from == "gitlab_new":
            if self.MODULES["GitLab_Project"]:
                project_id = 0
                if user.git_user_id > 0:
                    project_id = gitClient.createProject(tenant.tenant_name + "_" + service.service_alias)
                    logger.debug(project_id)
                    monitorhook.gitProjectMonitor(user.nick_name, service, 'create_git_project', project_id)
                    ts = TenantServiceInfo.objects.get(service_id=service.service_id)
                    if project_id > 0:
                        gitClient.addProjectMember(project_id, user.git_user_id, 'master')
                        gitClient.addProjectMember(project_id, 2, 'reporter')
                        ts.git_project_id = project_id
                        ts.git_url = "git@code.goodrain.com:app/" + tenant.tenant_name + "_" + service.service_alias + ".git"
                        gitClient.createWebHook(project_id)
                    ts.code_from = service_code_from
                    ts.code_version = "master"
                    ts.save()
        elif service_code_from == "gitlab_exit" or service_code_from == "gitlab_manual":
            ts = TenantServiceInfo.objects.get(service_id=service.service_id)
            ts.git_project_id = code_id
            ts.git_url = code_url
            ts.code_from = service_code_from
            ts.code_version = code_version
            ts.save()
            self.codeCheck(ts)
        elif service_code_from == "github":
            ts = TenantServiceInfo.objects.get(service_id=service.service_id)
            ts.git_project_id = code_id
            ts.git_url = code_url
            ts.code_from = service_code_from
            ts.code_version = code_version
            ts.save()
            code_user = code_url.split("/")[3]
            code_project_name = code_url.split("/")[4].split(".")[0]
            gitHubClient.createReposHook(code_user, code_project_name, user.github_token)
            self.codeCheck(ts)

    def codeCheck(self, service):
        data = {}
        data["tenant_id"] = service.tenant_id
        data["service_id"] = service.service_id
        data["git_url"] = "--branch " + service.code_version + " --depth 1 " + service.git_url
        
        parsed_git_url = git_url_parse(service.git_url)
        if parsed_git_url.host == "code.goodrain.com" and not settings.MODULES["Git_Code_Manual"]:
            gitUrl = "--branch " + service.code_version + " --depth 1 " + parsed_git_url.url2ssh
        elif parsed_git_url.host == 'github.com':
            createUser = Users.objects.get(user_id=service.creater)
            gitUrl = "--branch " + service.code_version + " --depth 1 " + parsed_git_url.url2https_token(createUser.github_token)
        else:
            gitUrl = "--branch " + service.code_version + " --depth 1 " + service.git_url
        data["git_url"] = gitUrl

        task = {}
        task["tube"] = "code_check"
        task["service_id"] = service.service_id
        task["data"] = data
        logger.debug(json.dumps(task))
        regionClient.writeToRegionBeanstalk(service.service_region, service.service_id, json.dumps(task))
        
    def showGitUrl(self, service):
        httpGitUrl = service.git_url
        if settings.MODULES["Git_Code_Manual"]:
                httpGitUrl = service.git_url
        else:
            if service.code_from == "gitlab_new" or service.code_from == "gitlab_exit":
                cur_git_url = service.git_url.split("/")
                httpGitUrl = "http://code.goodrain.com/app/" + cur_git_url[1]
            elif service.code_from == "gitlab_manual":
                httpGitUrl = service.git_url
        return httpGitUrl
    
    def deleteProject(self, service):
        if self.MODULES["GitLab_Project"]:
            if service.code_from == "gitlab_new" and service.git_project_id > 0:
                gitClient.deleteProject(service.git_project_id)

    def getProjectBranches(self, project_id):
        if self.MODULES["GitLab_Project"]:
            return gitClient.getProjectBranches(project_id)
        return ""
    
    def createUser(self, user, email, password, username, name):
        if self.MODULES["GitLab_User"]:
            if user.git_user_id == 0:
                logger.info("account.login", "user {0} didn't owned a gitlab user_id, will create it".format(user.nick_name))
                git_user_id = gitClient.createUser(email, password, username, name)
                if git_user_id == 0:
                    logger.info("account.gituser", "create gitlab user for {0} failed, reason: got uid 0".format(user.nick_name))
                else:
                    user.git_user_id = git_user_id
                    user.save()
                    logger.info("account.gituser", "user {0} set git_user_id = {1}".format(user.nick_name, git_user_id))
                monitorhook.gitUserMonitor(user, git_user_id)
    
    def modifyUser(self, user, password):
        if self.MODULES["GitLab_User"]:
            gitClient.modifyUser(user.git_user_id, password=password)
        
    def addProjectMember(self, git_project_id, git_user_id, level):
        if self.MODULES["GitLab_Project"]:
            gitClient.addProjectMember(git_project_id, git_user_id, level)
        
    def listProjectMembers(self, git_project_id):
        if self.MODULES["GitLab_Project"]:
            return gitClient.listProjectMembers(git_project_id)
        return ""
    
    def deleteProjectMember(self, project_id, git_user_id):
        if self.MODULES["GitLab_Project"]:
            gitClient.deleteProjectMember(project_id, git_user_id)
        
    def addProjectMember(self, project_id, git_user_id, gitlab_identity):
        if self.MODULES["GitLab_Project"]:
            gitClient.addProjectMember(project_id, git_user_id, gitlab_identity)
    
    def editMemberIdentity(self, project_id, git_user_id, gitlab_identity):
        if self.MODULES["GitLab_Project"]:
            gitClient.editMemberIdentity(project_id, git_user_id, gitlab_identity)

    def get_gitHub_access_token(self, code):
        if self.MODULES["Git_Hub"]:
            return gitHubClient.get_access_token(code)
        return ""
    
    def getgGitHubAllRepos(self, token):
        if self.MODULES["Git_Hub"]:
            return gitHubClient.getAllRepos(token)
        return ""
    
    def gitHub_authorize_url(self, user):
        if self.MODULES["Git_Hub"]:
            return gitHubClient.authorize_url(user.pk)
        return ""
    
    def gitHub_ReposRefs(self, user, repos, token):
        if self.MODULES["Git_Hub"]:
            return gitHubClient.getReposRefs(user, repos, token)
        return ""
