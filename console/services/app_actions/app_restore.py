import json
import logging

from console.repositories.app import service_repo
from console.repositories.app import service_source_repo
from console.repositories.app_config import dep_relation_repo
from console.repositories.app_config import env_var_repo
from console.repositories.app_config import port_repo
from console.repositories.app_config import volume_repo
from console.repositories.probe_repo import probe_repo
from www.models.main import TenantServiceEnvVar
from www.models.main import TenantServiceRelation
from www.models.main import TenantServicesPort

logger = logging.getLogger("default")


class AppRestore(object):

    def __init__(self, tenant, service):
        self.tenant = tenant
        self.service = service

    def svc(self, service_base):
        service_repo.del_by_sid(self.service.service_id)
        service_base.pop("ID")
        service_repo.create(service_base)

    def svc_source(self, service_source):
        service_source_repo.delete_service_source(self.tenant.tenant_id, self.service.service_id)
        if not service_source:
            return
        service_source["service_id"] = service_source["service"]
        service_source.pop("ID")
        service_source.pop("service")
        logger.debug("service_source: {}".format(json.dumps(service_source)))
        service_source_repo.create_service_source(**service_source)

    def envs(self, service_env_vars):
        env_var_repo.delete_service_env(self.tenant.tenant_id, self.service.service_id)
        if service_env_vars:
            envs = []
            for item in service_env_vars:
                item.pop("ID")
                envs.append(TenantServiceEnvVar(**item))
            env_var_repo.bulk_create(envs)

    def ports(self, service_ports):
        port_repo.delete_service_port(self.tenant.tenant_id, self.service.service_id)
        if service_ports:
            ports = []
            for item in service_ports:
                item.pop("ID")
                ports.append(TenantServicesPort(**item))
            port_repo.bulk_create(ports)

    def volumes(self, service_volumes, service_config_file):
        volume_repo.delete_service_volumes(self.service.service_id)
        volume_repo.delete_config_files(self.service.service_id)
        id_cfg = {item["volume_id"]: item for item in service_config_file}
        for item in service_volumes:
            item.pop("ID")
            v = volume_repo.add_service_volume(**item)
            if v.volume_type != "config-file":
                continue
            cfg = id_cfg.get(item.ID, None)
            if cfg is None:
                continue
            cfg["volume_id"] = v.ID
            cfg.pop("ID")
            _ = volume_repo.add_service_config_file(**cfg)

    def probe(self, probe):
        probe_repo.delete_service_probe(self.service.service_id)
        if not probe:
            return
        probe.pop("ID")
        probe_repo.add_service_probe(**probe)

    def dep_services(self, service_relation):
        dep_relation_repo.delete_service_relation(self.tenant.tenant_id, self.service.service_id)
        if not service_relation:
            return
        relations = []
        for relation in service_relation:
            relation.pop("ID")
            new_service_relation = TenantServiceRelation(**relation)
            relations.append(new_service_relation)
        TenantServiceRelation.objects.bulk_create(relations)

    def dep_volumes(self):
        # TODO
        pass
