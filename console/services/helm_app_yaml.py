import datetime
import json
import logging
import time

from console.models.main import RainbondCenterApp, RainbondCenterAppVersion, AppHelmOverrides
from console.repositories.helm import helm_repo
from console.services.app_actions import app_manage_service
from console.services.region_resource_processing import region_resource
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import RegionApp
from www.utils.crypt import make_helm_uuid, make_uuid

region_api = RegionInvokeApi()
logger = logging.getLogger('default')


class HelmAppService(object):
    def check_helm_app(self, name, repo_name, chart_name, version, overrides, region, tenant_name, tenant):
        data = helm_repo.get_helm_repo_by_name(repo_name)
        if not data:
            data = dict()
        data["name"] = name
        data["chart"] = repo_name + "/" + chart_name
        data["version"] = version
        data["overrides"] = overrides
        data["namespace"] = tenant.namespace
        res, body = region_api.check_helm_app(region, tenant_name, data)
        return res, body["bean"]

    def create_helm_center_app(self, **kwargs):
        logger.info("begin create_helm_center_app")
        return RainbondCenterApp(**kwargs).save()

    def generate_template(self, cvdata, app_model, version, tenant, chart, region_name, enterprise_id, user_id, overrides,
                          app_id):
        app_template = {}
        app_template["template_version"] = "v2"
        app_template["group_key"] = app_model.app_id
        app_template["group_name"] = app_model.app_name
        app_template["group_version"] = version
        app_template["group_dev_status"] = ""
        app_template["governance_mode"] = "KUBERNETES_NATIVE_SERVICE"
        app_template["k8s_resources"] = cvdata["kubernetes_resources"]
        apps = list()
        convert_resource = cvdata["convert_resource"] if cvdata["convert_resource"] else []
        for cv in convert_resource:
            app = dict()
            app["service_cname"] = cv["components_name"]
            app["tenant_id"] = tenant.tenant_id
            service_id = make_helm_uuid(chart + "/" + cv["components_name"])
            app["service_id"] = service_id
            app["service_key"] = service_id
            app["service_share_uuid"] = make_helm_uuid(chart + "/" + cv["components_name"]) + "+" + make_helm_uuid(
                chart + "/" + cv["components_name"])
            app["need_share"] = True
            app["category"] = "app_publish"
            app["language"] = ""
            if cv["basic_management"]["resource_type"] == "Deployment":
                app["extend_method"] = "stateless_multiple"
            if cv["basic_management"]["resource_type"] == "Job":
                app["extend_method"] = "job"
            if cv["basic_management"]["resource_type"] == "StatefulSet":
                app["extend_method"] = "state_multiple"
            if cv["basic_management"]["resource_type"] == "CronJob":
                app["extend_method"] = "cronjob"
            app["version"] = cv["basic_management"]["image"].split(":")[1]
            memory = cv["basic_management"]["memory"]
            app["memory"] = memory
            app["service_type"] = "application"
            app["service_source"] = "docker_image"
            now = datetime.datetime.now()
            app["deploy_version"] = now.strftime("%Y%m%d%H%M%S")
            app["image"] = cv["basic_management"]["image"]
            app["share_image"] = cv["basic_management"]["image"]
            app["share_type"] = ["image"]
            service_alias = "gr" + service_id[-6:]
            app["service_alias"] = service_alias
            app["service_name"] = ""
            app["service_region"] = region_name
            app["creater"] = 1
            app["cmd"] = cv["basic_management"]["command"]
            app["probes"] = []
            if cv["health_check_management"] and cv["health_check_management"]["port"] != 0:
                probes = dict()
                probes["port"] = cv["health_check_management"]["port"]
                probes["mode"] = cv["health_check_management"]["mode"]
                probes["scheme"] = cv["health_check_management"]["detection_method"]
                probes["path"] = cv["health_check_management"]["path"]
                probes["cmd"] = cv["health_check_management"]["cmd"]
                probes["http_header"] = cv["health_check_management"]["http_header"]
                second = cv["health_check_management"]
                probes["initial_delay_second"] = second["initial_delay_second"] if second["initial_delay_second"] else 1
                probes["period_second"] = second["period_second"] if second["period_second"] else 10
                probes["timeout_second"] = second["timeout_second"] if second["timeout_second"] else 1
                probes["failure_threshold"] = second["failure_threshold"] if second["failure_threshold"] else 3
                probes["success_threshold"] = second["success_threshold"] if second["success_threshold"] else 1
                probes["is_used"] = True
                probes["service_id"] = service_id
                app["probes"] = [probes]

            app["extend_method_map"] = {
                "step_node": 1,
                "min_memory": 64,
                "init_memory": 512,
                "max_memory": 65536,
                "step_memory": 64,
                "is_restart": 0,
                "min_node": 1,
                "container_cpu": 0,
                "max_node": 64
            }
            app["extend_method_map"]["min_node"] = 1
            app["port_map_list"] = []
            if cv["port_management"]:
                for port in cv["port_management"]:
                    port_management = {
                        "name": port["name"],
                        "protocol": port["protocol"],
                        "tenant_id": tenant.tenant_id,
                        "port_alias": service_alias.upper() + str(port["port"]),
                        "container_port": port["port"],
                        "is_inner_service": False,
                        "is_outer_service": False,
                        "k8s_service_name": service_alias
                    }
                    if port["protocol"] == "http":
                        port_management["is_outer_service"] = True
                    app["port_map_list"].append(port_management)

            app["service_volume_map_list"] = []
            if cv["config_management"]:
                for config in cv["config_management"]:
                    config_management = {
                        "file_content": config["config_value"],
                        "category": "app_publish",
                        "volume_capacity": 0,
                        "volume_provider_name": "",
                        "volume_type": "config-file",
                        "volume_path": config["config_path"],
                        "volume_name": config["config_name"],
                        "access_mode": "RWX",
                        "share_policy": "exclusive",
                        "backup_policy": "exclusive",
                        "mode": config["mode"]
                    }
                    app["service_volume_map_list"].append(config_management)

            app["service_env_map_list"] = []
            if cv["env_management"]:
                for env in cv["env_management"]:
                    env_management = {
                        "name": env["env_explain"],
                        "attr_name": env["env_key"],
                        "attr_value": env["env_value"],
                        "is_change": True
                    }
                    app["service_env_map_list"].append(env_management)

            app["service_connect_info_map_list"] = []

            app["service_related_plugin_config"] = []

            app["component_monitors"] = None
            app["component_graphs"] = None

            app["labels"] = []

            app["component_k8s_attributes"] = []
            if cv["component_k8s_attributes_management"]:
                for attributes in cv["component_k8s_attributes_management"]:
                    component_k8s_attributes_management = {
                        "create_time": "",
                        "update_time": "",
                        "tenant_id": tenant.tenant_id,
                        "component_id": service_id,
                        "name": attributes["name"],
                        "save_type": attributes["save_type"],
                        "attribute_value": attributes["attribute_value"]
                    }
                    app["component_k8s_attributes"].append(component_k8s_attributes_management)

            app["dep_service_map_list"] = []
            app["mnt_relation_list"] = []
            app["service_image"] = {"hub_url": None, "hub_user": None, "hub_password": None, "namespace": None}
            apps.append(app)
        app_template["apps"] = apps
        template = json.dumps(app_template)
        overrides = json.dumps(overrides)
        app_overrides = AppHelmOverrides(app_id=app_id, app_model_id=app_model.app_id, overrides=overrides)
        app_overrides.save()
        app_version = RainbondCenterAppVersion(
            app_id=app_model.app_id,
            version=version,
            app_version_info=app_model.details,
            version_alias="",
            template_type="",
            record_id=0,
            share_user=user_id,
            share_team=tenant.tenant_name,
            # group_id=share_record.group_id,
            source="local",
            scope=app_model.scope,
            app_template=template,
            template_version="v2",
            enterprise_id=enterprise_id,
            upgrade_time=time.time())
        app_version.region_name = region_name
        app_version.save()

    def yaml_conversion(self, name, repo_name, chart_name, version, overrides, region, tenant_name, tenant, eid, region_id):
        check_helm_app_data = helm_repo.get_helm_repo_by_name(repo_name)
        if not check_helm_app_data:
            check_helm_app_data = dict()
        check_helm_app_data["name"] = name
        check_helm_app_data["chart"] = repo_name + "/" + chart_name
        check_helm_app_data["version"] = version
        check_helm_app_data["overrides"] = overrides
        check_helm_app_data["namespace"] = tenant.namespace
        _, check_body = region_api.check_helm_app(region, tenant_name, check_helm_app_data)
        body = self.yaml_handle(eid, region_id, tenant, check_body["bean"]["yaml"])
        return body

    def yaml_handle(self, eid, region_id, tenant, yaml):
        logger.info("begin yaml_handle")
        yaml_resource_detailed_data = {
            "event_id": "",
            "region_app_id": "",
            "tenant_id": tenant.tenant_id,
            "namespace": tenant.namespace,
            "yaml": yaml
        }
        _, body = region_api.yaml_resource_detailed(eid, region_id, yaml_resource_detailed_data)
        return body["bean"]

    def add_helm_repo(self, repo_name, repo_url, username, password):
        helm_repo_data = {
            "repo_id": make_uuid(),
            "repo_name": repo_name,
            "repo_url": repo_url,
            "username": username,
            "password": password
        }
        return helm_repo.create_helm_repo(**helm_repo_data)

    def get_helm_chart_information(self, region, tenant_name, repo_url, chart_name):
        repo_chart = dict()
        repo_chart["repo_url"] = repo_url
        repo_chart["chart_name"] = chart_name
        _, body = region_api.get_chart_information(region, tenant_name, repo_chart)
        return body["bean"]

    def get_command_install_yaml(self, region, tenant_name, command):
        _, body = region_api.command_helm_yaml(region, tenant_name, {"command": command})
        return body["bean"]

    def tgz_yaml_handle(self, eid, region, tenant, app_id, user, data):
        app = RegionApp.objects.filter(app_id=app_id)
        if app:
            app = app[0]
            data = {
                "event_id": "",
                "region_app_id": app.region_app_id,
                "tenant_id": tenant.tenant_id,
                "namespace": tenant.namespace,
                "yaml": data.get("yaml", "")
            }
            _, body = region_api.yaml_resource_import(eid, region.region_id, data)
            ac = body["bean"]
            region_resource.create_k8s_resources(ac["k8s_resources"], app_id)
            service_ids = region_resource.create_components(app, ac["component"], tenant, region.region_name, user.user_id,
                                                            "yaml")
            app_manage_service.batch_action(region.region_name, tenant, user, "deploy", service_ids, None, None)

    def repo_yaml_handle(self, eid, region_id, command, region_name, tenant, data, user_id):
        logger.info("begin function repo_yaml_handle")
        cmd_list = command.split()
        repo_name, repo_url, username, password, chart_name, version = "", "", "", "", "", ""
        overrides = list()
        logger.info("parse the helm command")
        for i in range(len(cmd_list)):
            if cmd_list[i] == "--repo" and i + 1 != len(cmd_list):
                repo_url = cmd_list[i + 1]
                repo_name = repo_url.split("/")[-1]
                if repo_name == "" or len(repo_name) > 32:
                    repo_name = "rainbond"
            if cmd_list[i] == "--username" and i + 1 != len(cmd_list):
                username = cmd_list[i + 1]
            if cmd_list[i] == "--version" and i + 1 != len(cmd_list):
                version = cmd_list[i + 1]
            if cmd_list[i] == "--password" and i + 1 != len(cmd_list):
                password = cmd_list[i + 1]
            if cmd_list[i] == "--set" and i + 1 != len(cmd_list):
                overrides.append(cmd_list[i + 1])
            if not cmd_list[i].startswith('-') and i + 1 != len(cmd_list):
                if not cmd_list[i + 1].startswith('-'):
                    chart_name = cmd_list[i + 1]
        overrides = [{override.split("=")[0]: override.split("=")[1]} for override in overrides]
        if not repo_name:
            return None
        chart_data = self.get_helm_chart_information(region_name, tenant.tenant_name, repo_url, chart_name)
        if not version:
            logger.warning("version is not obtained from the command.use the highest version of {}".format(chart_name))
            version = chart_data[0]["Version"]
        i = 0
        repo_name = repo_name + "cmd"
        while True:
            i = i + 1
            repo_name = repo_name + str(i)
            repo = helm_repo.get_helm_repo_by_name(repo_name)
            if not repo:
                logger.info("create helm repo {}".format(repo_name))
                self.add_helm_repo(repo_name, repo_url, username, password)
                break
            else:
                if repo["repo_url"] == repo_url:
                    logger.info("helm repo {} is exist and url is the same".format(repo_name))
                    break

        return {
            "version": version,
            "repo_name": repo_name,
            "repo_url": repo_url,
            "username": username,
            "password": password,
            "chart_name": chart_name,
            "eid": eid,
            "overrides": overrides
        }

    def openapi_yaml_handle(self, eid, region_id, tenant, app, namespace, yaml):
        yaml_resource_detailed_data = {
            "event_id": "",
            "region_app_id": app.region_app_id,
            "tenant_id": tenant.tenant_id,
            "namespace": namespace,
            "yaml": yaml
        }
        _, body = region_api.yaml_resource_import(eid, region_id, yaml_resource_detailed_data)
        return body["bean"]


helm_app_service = HelmAppService()
