# -*- coding: utf8 -*-
import logging
import json
from datetime import datetime

# service
from console.services.app_config import port_service
from console.services.app_config import volume_service
from console.services.app_config import probe_service
from console.services.app_config.promql_service import promql_service
from console.services.app_config import env_var_service
# repository
from console.repositories.app_config import port_repo
# model
from www.models.main import TenantServiceInfo
from www.models.main import TenantServicesPort
from www.models.main import TenantServiceEnvVar
from www.models.main import TenantServiceVolume
from www.models.main import ServiceGroupRelation
from console.models.main import ServiceSourceInfo
from console.models.main import ServiceMonitor
from console.models.main import ComponentGraph
from www.models.service_publish import ServiceExtendMethod
from www.models.main import TenantServiceConfigurationFile
# exception
from console.exception.main import AbortRequest
from console.exception.bcode import ErrK8sServiceNameExists
from console.exception.main import ErrVolumePath
from console.exception.main import EnvAlreadyExist, InvalidEnvName
# enum
from console.enum.component_enum import ComponentType
from console.constants import AppConstants
# util
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class Component(object):
    def __init__(self,
                 component,
                 component_source,
                 envs,
                 ports,
                 volumes,
                 config_files,
                 probe,
                 extend_info,
                 monitors,
                 graphs,
                 service_group_rel=None):
        self.component = component
        self.component_source = component_source
        self.envs = list(envs)
        self.ports = list(ports)
        self.volumes = list(volumes)
        self.config_files = list(config_files)
        self.probe = probe
        self.extend_info = extend_info
        self.monitors = list(monitors)
        self.graphs = list(graphs)
        self.component_deps = []
        self.service_group_rel = service_group_rel

    def set_changes(self, changes):
        """
        Set changes to the component
        """
        update_funcs = self._create_update_funcs()
        for key in update_funcs:
            if not changes.get(key):
                continue
            update_func = update_funcs[key]
            update_func(changes.get(key))

    def _create_update_funcs(self):
        return {
            "deploy_version": self._update_deploy_version,
            "app_version": self._update_version,
            # "image": self.dummy_func,  # TODO(huangrh)
            "envs": self._update_inner_envs,
            "connect_infos": self._update_outer_envs,
            "ports": self._update_ports,
            "volumes": self._update_volumes,
            "probe": self._update_probe,
            # TODO(huangrh)
            # "dep_services": self._update_dep_services,
            # "dep_volumes": self._update_dep_volumes,
            # "plugins": self._update_plugins,
            "component_graphs": self._update_component_graphs,
            "component_monitors": self._update_component_monitors,
        }

    def _update_deploy_version(self, dv):
        if not dv["is_change"]:
            return
        self.component.deploy_version = dv["new"]

    def _update_version(self, v):
        if not v["is_change"]:
            return
        self.component.version = v["new"]

    def _update_inner_envs(self, envs):
        self._update_envs(envs, "inner")

    def _update_outer_envs(self, envs):
        self._update_envs(envs, "outer")

    def _update_envs(self, envs, scope):
        if envs is None:
            return
        # create envs
        add = envs.get("add", [])
        for env in add:
            container_port = env.get("container_port", 0)
            value = env.get("attr_value", "")
            name = env.get("name", "")
            attr_name = env.get("attr_name", "")
            if not attr_name:
                continue
            if container_port == 0 and value == "**None**":
                value = self.component.service_id[:8]
            try:
                env_var_service.check_env(self.component, attr_name, value)
            except (EnvAlreadyExist, InvalidEnvName) as e:
                logger.warning("failed to create env: {}; will ignore this env".format(e))
                continue
            self.envs.append(
                TenantServiceEnvVar(
                    tenant_id=self.component.tenant_id,
                    service_id=self.component.service_id,
                    container_port=container_port,
                    name=name,
                    attr_name=attr_name,
                    attr_value=value,
                    scope=scope,
                ))

    def _update_ports(self, ports):
        if ports is None:
            return

        add = ports.get("add", [])
        envs = {"add": []}
        for port in add:
            # Optimization: do not update port data iteratively
            self._update_port_data(port)
            self.ports.append(TenantServicesPort(**port))
            if not port["is_inner_service"]:
                continue
            # TODO(huangrh): envs for port
            envs["add"].extend(self._create_envs_4_ports(port))
        # TODO(huangrh): can't update port

    def _create_envs_4_ports(self, port):
        container_port = int(port["container_port"])
        port_alias = self.component.service_alias.upper()
        host_env = {
            "name": "连接地址",
            "attr_name": port_alias + str(port["container_port"]) + "_HOST",
            # TODO(huangrh): attr_value can be k8s_service_name
            "attr_value": "127.0.0.1",
            "is_change": False,
        }
        port_env = {
            "name": "端口",
            "attr_name": port_alias + str(port["container_port"]) + "_PORT",
            "attr_value": container_port,
            "is_change": False,
        }
        return [host_env, port_env]

    def _update_component_graphs(self, component_graphs):
        if not component_graphs:
            return
        graphs = component_graphs.get("add", [])
        self.graphs = [ComponentGraph(**graph) for graph in graphs]

    def _update_component_monitors(self, component_monitors):
        if not component_monitors:
            return
        monitors = component_monitors.get("add", [])
        self.monitors = [ComponentGraph(**monitor) for monitor in monitors]

    def _update_port_data(self, port):
        container_port = int(port["container_port"])
        port_alias = self.component.service_alias.upper()
        k8s_service_name = port.get("k8s_service_name", self.component.service_alias + "-" + str(container_port))
        if k8s_service_name:
            try:
                port_repo.get_by_k8s_service_name(self.component.tenant_id, k8s_service_name)
                k8s_service_name += "-" + make_uuid()[-4:]
            except TenantServicesPort.DoesNotExist:
                pass
            port["k8s_service_name"] = k8s_service_name
        port["tenant_id"] = self.component.tenant_id
        port["service_id"] = self.component.service_id
        port["mapping_port"] = container_port
        port["port_alias"] = port_alias

    def _update_volumes(self, volumes):
        for volume in volumes.get("add"):
            volume["service_id"] = self.component.service_id
            host_path = "/grdata/tenant/{0}/service/{1}{2}".format(self.component.tenant_id, self.component.service_id,
                                                                   volume["volume_path"])
            volume["host_path"] = host_path
            file_content = volume.get("file_content")
            if file_content:
                self.config_files.append(
                    TenantServiceConfigurationFile(
                        service_id=self.component.component_id,
                        volume_name=volume["volume_name"],
                        file_content=file_content,
                    ))
            if "file_content" in volume.keys():
                volume.pop("file_content")
            self.volumes.append(TenantServiceVolume(**volume))

    def _update_probe(self, probe):
        add = probe.get("add")
        if add:
            add["probe_id"] = make_uuid()
            self.probe = TenantServicesPort(**add)
        upd = probe.get("upd", None)
        if upd:
            probe = TenantServicesPort(**upd)
            probe.ID = self.probe.ID
            probe.tenant_id = self.probe.tenant_id
            probe.service_id = self.probe.service_id


class NewComponents(object):
    def __init__(self,
                 tenant,
                 region_name,
                 user,
                 original_app,
                 app_model_key,
                 app_template,
                 version,
                 install_from_cloud,
                 components_keys,
                 market_name=""):
        """
        components_keys: component keys that the user select.
        """
        self.tenant = tenant
        self.region_name = region_name
        self.user = user
        self.original_app = original_app
        # TODO(huangrh): merge app_model_key, app_template, version, install_from_cloud and market_name
        self.app_model_key = app_model_key
        self.app_template = app_template
        self.version = version
        self.install_from_cloud = install_from_cloud
        self.market_name = market_name

        self.components_keys = components_keys
        self.components = self.create_components()

    def create_components(self):
        """
        create component and related attributes
        """
        # new component templates
        exist_components = {cpt.component.service_key: cpt.component for cpt in self.original_app.components()}
        templates = self.app_template.get("apps")
        templates = templates if templates else []
        templates = [ct for ct in templates if not exist_components.get(ct.get("service_key"))]

        components = [self._template_to_component(self.tenant.tenant_id, template) for template in templates]
        if self.components_keys:
            components = [cpt for cpt in components if cpt.service_key in self.components_keys]

        # make a map of templates
        templates = {tmpl.get("service_key"): tmpl for tmpl in templates}

        result = []
        for cpt in components:
            component_tmpl = templates.get(cpt.service_key)

            # component source
            component_source = self._template_to_component_source(cpt, component_tmpl)
            # envs
            inner_envs = component_tmpl.get("service_env_map_list")
            outer_envs = component_tmpl.get("service_connect_info_map_list")
            envs = self._template_to_envs(cpt, inner_envs, outer_envs)
            # ports
            ports = self._template_to_ports(cpt, component_tmpl.get("port_map_list"))
            # volumes
            volumes, config_files = self._template_to_volumes(cpt, component_tmpl.get("service_volume_map_list"))
            # probe
            probes = self._template_to_probes(cpt, component_tmpl.get("probes"))
            probe = None
            if probes:
                probe = probes[0]
            # extend info
            extend_info = self._template_to_extend_info(cpt, component_tmpl.get("extend_method_map"))
            # service monitors
            monitors = self._template_to_service_monitors(cpt, component_tmpl.get("component_monitors"))
            # graphs
            graphs = self._template_to_component_graphs(cpt, component_tmpl.get("component_graphs"))
            service_group_rel = ServiceGroupRelation(
                service_id=cpt.component_id,
                group_id=self.original_app.app_id,
                tenant_id=self.tenant.tenant_id,
                region_name=self.region_name,
            )
            result.append(
                Component(cpt, component_source, envs, ports, volumes, config_files, probe, extend_info, monitors, graphs,
                          service_group_rel))
        return result

    def _template_to_component(self, tenant_id, template):
        component = TenantServiceInfo()
        component.tenant_id = tenant_id
        component.service_id = make_uuid()
        component.service_cname = template.get("service_cname", "default-name")
        component.service_alias = "gr" + component.service_id[-6:]
        component.creater = self.user.pk
        component.image = template.get("share_image", template["image"])
        component.cmd = template.get("cmd", "")
        component.service_region = self.region_name
        component.service_key = template.get("service_key")
        component.desc = "install from market app"
        component.category = "app_publish"
        component.min_cpu = component.calculate_min_cpu(component.min_memory)
        component.version = template.get("version")
        component.create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        component.deploy_version = template.get("deploy_version")
        component.service_type = "application"
        component.total_memory = component.min_node * component.min_memory
        component.service_source = AppConstants.MARKET
        component.create_status = "complete"
        component.tenant_service_group_id = self.original_app.upgrade_group_id

        # component type
        extend_method = template["extend_method"]
        if extend_method:
            if extend_method == "state":
                component.extend_method = ComponentType.state_multiple.value
            elif extend_method == "stateless":
                component.extend_method = ComponentType.stateless_multiple.value
            else:
                component.extend_method = extend_method

        component.min_node = template.get("extend_method_map", {}).get("min_node")
        if template.get("extend_method_map", {}).get("init_memory"):
            component.min_memory = template.get("extend_method_map", {}).get("init_memory")
        elif template.get("extend_method_map", {}).get("min_memory"):
            component.min_memory = template.get("extend_method_map", {}).get("min_memory")
        else:
            component.min_memory = 512

        return component

    def _template_to_component_source(self, component: TenantServiceInfo, tmpl: map):
        extend_info = tmpl.get("service_image")
        extend_info["source_deploy_version"] = tmpl.get("deploy_version")
        extend_info["source_service_share_uuid"] = tmpl.get("service_share_uuid") if tmpl.get(
            "service_share_uuid", None) else tmpl.get("service_key", "")
        if "update_time" in tmpl:
            if type(tmpl["update_time"]) == datetime:
                extend_info["update_time"] = tmpl["update_time"].strftime('%Y-%m-%d %H:%M:%S')
            elif type(tmpl["update_time"]) == str:
                extend_info["update_time"] = tmpl["update_time"]
        if self.install_from_cloud:
            extend_info["install_from_cloud"] = True
            extend_info["market"] = "default"
            extend_info["market_name"] = self.market_name
        return ServiceSourceInfo(
            team_id=component.tenant_id,
            service_id=component.service_id,
            extend_info=json.dumps(extend_info),
            group_key=self.app_model_key,
            version=self.version,
            service_share_uuid=tmpl.get("service_share_uuid")
            if tmpl.get("service_share_uuid", None) else tmpl.get("service_key"),
        )

    def _template_to_envs(self, component, inner_envs, outer_envs):
        if not inner_envs and not outer_envs:
            return []
        envs = []
        for env in inner_envs:
            if not env.get("attr_name"):
                continue
            envs.append(
                TenantServiceEnvVar(
                    tenant_id=component.tenant_id,
                    service_id=component.service_id,
                    container_port=0,
                    name=env.get("name"),
                    attr_name=env.get("attr_name"),
                    attr_value=env.get("attr_value"),
                    is_change=env.get("is_change", True),
                    scope="inner"))
        for env in outer_envs:
            if not env.get("attr_name"):
                continue
            container_port = env.get("container_port", 0)
            if env.get("attr_value") == "**None**":
                env["attr_value"] = make_uuid()[:8]
            envs.append(
                TenantServiceEnvVar(
                    tenant_id=component.tenant_id,
                    service_id=component.service_id,
                    container_port=container_port,
                    name=env.get("name"),
                    attr_name=env.get("attr_name"),
                    attr_value=env.get("attr_value"),
                    is_change=env.get("is_change", True),
                    scope="outer"))
        # port envs
        return envs

    def _template_to_ports(self, component, ports):
        if not ports:
            return []
        result = []
        for port in ports:
            component_port = port["container_port"]
            k8s_service_name = port.get("k8s_service_name") if port.get(
                "k8s_service_name") else component.service_alias + "-" + str(component_port)
            try:
                port_service.check_k8s_service_name(component.tenant_id, k8s_service_name)
            except ErrK8sServiceNameExists:
                k8s_service_name = k8s_service_name + "-" + make_uuid()[:4]
            except AbortRequest:
                k8s_service_name = component.service_alias + "-" + str(component_port)
            port = TenantServicesPort(
                tenant_id=component.tenant_id,
                service_id=component.service_id,
                container_port=int(component_port),
                mapping_port=int(component_port),
                lb_mapping_port=0,
                protocol=port.get("protocol", "tcp"),
                port_alias=port.get("port_alias", ""),
                is_inner_service=port.get("is_inner_service", False),
                is_outer_service=port.get("is_outer_service", False),
                k8s_service_name=k8s_service_name,
            )
            # TODO(huangrh): create default rule
            # if port.get("is_outer_service", False):
            #     domain_service.create_default_gateway_rule(tenant, region, service, t_port)
            result.append(port)
        return result

    def _template_to_volumes(self, component, volumes):
        if not volumes:
            return [], []
        volumes2 = []
        config_files = []
        for volume in volumes:
            try:
                if volume["volume_type"] == "config-file" and volume["file_content"] != "":
                    settings = None
                    config_file = TenantServiceConfigurationFile(
                        service_id=component.component_id,
                        volume_name=volume["volume_name"],
                        file_content=volume["file_content"])
                    config_files.append(config_file)
                else:
                    settings = volume_service.get_best_suitable_volume_settings(self.tenant, component, volume["volume_type"],
                                                                                volume.get("access_mode"),
                                                                                volume.get("share_policy"),
                                                                                volume.get("backup_policy"), None,
                                                                                volume.get("volume_provider_name"))
                    if settings["changed"]:
                        logger.debug('volume type changed from {0} to {1}'.format(volume["volume_type"],
                                                                                  settings["volume_type"]))
                        volume["volume_type"] = settings["volume_type"]
                        if volume["volume_type"] == "share-file":
                            volume["volume_capacity"] = 0
                    else:
                        settings["volume_capacity"] = volume.get("volume_capacity", 0)

                volumes2.append(
                    volume_service.create_service_volume(self.tenant, component, volume["volume_path"], volume["volume_type"],
                                                         volume["volume_name"], settings))
            except ErrVolumePath:
                logger.warning("Volume {0} Path {1} error".format(volume["volume_name"], volume["volume_path"]))
        return volumes2, config_files

    def _template_to_probes(self, component, probes):
        if not probes:
            return []
        result = []
        for probe in probes:
            result.append(probe_service.create_probe(self.tenant, component, probe))

    def _template_to_extend_info(self, component, extend_info):
        if not extend_info:
            return None
        version = component.version
        if len(version) > 255:
            version = version[:255]
        return ServiceExtendMethod(
            service_key=component.service_key,
            app_version=version,
            min_node=extend_info["min_node"],
            max_node=extend_info["max_node"],
            step_node=extend_info["step_node"],
            min_memory=extend_info["min_memory"],
            max_memory=extend_info["max_memory"],
            step_memory=extend_info["step_memory"],
            is_restart=extend_info["is_restart"])

    def _template_to_service_monitors(self, component, service_monitors):
        if not service_monitors:
            return []
        monitors = []
        for monitor in service_monitors:
            # Optimization: check all monitor names at once
            if ServiceMonitor.objects.filter(tenant_id=component.tenant_id, name=monitor["name"]).count() > 0:
                monitor["name"] = "-".join([monitor["name"], make_uuid()[-4:]])
            data = ServiceMonitor(
                name=monitor["name"],
                tenant_id=component.tenant_id,
                service_id=component.service_id,
                path=monitor["path"],
                port=monitor["port"],
                service_show_name=monitor["service_show_name"],
                interval=monitor["interval"])
            monitors.append(data)
        return monitors

    def _template_to_component_graphs(self, component, graphs):
        if not graphs:
            return []
        result = []
        for graph in graphs:
            try:
                promql = promql_service.add_or_update_label(component.service_id, graph.get("promql"))
            except AbortRequest as e:
                logger.warning("promql: {}, {}".format(graph.get("promql"), e))
                continue

            result.append(
                ComponentGraph(
                    component_id=component.service_id,
                    graph_id=make_uuid(),
                    title=graph.get("title"),
                    promql=promql,
                    sequence=graph.get("sequence"),
                ))
        return result
