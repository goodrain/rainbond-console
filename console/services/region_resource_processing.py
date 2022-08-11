import datetime

from console.enum.app import GovernanceModeEnum
from console.models.main import AutoscalerRuleMetrics, ComponentK8sAttributes, K8sResource
from console.repositories.app_config import env_var_repo, volume_repo, port_repo
from console.repositories.autoscaler_repo import autoscaler_rules_repo
from console.repositories.group import group_repo, group_service_relation_repo
from console.repositories.k8s_attribute import k8s_attribute_repo
from console.repositories.k8s_resources import k8s_resources_repo
from console.repositories.region_app import region_app_repo
from console.services.app_actions import app_manage_service
from console.services.perm_services import role_kind_services
from console.services.team_services import team_services
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants, ServiceGroup, TenantServiceInfo, TenantRegionInfo, TenantServiceVolume, \
    TenantServiceEnvVar, TenantServicesPort, ServiceProbe

region_api = RegionInvokeApi()


class RegionResource(object):
    def get_namespaces(self, eid, region_id, content):
        res, body = region_api.list_namespaces(eid, region_id, content)
        return body

    def get_namespaces_resource(self, eid, region_id, content, namespace):
        res, body = region_api.list_namespace_resources(eid, region_id, content, namespace)
        return body

    def convert_resource(self, eid, region_id, namespace, content):
        res, body = region_api.list_convert_resource(eid, region_id, namespace, content)
        return body

    def create_tenant(self, tenant, enterprise_id, namespace, user_id, region_name):
        if Tenants.objects.filter(tenant_alias=tenant["Namespace"], enterprise_id=enterprise_id).exists():
            return
        expire_time = datetime.datetime.now() + datetime.timedelta(days=7)
        params = {
            "tenant_name": tenant["Name"],
            "pay_type": "payed",
            "pay_level": "company",
            "creater": user_id,
            "expired_time": expire_time,
            "tenant_alias": tenant["Namespace"],
            "enterprise_id": enterprise_id,
            "limit_memory": tenant["LimitMemory"],
            "namespace": namespace,
            "tenant_id": tenant["UUID"]
        }
        t = Tenants.objects.create(**params)
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        TenantRegionInfo.objects.create(
            tenant_id=tenant["UUID"],
            region_name=region_name,
            is_active=True,
            is_init=True,
            service_status=True,
            create_time=now,
            update_time=now,
            region_tenant_name=tenant["Name"],
            region_tenant_id=tenant["UUID"],
            region_scope="private",
            enterprise_id=enterprise_id,
        ).save()
        role_kind_services.init_default_roles(kind="team", kind_id=t.tenant_id)
        team_services.add_user_role_to_team(tenant=t, user_ids=[user_id], role_ids=[])
        return t

    def create_app(self, tenant, apps, region, user):
        if apps:
            for app in apps:
                application = ServiceGroup(
                    tenant_id=tenant.tenant_id,
                    region_name=region.region_name,
                    group_name=app["app"]["app_name"],
                    note="",
                    is_default=False,
                    username="",
                    update_time=datetime.datetime.now(),
                    create_time=datetime.datetime.now(),
                    app_type="rainbond",
                    app_store_name="",
                    app_store_url="",
                    app_template_name="",
                    governance_mode=GovernanceModeEnum.KUBERNETES_NATIVE_SERVICE.name,
                    version="",
                    logo="",
                    k8s_app=app["app"]["app_name"],
                )
                group_repo.create(application)
                da = {
                    "region_name": region.region_name,
                    "region_app_id": app["app"]["app_id"],
                    "app_id": application.ID,
                }
                region_app_repo.create(**da)
                if app["k8s_resources"]:
                    self.create_k8s_resources(app["k8s_resources"], application.ID)
                components = app["component"]
                service_ids = self.create_components(application, components, tenant, region.region_name, user.user_id)
                app_manage_service.batch_action(region.region_name, tenant, user, "deploy", service_ids, None, None)

    def create_k8s_resources(self, k8s_resources, app_id):
        app_k8s_resource_list = list()
        if not k8s_resources:
            return
        for k8s_resource in k8s_resources:
            app_k8s_resource_list.append(
                K8sResource(
                    app_id=app_id,
                    name=k8s_resource["name"],
                    kind=k8s_resource["kind"],
                    content=k8s_resource["content"],
                    state=k8s_resource["state"],
                    error_overview=k8s_resource["error_overview"]))
        k8s_resources_repo.bulk_create(app_k8s_resource_list)

    def create_components(self, application, components, tenant, region_name, user_id):
        if not components:
            return []
        service_ids = list()
        for component in components:
            new_service = TenantServiceInfo()
            new_service.cmd = component["cmd"]
            new_service.service_region = region_name
            new_service.service_key = "0000"
            new_service.desc = "docker run application"
            new_service.category = "app_publish"
            new_service.setting = ""
            new_service.extend_method = component["ts"]["extend_method"]
            new_service.env = ""
            new_service.min_node = component["ts"]["replicas"]
            new_service.min_memory = component["ts"]["container_memory"]
            new_service.min_cpu = component["ts"]["container_cpu"]
            new_service.inner_port = 0
            new_service.image = component["image"]
            version = component["image"].split(":")[1] if len(component["image"].split(":")) > 1 else "latest"
            new_service.version = version
            new_service.namespace = "goodrain"
            new_service.update_version = 1
            new_service.port_type = "multi_outer"
            new_service.create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            new_service.deploy_version = ""
            new_service.git_project_id = 0
            new_service.service_type = "application"
            new_service.total_memory = 0
            new_service.volume_mount_path = ""
            new_service.host_path = ""
            new_service.code_from = "image_manual"
            new_service.language = ""
            new_service.create_status = "complete"
            new_service.tenant_id = tenant.tenant_id
            new_service.service_cname = component["ts"]["k8s_component_name"]
            new_service.service_source = "docker_image"
            new_service.service_id = component["ts"]["service_id"]
            new_service.service_alias = component["ts"]["service_alias"]
            new_service.creater = user_id
            new_service.build_upgrade = False
            new_service.host_path = "/grdata/tenant/" + tenant.tenant_id + "/service/" + component["ts"]["service_id"]
            new_service.docker_cmd = ""
            new_service.k8s_component_name = component["ts"]["k8s_component_name"]
            new_service.job_strategy = component["ts"]["job_strategy"]
            new_service.save()
            group_service_relation_repo.add_service_group_relation(application.ID, component["ts"]["service_id"],
                                                                   tenant.tenant_id, region_name)
            self.create_component_env(component["env"], tenant.tenant_id, new_service)
            self.create_component_config(component["config"], tenant.tenant_id, new_service)
            self.create_component_port(component["port"], tenant.tenant_id, new_service)
            self.create_component_telescopic(component["telescopic"], new_service)
            self.create_healthy_check(component["healthy_check"], new_service)
            self.create_component_special(component["component_k8s_attributes"], tenant.tenant_id, new_service)
            service_ids.append(new_service.service_id)
        return service_ids

    def create_component_env(self, envs, tenant_id, service):
        if not envs:
            return
        env_data = list()
        for env in envs:
            tenantServiceEnvVar = TenantServiceEnvVar(
                tenant_id=tenant_id,
                service_id=service.service_id,
                container_port=0,
                name=env["env_explain"],
                attr_name=env["env_key"],
                attr_value=env["env_value"],
                is_change=1,
                scope="inner")
            env_data.append(tenantServiceEnvVar)
        if len(env_data) > 0:
            env_var_repo.bulk_create_component_env(env_data)

    def create_component_config(self, configs, tenant_id, service):
        if not configs:
            return
        for config in configs:
            host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant_id, service.service_id, config["config_path"])
            volume_data = TenantServiceVolume(
                service_id=service.service_id,
                category="app_publish",
                host_path=host_path,
                volume_type="config-file",
                volume_path=config["config_path"],
                volume_name=config["config_name"],
                mode=config["mode"],
                volume_capacity=0,
                volume_provider_name="",
                access_mode="RWX",
                share_policy="exclusive",
                backup_policy="exclusive",
                reclaim_policy="exclusive",
                allow_expansion=0,
            )
            volume_data.save()
            file_data = {
                "service_id": service.service_id,
                "volume_id": volume_data.ID,
                "file_content": config["config_value"],
                "volume_name": volume_data.volume_name
            }
            volume_repo.add_service_config_file(**file_data)

    def create_component_port(self, ports, tenant_id, service):
        if not ports:
            return
        port_data = list()
        for port in ports:
            service_port = TenantServicesPort(
                tenant_id=tenant_id,
                service_id=service.service_id,
                container_port=port["port"],
                mapping_port=port["port"],
                protocol=port["protocol"],
                port_alias=service.service_alias.upper().replace("-", "_") + str(port["port"]),
                is_inner_service=False,
                is_outer_service=False,
                k8s_service_name=service.service_alias + "-" + str(port["port"]))
            port_data.append(service_port)
        if len(port_data):
            port_repo.bulk_create(port_data)

    def create_component_telescopic(self, telescopic, service):
        if not telescopic["enable"]:
            return
        autoscaler_rule = {
            "rule_id": telescopic["rule_id"],
            "service_id": service.service_id,
            "xpa_type": "hpa",
            "enable": True,
            "min_replicas": telescopic["min_replicas"],
            "max_replicas": telescopic["max_replicas"],
        }
        autoscaler_rules_repo.create(**autoscaler_rule)
        metrics = list()
        if telescopic["cpu_or_memory"]:
            for metric in telescopic["cpu_or_memory"]:
                metrics.append(
                    AutoscalerRuleMetrics(
                        rule_id=telescopic["rule_id"],
                        metric_type=metric["MetricsType"],
                        metric_name=metric["MetricsName"],
                        metric_target_type=metric["MetricTargetType"],
                        metric_target_value=metric["MetricTargetValue"],
                    ))
        if len(metrics):
            AutoscalerRuleMetrics.objects.bulk_create(metrics)

    def create_healthy_check(self, healthy_check, service):
        if not healthy_check["status"]:
            return
        ServiceProbe(
            service_id=service.service_id,
            probe_id=healthy_check["probe_id"],
            mode=healthy_check["mode"],
            scheme=healthy_check["detection_method"],
            path=healthy_check["path"],
            port=healthy_check["port"],
            cmd=healthy_check["cmd"],
            http_header=healthy_check["http_header"],
            initial_delay_second=healthy_check["initial_delay_second"],
            period_second=healthy_check["period_second"],
            timeout_second=healthy_check["timeout_second"],
            success_threshold=healthy_check["success_threshold"],
            failure_threshold=healthy_check["failure_threshold"],
            is_used=1).save()

    def create_component_special(self, specials, tenant_id, service):
        componentK8sAttributes = list()
        if not specials:
            return
        for special in specials:
            componentK8sAttributes.append(
                ComponentK8sAttributes(
                    tenant_id=tenant_id,
                    component_id=service.service_id,
                    name=special["name"],
                    save_type=special["save_type"],
                    attribute_value=special["attribute_value"]))
        k8s_attribute_repo.bulk_create(componentK8sAttributes)

    def resource_import(self, eid, region_id, namespace, content):
        res, body = region_api.resource_import(eid, region_id, namespace, content)
        return body


region_resource = RegionResource()
