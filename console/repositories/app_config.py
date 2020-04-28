# -*- coding: utf8 -*-
"""
  Created on 18/1/12.
"""
import datetime
import logging

from django.db.models import Q

from console.exception.main import AbortRequest
from console.utils.shortcuts import get_object_or_404
from www.db.base import BaseConnection
from www.models.main import GatewayCustomConfiguration
from www.models.main import ImageServiceRelation
from www.models.main import ServiceAttachInfo
from www.models.main import ServiceCreateStep
from www.models.main import ServiceDomain
from www.models.main import ServiceDomainCertificate
from www.models.main import ServicePaymentNotify
from www.models.main import ServiceTcpDomain
from www.models.main import TenantServiceAuth
from www.models.main import TenantServiceConfigurationFile
from www.models.main import TenantServiceEnv
from www.models.main import TenantServiceEnvVar
from www.models.main import TenantServiceMountRelation
from www.models.main import TenantServiceRelation
from www.models.main import TenantServicesPort
from www.models.main import TenantServiceVolume
from www.models.main import ThirdPartyServiceEndpoints
from www.models.service_publish import ServiceExtendMethod

logger = logging.getLogger("default")


class TenantServiceEnvVarRepository(object):
    def get_service_env(self, tenant_id, service_id):
        return TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id)

    def get_service_env_by_scope(self, tenant_id, service_id, scope):
        return TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, scope=scope).all()

    def get_by_attr_name_and_scope(self, tenant_id, service_id, attr_name, scope):
        envs = TenantServiceEnvVar.objects.filter(
            tenant_id=tenant_id, service_id=service_id, attr_name=attr_name, scope=scope)
        if envs:
            return envs[0]
        return None

    def get_service_env_by_attr_name(self, tenant_id, service_id, attr_name):
        envs = TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, attr_name=attr_name)
        if envs:
            return envs[0]
        return None

    def get_service_env_or_404_by_env_id(self, tenant_id, service_id, env_id):
        return get_object_or_404(
            TenantServiceEnvVar,
            msg="Environment variable with ID {} not found".format(env_id),
            msg_show=u"环境变量`{}`不存在".format(env_id),
            tenant_id=tenant_id,
            service_id=service_id,
            ID=env_id)

    def get_env_by_ids_and_attr_names(self, tenant_id, service_ids, attr_names):
        envs = TenantServiceEnvVar.objects.filter(
            tenant_id=tenant_id, service_id__in=service_ids, attr_name__in=attr_names)
        return envs

    def get_env_by_ids_and_env_id(self, tenant_id, service_id, env_id):
        envs = TenantServiceEnvVar.objects.get(tenant_id=tenant_id, service_id=service_id, ID=env_id)
        return envs

    def get_service_env_by_port(self, tenant_id, service_id, port):
        return TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, container_port=port)

    def add_service_env(self, **tenant_service_env_var):
        env = TenantServiceEnvVar.objects.create(**tenant_service_env_var)
        return env

    def delete_service_env(self, tenant_id, service_id):
        TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id).delete()

    def delete_service_build_env(self, tenant_id, service_id):
        TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, scope="build").delete()

    def delete_service_env_by_attr_name(self, tenant_id, service_id, attr_name):
        TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id, attr_name=attr_name).delete()

    def delete_service_env_by_pk(self, pk):
        TenantServiceEnvVar.objects.filter(pk=pk).delete()

    def delete_service_env_by_port(self, tenant_id, service_id, container_port):
        TenantServiceEnvVar.objects.filter(tenant_id=tenant_id, service_id=service_id,
                                           container_port=container_port).delete()

    def update_env_var(self, tenant_id, service_id, attr_name, **update_params):
        TenantServiceEnvVar.objects.filter(
            tenant_id=tenant_id, service_id=service_id, attr_name=attr_name).update(**update_params)

    def get_build_envs(self, tenant_id, service_id):
        envs = {}
        default_envs = Q(attr_name__in=("COMPILE_ENV", "NO_CACHE", "DEBUG", "PROXY", "SBT_EXTRAS_OPTS"))
        prefix_start_env = Q(attr_name__startswith="BUILD_")
        build_start_env = Q(scope="build")
        buildEnvs = self.get_service_env(
            tenant_id, service_id).filter(
            default_envs | prefix_start_env | build_start_env)
        for benv in buildEnvs:
            attr_name = benv.attr_name
            if attr_name.startswith("BUILD_"):
                attr_name = attr_name.replace("BUILD_", "", 1)
            envs[attr_name] = benv.attr_value
        compile_env = compile_env_repo.get_service_compile_env(service_id)
        if compile_env:
            envs["PROC_ENV"] = compile_env.user_dependency
        return envs

    def change_service_env_scope(self, env, scope):
        """变更环境变量范围"""
        scope = self._check_service_env_scope(scope)
        env.scope = scope
        env.save()

    @staticmethod
    def _check_service_env_scope(scope):
        try:
            return TenantServiceEnvVar.ScopeType(scope).value
        except ValueError:
            raise AbortRequest(msg="the value of scope is outer or inner")

    def bulk_create(self, envs):
        TenantServiceEnvVar.objects.bulk_create(envs)


class TenantServicePortRepository(object):
    def list_inner_ports(self, tenant_id, service_id):
        return TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id, is_inner_service=True)

    def get_service_ports(self, tenant_id, service_id):
        return TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id)

    def get_service_port_by_port(self, tenant_id, service_id, container_port):
        ports = TenantServicesPort.objects.filter(
            tenant_id=tenant_id, service_id=service_id, container_port=container_port)
        if ports:
            return ports[0]
        return None

    def add_service_port(self, **tenant_service_port):
        service_port = TenantServicesPort.objects.create(**tenant_service_port)
        return service_port

    def delete_service_port(self, tenant_id, service_id):
        TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id).delete()

    def delete_serivce_port_by_port(self, tenant_id, service_id, container_port):
        TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id,
                                          container_port=container_port).delete()

    def delete_service_port_by_pk(self, pk):
        TenantServicesPort.objects.filter(pk=pk).delete()

    def get_service_port_by_alias(self, service_id, alias):
        return TenantServicesPort.objects.filter(service_id=service_id, port_alias=alias)

    def update_port(self, tenant_id, service_id, container_port, **update_params):
        TenantServicesPort.objects.filter(
            tenant_id=tenant_id, service_id=service_id, container_port=container_port).update(**update_params)

    def get_http_opend_services_ports(self, tenant_id, service_ids):
        return TenantServicesPort.objects.filter(
            tenant_id=tenant_id, service_id__in=service_ids, is_outer_service=True, protocol__in=("http", "https"))

    def get_tcp_outer_opend_ports(self, service_ids):
        return TenantServicesPort.objects.filter(
            service_id__in=service_ids, is_outer_service=True).exclude(protocol__in=("http", "https"))

    def get_service_port_by_lb_mapping_port(self, service_id, lb_mapping_port):
        return TenantServicesPort.objects.filter(service_id=service_id, lb_mapping_port=lb_mapping_port).first()

    def bulk_create(self, ports):
        TenantServicesPort.objects.bulk_create(ports)

    def update(self, **param):
        TenantServicesPort.objects.filter(
            tenant_id=param["tenant_id"], service_id=param["service_id"],
            container_port=param["container_port"]).update(**param)


class TenantServiceVolumnRepository(object):
    def get_multi_service_volumes(self, service_ids):
        return TenantServiceVolume.objects.filter(service_id__in=service_ids).exclude(volume_type="config-file")

    def get_service_volumes_with_config_file(self, service_id):
        return TenantServiceVolume.objects.filter(service_id=service_id)

    def get_service_volumes(self, service_id):
        return TenantServiceVolume.objects.filter(service_id=service_id).exclude(volume_type="config-file")

    def get_service_volumes_about_config_file(self, service_id):
        return TenantServiceVolume.objects.filter(service_id=service_id, volume_type="config-file")

    def get_service_volume_by_name(self, service_id, volume_name):
        volumes = TenantServiceVolume.objects.filter(service_id=service_id, volume_name=volume_name)
        if volumes:
            return volumes[0]
        return None

    def get_service_volume_by_path(self, service_id, volume_path):
        volumes = TenantServiceVolume.objects.filter(service_id=service_id, volume_path=volume_path)
        if volumes:
            return volumes[0]
        return None

    def get_service_volume_by_pk(self, volume_id):
        try:
            return TenantServiceVolume.objects.get(pk=volume_id)
        except TenantServiceVolume.DoesNotExist:
            return None

    def add_service_volume(self, **tenant_service_volume):
        return TenantServiceVolume.objects.create(**tenant_service_volume)

    def delete_volume_by_id(self, volume_id):
        TenantServiceVolume.objects.filter(ID=volume_id).delete()

    def delete_file_by_volume_id(self, volume_id):
        TenantServiceConfigurationFile.objects.filter(volume_id=volume_id).delete()

    def add_service_config_file(self, **service_config_file):
        return TenantServiceConfigurationFile.objects.create(**service_config_file)

    def get_service_config_files(self, service_id):
        return TenantServiceConfigurationFile.objects.filter(service_id=service_id)

    def get_service_config_file(self, volume_id):
        return TenantServiceConfigurationFile.objects.filter(volume_id=volume_id).first()

    def get_services_volumes(self, service_ids):
        return TenantServiceVolume.objects.filter(service_id__in=service_ids)

    def delete_service_volumes(self, service_id):
        TenantServiceVolume.objects.filter(service_id=service_id).delete()

    def get_by_sid_name(self, service_id, volume_name):
        return TenantServiceVolume.objects.filter(service_id=service_id, volume_name=volume_name).first()

    def delete_config_files(self, sid):
        TenantServiceConfigurationFile.objects.filter(service_id=sid).defer()


class TenantServiceRelationRepository(object):
    def get_service_dependencies(self, tenant_id, service_id):
        return TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id)

    def get_depency_by_serivce_id_and_dep_service_id(self, tenant_id, service_id, dep_service_id):
        deps = TenantServiceRelation.objects.filter(
            tenant_id=tenant_id, service_id=service_id, dep_service_id=dep_service_id)
        if deps:
            return deps[0]
        return None

    def add_service_dependency(self, **tenant_service_relation):
        return TenantServiceRelation.objects.create(**tenant_service_relation)

    def get_dependency_by_dep_service_ids(self, tenant_id, service_id, dep_service_ids):
        return TenantServiceRelation.objects.filter(
            tenant_id=tenant_id, service_id=service_id, dep_service_id__in=dep_service_ids)

    def get_dependency_by_dep_id(self, tenant_id, dep_service_id):
        tsr = TenantServiceRelation.objects.filter(tenant_id=tenant_id, dep_service_id=dep_service_id)
        return tsr

    def delete_service_relation(self, tenant_id, service_id):
        TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id).delete()

    def get_services_dep_current_service(self, tenant_id, dep_service_id):
        return TenantServiceRelation.objects.filter(tenant_id=tenant_id, dep_service_id=dep_service_id)

    def check_db_dep_by_eid(self, eid):
        """
        check if there is a database installed from the market that is dependent on
        """
        conn = BaseConnection()
        sql = """
            SELECT
                a.service_id, a.dep_service_id
            FROM
                tenant_service_relation a,
                tenant_service b,
                tenant_info c,
                tenant_service d
            WHERE
                b.tenant_id = c.tenant_id
                AND c.enterprise_id = "{eid}"
                AND a.service_id = d.service_id
                AND a.dep_service_id = b.service_id
                AND ( b.image LIKE "%mysql%" OR b.image LIKE "%postgres%" OR b.image LIKE "%mariadb%" )
                AND (b.service_source <> "market" OR d.service_source <> "market")
                limit 1""".format(eid=eid)
        result = conn.query(sql)
        if len(result) > 0:
            return True
        sql2 = """
            SELECT
                a.dep_service_id
            FROM
                tenant_service_relation a,
                tenant_service b,
                tenant_info c,
                tenant_service d,
                service_source e,
                service_source f
            WHERE
                b.tenant_id = c.tenant_id
                AND c.enterprise_id = "{eid}"
                AND a.service_id = d.service_id
                AND a.dep_service_id = b.service_id
                AND ( b.image LIKE "%mysql%" OR b.image LIKE "%postgres%" OR b.image LIKE "%mariadb%" )
                AND ( b.service_source = "market" AND d.service_source = "market" )
                AND e.service_id = b.service_id
                AND f.service_id = d.service_id
                AND e.group_key <> f.group_key
                LIMIT 1""".format(eid=eid)
        result2 = conn.query(sql2)
        return True if len(result2) > 0 else False


class TenantServiceMntRelationRepository(object):
    def get_mnt_by_dep_id_and_mntname(self, dep_service_id, mnt_name):
        return TenantServiceMountRelation.objects.filter(dep_service_id=dep_service_id, mnt_name=mnt_name)

    def get_service_mnts(self, tenant_id, service_id):
        volume_types = ['share-file', 'memoryfs', 'local']
        dep_mnts = []
        real_dep_mnts = self.get_service_mnts_filter_volume_type(
            tenant_id=tenant_id, service_id=service_id, volume_types=volume_types)
        if real_dep_mnts:
            volume_names = [mnt.get("volume_name") for mnt in real_dep_mnts]
            dep_mnts = TenantServiceMountRelation.objects.filter(
                tenant_id=tenant_id, service_id=service_id, mnt_name__in=volume_names)
        return dep_mnts

    def get_by_dep_service_id(self, tenant_id, dep_service_id):
        return TenantServiceMountRelation.objects.filter(tenant_id=tenant_id, dep_service_id=dep_service_id)

    def get_service_mnts_filter_volume_type(self, tenant_id, service_id, volume_types=None):
        query = "mnt.tenant_id = %s and mnt.service_id = %s"
        if volume_types:
            query += " and volume.volume_type in ({})".format(','.join(['%s'] * len(volume_types)))

        sql = """
        select *
        from tenant_service_mnt_relation as mnt
                 inner join tenant_service_volume as volume
                            on mnt.dep_service_id = volume.service_id and mnt.mnt_name = volume.volume_name
        where {};
        """.format(query)

        params = [tenant_id, service_id] + (volume_types or [])

        return list(TenantServiceMountRelation.objects.raw(sql, params=params))

    def list_mnt_relations_by_service_ids(self, tenant_id, service_ids):
        dep_mnts = TenantServiceMountRelation.objects.filter(tenant_id=tenant_id, service_id__in=service_ids)

        return dep_mnts

    def add_service_mnt_relation(self, tenant_id, service_id, dep_service_id, mnt_name, mnt_dir):
        tsr = TenantServiceMountRelation.objects.create(
            tenant_id=tenant_id,
            service_id=service_id,
            dep_service_id=dep_service_id,
            mnt_name=mnt_name,
            mnt_dir=mnt_dir  # this dir is source app's volume path
        )
        return tsr

    def delete_mnt_relation(self, service_id, dep_service_id, mnt_name):
        TenantServiceMountRelation.objects.filter(
            service_id=service_id, dep_service_id=dep_service_id, mnt_name=mnt_name).delete()

    def get_mount_current_service(self, tenant_id, service_id):
        """查询挂载当前组件的信息"""
        return TenantServiceMountRelation.objects.filter(tenant_id=tenant_id, dep_service_id=service_id)

    def delete_mnt(self, service_id):
        TenantServiceMountRelation.objects.filter(service_id=service_id).delete()

    def bulk_create(self, mnts):
        TenantServiceMountRelation.objects.bulk_create(mnts)


class ImageServiceRelationRepository(object):
    def create_image_service_relation(self, tenant_id, service_id, image_url, service_cname):
        isr = ImageServiceRelation.objects.create(
            tenant_id=tenant_id, service_id=service_id, image_url=image_url, service_cname=service_cname)
        return isr

    def get_image_service_relation(self, tenant_id, service_id):
        isrs = ImageServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id)
        if isrs:
            return isrs[0]
        return None


class ServiceDomainRepository(object):
    def get_service_domain_by_container_port(self, service_id, container_port):
        return ServiceDomain.objects.filter(service_id=service_id, container_port=container_port)

    def get_service_domain_by_container_port_and_protocol(self, service_id, container_port, protocol):
        return ServiceDomain.objects.filter(service_id=service_id, container_port=container_port, protocol=protocol)

    def get_service_domain_by_http_rule_id(self, http_rule_id):
        domain = ServiceDomain.objects.filter(http_rule_id=http_rule_id).first()
        if domain:
            return domain
        else:
            return None

    def get_domain_by_domain_name(self, domain_name):
        domains = ServiceDomain.objects.filter(domain_name=domain_name)
        if domains:
            return domains[0]
        return None

    def get_domains_by_service_ids(self, service_ids):
        return ServiceDomain.objects.filter(service_id__in=service_ids)

    def get_domain_by_id(self, domain_id):
        domains = ServiceDomain.objects.filter(ID=domain_id)
        if domains:
            return domains[0]
        return None

    def get_domain_by_domain_name_or_service_alias_or_group_name(self, search_conditions):
        domains = ServiceDomain.objects.filter(
            Q(domain_name__contains=search_conditions)
            | Q(service_alias__contains=search_conditions)
            | Q(group_name__contains=search_conditions)).order_by("-type")
        return domains

    def get_all_domain(self):
        return ServiceDomain.objects.all()

    def get_all_domain_count_by_tenant_and_region_id(self, tenant_id, region_id):
        return ServiceDomain.objects.filter(tenant_id=tenant_id, region_id=region_id).count()

    def get_domain_by_name_and_port(self, service_id, container_port, domain_name):
        try:
            return ServiceDomain.objects.filter(
                service_id=service_id, container_port=container_port, domain_name=domain_name).all()
        except ServiceDomain.DoesNotExist:
            return None

    def get_domain_by_name_and_port_and_protocol(
            self, service_id, container_port, domain_name, protocol, domain_path=None):
        if domain_path:
            try:
                return ServiceDomain.objects.get(
                    service_id=service_id,
                    container_port=container_port,
                    domain_name=domain_name,
                    protocol=protocol,
                    domain_path=domain_path)
            except ServiceDomain.DoesNotExist:
                return None
        else:
            try:
                return ServiceDomain.objects.get(
                    service_id=service_id, container_port=container_port, domain_name=domain_name, protocol=protocol)
            except ServiceDomain.DoesNotExist:
                return None

    def get_domain_by_name_and_path(self, domain_name, domain_path):
        if domain_path:
            return ServiceDomain.objects.filter(domain_name=domain_name, domain_path=domain_path).all()
        else:
            return None

    def get_domain_by_name_and_path_and_protocol(self, domain_name, domain_path, protocol):
        if domain_path:
            return ServiceDomain.objects.filter(
                domain_name=domain_name, domain_path=domain_path, protocol=protocol).all()
        else:
            return None

    def delete_service_domain_by_port(self, service_id, container_port):
        ServiceDomain.objects.filter(service_id=service_id, container_port=container_port).delete()

    def delete_service_domain(self, service_id):
        ServiceDomain.objects.filter(service_id=service_id).delete()

    def delete_service_domain_by_id(self, domain_id):
        ServiceDomain.objects.filter(ID=domain_id).delete()

    def get_tenant_certificate(self, tenant_id):
        return ServiceDomainCertificate.objects.filter(tenant_id=tenant_id)

    def get_tenant_certificate_page(self, tenant_id, start, end):
        """提供指定位置和数量的数据"""
        cert = ServiceDomainCertificate.objects.filter(tenant_id=tenant_id)
        nums = cert.count()  # 证书数量
        # if end > nums - 1:
        #     end =nums - 1
        # if start <= nums - 1:

        part_cert = ServiceDomainCertificate.objects.filter(tenant_id=tenant_id)[start:end + 1]
        return part_cert, nums

    def get_certificate_by_alias(self, tenant_id, alias):
        sdc = ServiceDomainCertificate.objects.filter(tenant_id=tenant_id, alias=alias)
        if sdc:
            return sdc[0]
        return None

    def add_service_domain(self, **domain_info):
        return ServiceDomain.objects.create(**domain_info)

    def get_certificate_by_pk(self, pk):
        try:
            return ServiceDomainCertificate.objects.get(pk=pk)
        except ServiceDomainCertificate.DoesNotExist:
            return None

    def add_certificate(self, tenant_id, alias, certificate_id, certificate, private_key, certificate_type):
        service_domain_certificate = dict()
        service_domain_certificate["tenant_id"] = tenant_id
        service_domain_certificate["certificate_id"] = certificate_id
        service_domain_certificate["certificate"] = certificate
        service_domain_certificate["private_key"] = private_key
        service_domain_certificate["alias"] = alias
        service_domain_certificate["certificate_type"] = certificate_type
        service_domain_certificate["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        certificate_info = ServiceDomainCertificate(**service_domain_certificate)
        certificate_info.save()
        return certificate_info

    def delete_certificate_by_alias(self, tenant_id, alias):
        ServiceDomainCertificate.objects.filter(tenant_id=tenant_id, alias=alias).delete()

    def delete_certificate_by_pk(self, pk):
        ServiceDomainCertificate.objects.filter(pk=pk).delete()

    def get_service_domains(self, service_id):
        return ServiceDomain.objects.filter(service_id=service_id).all()

    def create_service_domains(
            self, service_id, service_name, domain_name, create_time, container_port, protocol, http_rule_id, tenant_id,
            service_alias, region_id):
        ServiceDomain.objects.create(
            service_id=service_id,
            service_name=service_name,
            domain_name=domain_name,
            create_time=create_time,
            container_port=container_port,
            protocol=protocol,
            http_rule_id=http_rule_id,
            tenant_id=tenant_id,
            service_alias=service_alias,
            region_id=region_id)

    def delete_http_domains(self, http_rule_id):
        ServiceDomain.objects.filter(http_rule_id=http_rule_id).delete()

    def check_custom_rule(self, eid):
        """
        check if there is a custom gateway rule
        """
        conn = BaseConnection()
        sql = """
            SELECT
                *
            FROM
                service_domain a,
                tenant_info b
            WHERE
                a.tenant_id = b.tenant_id
                AND b.enterprise_id = "{eid}"
                AND (
                    a.certificate_id <> 0
                    OR ( a.domain_path <> "/" AND a.domain_path <> "" )
                    OR a.domain_cookie <> ""
                    OR a.domain_heander <> ""
                    OR a.the_weight <> 100
                    OR a.domain_name NOT LIKE concat('%',b.tenant_name,'%')
                )
                LIMIT 1""".format(eid=eid)
        result = conn.query(sql)
        return True if len(result) > 0 else False

    def list_service_domains_by_cert_id(self, certificate_id):
        return ServiceDomain.objects.filter(certificate_id=certificate_id)


class ServiceExtendRepository(object):
    # only market service return extend_method
    def get_extend_method_by_service(self, service):
        if service.service_source == "market":
            sem = ServiceExtendMethod.objects.filter(service_key=service.service_key, app_version=service.version)
            if sem:
                return sem[0]
        return None

    def create_extend_method(self, **params):
        return ServiceExtendMethod.objects.create(**params)


class CompileEnvRepository(object):
    def delete_service_compile_env(self, service_id):
        TenantServiceEnv.objects.filter(service_id=service_id).delete()

    def save_service_compile_env(self, **params):
        return TenantServiceEnv.objects.create(**params)

    def get_service_compile_env(self, service_id):
        tse = TenantServiceEnv.objects.filter(service_id=service_id)
        if tse:
            return tse[0]
        return None

    def update_service_compile_env(self, service_id, **update_params):
        TenantServiceEnv.objects.filter(service_id=service_id).update(**update_params)


class ServiceAuthRepository(object):
    def delete_service_auth(self, service_id):
        TenantServiceAuth.objects.filter(service_id=service_id).delete()

    def get_service_auth(self, service_id):
        return TenantServiceAuth.objects.filter(service_id=service_id)


class ServiceAttachInfoRepository(object):
    def delete_service_attach(self, service_id):
        ServiceAttachInfo.objects.filter(service_id=service_id).delete()


class ServiceStepRepository(object):
    def delete_create_step(self, service_id):
        ServiceCreateStep.objects.filter(service_id=service_id).delete()


class ServicePaymentRepository(object):
    def delete_service_payment(self, service_id):
        ServicePaymentNotify.objects.filter(service_id=service_id).delete()


class ServiceTcpDomainRepository(object):
    def get_service_tcp_domain_by_service_id(self, service_id):

        tcp_domain = ServiceTcpDomain.objects.filter(service_id=service_id).first()
        if tcp_domain:
            return tcp_domain
        else:
            return None

    def get_service_tcp_domain_by_service_id_and_port(self, service_id, container_port, domain_name):
        tcp_domain = ServiceTcpDomain.objects.filter(
            service_id=service_id, container_port=container_port, end_point=domain_name).first()
        if tcp_domain:
            return tcp_domain
        else:
            return None

    def get_service_tcp_domains_by_service_id_and_port(self, service_id, container_port):

        return ServiceTcpDomain.objects.filter(service_id=service_id, container_port=container_port)

    def get_all_domain_count_by_tenant_and_region(self, tenant_id, region_id):
        return ServiceTcpDomain.objects.filter(tenant_id=tenant_id, region_id=region_id).count()

    def delete_tcp_domain(self, tcp_rule_id):
        ServiceTcpDomain.objects.filter(tcp_rule_id=tcp_rule_id).delete()

    def create_service_tcp_domains(self, service_id, service_name, end_point, create_time, container_port, protocol,
                                   service_alias, tcp_rule_id, tenant_id, region_id):
        ServiceTcpDomain.objects.create(
            service_id=service_id,
            service_name=service_name,
            end_point=end_point,
            create_time=create_time,
            service_alias=service_alias,
            container_port=container_port,
            protocol=protocol,
            tcp_rule_id=tcp_rule_id,
            tenant_id=tenant_id,
            region_id=region_id)

    def get_tcpdomain_by_name_and_port(self, service_id, container_port, end_point):
        try:
            return ServiceTcpDomain.objects.get(
                service_id=service_id, container_port=container_port, end_point=end_point)
        except ServiceTcpDomain.DoesNotExist:
            return None

    def get_tcpdomain_by_end_point(self, region_id, end_point):
        try:
            hostport = end_point.split(":")
            if len(hostport) > 1:
                if hostport[0] == "0.0.0.0":
                    query = Q(region_id=region_id, end_point__icontains=":{}".format(hostport[1]))
                    return ServiceTcpDomain.objects.filter(query)
                queryDefaultEndpoint = "0.0.0.0:{0}".format(hostport[1])
                query = Q(region_id=region_id, end_point=end_point) | Q(
                    region_id=region_id, end_point=queryDefaultEndpoint)
                return ServiceTcpDomain.objects.filter(query)
            return None
        except ServiceTcpDomain.DoesNotExist:
            return None

    def add_service_tcpdomain(self, **domain_info):
        return ServiceTcpDomain.objects.create(**domain_info)

    def get_service_tcpdomains(self, service_id):
        return ServiceTcpDomain.objects.filter(service_id=service_id).all()

    def get_service_tcpdomain_by_tcp_rule_id(self, tcp_rule_id):
        return ServiceTcpDomain.objects.filter(tcp_rule_id=tcp_rule_id).first()

    def delete_service_tcp_domain(self, service_id):
        ServiceTcpDomain.objects.filter(service_id=service_id).delete()

    def get_service_tcpdomain(self, tenant_id, region_id, service_id, container_port):
        return ServiceTcpDomain.objects.filter(
            tenant_id=tenant_id, region_id=region_id, service_id=service_id, container_port=container_port).first()


class TenantServiceEndpoints(object):
    def add_service_endpoints(self, service_endpoints):
        return ThirdPartyServiceEndpoints.objects.create(**service_endpoints)

    def get_service_endpoints_by_service_id(self, service_id):
        data = ThirdPartyServiceEndpoints.objects.filter(service_id=service_id).first()
        if data:
            return data
        return None


class GatewayCustom(object):
    def get_configuration_by_rule_id(self, rule_id):
        return GatewayCustomConfiguration.objects.filter(rule_id=rule_id).first()

    def add_configuration(self, **configuration_info):
        return GatewayCustomConfiguration.objects.create(**configuration_info)


tcp_domain = ServiceTcpDomainRepository()
env_var_repo = TenantServiceEnvVarRepository()
port_repo = TenantServicePortRepository()
image_service_relation_repo = ImageServiceRelationRepository()
domain_repo = ServiceDomainRepository()
volume_repo = TenantServiceVolumnRepository()
mnt_repo = TenantServiceMntRelationRepository()
dep_relation_repo = TenantServiceRelationRepository()
extend_repo = ServiceExtendRepository()
compile_env_repo = CompileEnvRepository()
# 其他
auth_repo = ServiceAuthRepository()
service_attach_repo = ServiceAttachInfoRepository()
create_step_repo = ServiceStepRepository()
service_payment_repo = ServicePaymentRepository()
# endpoints
service_endpoints_repo = TenantServiceEndpoints()
configuration_repo = GatewayCustom()
