import datetime
import json
import logging
import re
import time

from console.exception.main import AbortRequest
from console.models.main import RainbondCenterApp, RainbondCenterAppVersion, AppHelmOverrides
from console.repositories.helm import helm_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid3, make_uuid

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
        res, body = region_api.get_cluster_nodes_arch(region_name)
        chaos_arch = list(set(body.get("list")))
        arch = chaos_arch[0] if chaos_arch else "amd64"
        app_template = {}
        app_template["template_version"] = "v2"
        app_template["group_key"] = app_model.app_id
        app_template["group_name"] = app_model.app_name
        app_template["group_version"] = version
        app_template["group_dev_status"] = ""
        app_template["governance_mode"] = "KUBERNETES_NATIVE_SERVICE"
        app_template["k8s_resources"] = cvdata["kubernetes_resources"]
        app_template["arch"] = arch
        apps = list()
        convert_resource = cvdata["convert_resource"] if cvdata["convert_resource"] else []
        for cv in convert_resource:
            app = dict()
            app["service_cname"] = cv["components_name"]
            app["tenant_id"] = tenant.tenant_id
            service_id = make_uuid3(chart + "/" + cv["components_name"])
            app["service_id"] = service_id
            app["service_key"] = service_id
            app["service_share_uuid"] = make_uuid3(chart + "/" + cv["components_name"]) + "+" + make_uuid3(
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
            app_image = cv["basic_management"]["image"].split(":")
            app["version"] = app_image[1] if len(app_image) > 2 else "latest"
            memory = cv["basic_management"]["memory"]
            app["memory"] = memory
            app["service_type"] = "application"
            app["service_source"] = "docker_image"
            now = datetime.datetime.now()
            app["deploy_version"] = now.strftime("%Y%m%d%H%M%S")
            app["image"] = cv["basic_management"]["image"]
            app["arch"] = arch
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
                    if port["protocol"] in ["http", "tcp"]:
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

    def parse_cmd_add_repo(self,command):

        repo_add_pattern = r'^helm\s+repo\s+add\s+(?P<repo_name>\S+)\s+(?P<repo_url>\S+)(?:\s+--username\s+' \
                           r'(?P<username>\S+))?(?:\s+--password\s+(?P<password>\S+))?$'
        repo_add_match = re.match(repo_add_pattern, command)
        if not repo_add_match:
            raise AbortRequest("helm repo is exist", "命令解析错误，请重新输入", status_code=400, error_code=400)
        repo_name = repo_add_match.group('repo_name')
        repo_url = repo_add_match.group('repo_url')
        username = repo_add_match.group('username') if repo_add_match.group('username') else ""
        password = repo_add_match.group('password') if repo_add_match.group('password') else ""
        repo = helm_repo.get_helm_repo_by_name(repo_name)
        if not repo:
            logger.info("create helm repo {}".format(repo_name))
            self.add_helm_repo(repo_name, repo_url, username, password)
            return repo_name,repo_url,username,password,True
        else:
            # 有一种情况，仓库名被占用了，但是url不同。
            repo = helm_repo.get_helm_repo_by_url(repo_url)
            if repo:
                return repo_name,repo_url,username,password,False
            else:
                raise AbortRequest("helm repo is exist", "仓库名称已被占用，请更改仓库名称", status_code=409, error_code=409)

    def parse_helm_command(self, command, region_name, tenant):
        result = dict()
        repo_add_pattern = r'^helm\s+repo\s+add\s+(?P<repo_name>\S+)\s+(?P<repo_url>\S+)(?:\s+--username\s+' \
                           r'(?P<username>\S+))?(?:\s+--password\s+(?P<password>\S+))?$'
        repo_add_match = re.match(repo_add_pattern, command)
        if repo_add_match:
            result['command'] = 'repo_add'
            repo_name = repo_add_match.group('repo_name')
            repo_url = repo_add_match.group('repo_url')
            username = repo_add_match.group('username') if repo_add_match.group('username') else ""
            password = repo_add_match.group('password') if repo_add_match.group('password') else ""
            repo = helm_repo.get_helm_repo_by_name(repo_name)
            if not repo:
                logger.info("create helm repo {}".format(repo_name))
                self.add_helm_repo(repo_name, repo_url, username, password)
            else:
                raise AbortRequest("helm repo is exist", "仓库名称已存在", status_code=404, error_code=404)
            result["repo_name"] = repo_name
            result["repo_url"] = repo_url
            result["username"] = username
            result["password"] = password
            return result

        install_pattern = r'^helm\s+install\s+(?P<release_name>\S+)\s+(?P<chart>\S+)(?:\s+-n\s+(?P<namespace>\S+))' \
                          r'?(?:(?:\s+--version\s+(?P<version>\S+))?(?P<set_values>(?:\s+--set\s+[^-].*)*))?'
        set_pattern = r'--set\s+([^=]+)=([^ \s]+)'

        install_match = re.match(install_pattern, command)
        if install_match:
            result['command'] = 'install'
            release_name = install_match.group('release_name')
            version = install_match.group('version')
            chart = install_match.group('chart')
            namespace = install_match.group('namespace')
            if namespace:
                raise AbortRequest("can not set namespace", "团队下不支持设置命名空间", status_code=404, error_code=404)
            result['overrides'] = list()
            set_values_str = install_match.group('set_values')
            if set_values_str:
                set_values = re.findall(set_pattern, set_values_str)
                for key, value in set_values:
                    result['overrides'].append({key.strip(): value.strip()})
            repo_chart = chart.split("/")
            if len(repo_chart) == 2:
                repo_name = chart.split("/")[0]
                chart_name = chart.split("/")[1]
            else:
                raise AbortRequest(
                    "repo_name/chart_name incorrect format", "格式不正确，仓库名称和应用名称之间应用 '/' 划分", status_code=404, error_code=404)
            repo = helm_repo.get_helm_repo_by_name(repo_name)
            if not repo:
                raise AbortRequest("helm repo is not exist", "商店不存在，执行 helm repo add 进行添加", status_code=404, error_code=404)
            repo_url = repo.get("repo_url")
            chart_data = self.get_helm_chart_information(region_name, tenant.tenant_name, repo_url, chart_name)
            if not version:
                logger.warning("version is not obtained from the command.use the highest version of {}".format(chart_name))
                version = chart_data[0]["Version"]
            result["release_name"] = release_name
            result["chart"] = chart
            result["version"] = version
            result["repo_name"] = repo_name
            result["repo_url"] = repo_url
            result["chart_name"] = chart_name
            return result
        raise AbortRequest("helm command command mismatch", "命令解析失败，请检查命令", status_code=404, error_code=404)


helm_app_service = HelmAppService()
