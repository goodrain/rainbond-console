# -*- coding: utf8 -*-
import logging
from datetime import datetime

# service
from console.services.app_config import env_var_service
# repository
from console.repositories.app_config import port_repo
# model
from www.models.main import TenantServicesPort
from www.models.main import TenantServiceEnvVar
from www.models.main import TenantServiceVolume
from console.models.main import ComponentGraph
from www.models.main import TenantServiceConfigurationFile
# exception
from console.exception.main import EnvAlreadyExist, InvalidEnvName
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
        self.volume_deps = []
        self.app_config_groups = []
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
        self._ensure_port_envs()

    def _ensure_port_envs(self):
        # filter out the old port envs
        envs = [env for env in self.envs if env.container_port != 0]
        # create outer envs for every port
        for port in self.ports:
            envs.extend(self._create_envs_4_ports(port))
        self.envs = envs

    def _create_envs_4_ports(self, port: TenantServicesPort):
        port_alias = self.component.service_alias.upper()
        host_env = self._create_port_env(port, "连接地址", port_alias + "_HOST", "127.0.0.1")
        port_env = self._create_port_env(port, "端口", port_alias + "_PORT", str(port.container_port))
        return [host_env, port_env]

    def _create_port_env(self, port: TenantServicesPort, name, attr_name, attr_value):
        return TenantServiceEnvVar(
            tenant_id=self.component.tenant_id,
            service_id=self.component.component_id,
            container_port=port.container_port,
            name=name,
            attr_name=attr_name,
            attr_value=attr_value,
            is_change=False,
            scope="outer",
            create_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )

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
        for port in add:
            # Optimization: do not update port data iteratively
            self._update_port_data(port)
            self.ports.append(TenantServicesPort(**port))

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
