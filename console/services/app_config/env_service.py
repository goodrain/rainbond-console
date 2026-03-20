# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
import json
import logging
import re
from itertools import chain
from datetime import datetime

from django.db.transaction import atomic

# exception
from console.exception.main import (EnvAlreadyExist, InvalidEnvName, ServiceHandleException)
# repository
from console.repositories.app_config import (compile_env_repo, dep_relation_repo, env_var_repo)
# model
from www.models.main import TenantServicesPort, TenantServiceEnvVar
# www
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class AppEnvVarService(object):
    SENSITIVE_ENV_NAMES = ('TENANT_ID', 'SERVICE_ID', 'TENANT_NAME', 'SERVICE_NAME', 'SERVICE_VERSION', 'MEMORY_SIZE',
                           'SERVICE_EXTEND_METHOD', 'SLUG_URL', 'DEPEND_SERVICE', 'REVERSE_DEPEND_SERVICE', 'POD_ORDER', 'PATH',
                           'POD_NET_IP', 'LOG_MATCH')

    def check_env_attr_name(self, attr_name):
        if attr_name in self.SENSITIVE_ENV_NAMES:
            return False, "不允许的变量名{0}".format(attr_name)

        if not re.match(r"^[-._a-zA-Z][-._a-zA-Z0-9]*$", attr_name):
            return False, "变量名称{0}不符合规范".format(attr_name)
        return True, "success"

    def check_env(self, component, attr_name, attr_value):
        if env_var_repo.get_service_env_by_attr_name(component.tenant_id, component.service_id, attr_name):
            raise EnvAlreadyExist()
        attr_name = str(attr_name).strip()
        attr_value = str(attr_value).strip()
        is_pass, msg = self.check_env_attr_name(attr_name)
        if not is_pass:
            raise InvalidEnvName(msg)

    def create_env_var(self, service, container_port, name, attr_name, attr_value, is_change=False, scope="outer"):
        """
        raise: EnvAlreadyExist
        raise: InvalidEnvName
        """
        self.check_env(service, attr_name, attr_value)
        if len(str(attr_value)) > 65532:
            attr_value = str(attr_value)[:65532]
        tenantServiceEnvVar = {}
        tenantServiceEnvVar["tenant_id"] = service.tenant_id
        tenantServiceEnvVar["service_id"] = service.service_id
        tenantServiceEnvVar['container_port'] = container_port
        tenantServiceEnvVar["name"] = name
        tenantServiceEnvVar["attr_name"] = attr_name
        tenantServiceEnvVar["attr_value"] = attr_value
        tenantServiceEnvVar["is_change"] = is_change
        tenantServiceEnvVar["scope"] = scope
        return env_var_repo.add_service_env(**tenantServiceEnvVar)

    def json_service_env_var(self, attr_name, attr_value, name):
        return json.dumps({"变量名": attr_name, "变量值": attr_value, "说明": name}, ensure_ascii=False)

    def env_to_log(self, env):
        if not env:
            return "{}"
        if hasattr(env, "to_dict"):
            return json.dumps(env.to_dict(), ensure_ascii=False)
        return json.dumps({
            "ID": getattr(env, "ID", None),
            "tenant_id": getattr(env, "tenant_id", None),
            "service_id": getattr(env, "service_id", None),
            "name": getattr(env, "name", None),
            "attr_name": getattr(env, "attr_name", None),
            "attr_value": getattr(env, "attr_value", None),
            "scope": getattr(env, "scope", None),
            "container_port": getattr(env, "container_port", None),
            "is_change": getattr(env, "is_change", None),
        }, ensure_ascii=False)

    def envs_to_log(self, envs):
        return json.dumps([
            {
                "ID": getattr(env, "ID", None),
                "name": getattr(env, "name", None),
                "attr_name": getattr(env, "attr_name", None),
                "attr_value": getattr(env, "attr_value", None),
                "scope": getattr(env, "scope", None),
                "container_port": getattr(env, "container_port", None),
                "is_change": getattr(env, "is_change", None),
            } for env in envs
        ], ensure_ascii=False)

    def add_service_env_var(self,
                            tenant,
                            service,
                            container_port,
                            name,
                            attr_name,
                            attr_value,
                            is_change,
                            scope="outer",
                            user_name=''):
        logger.info("[PurchaseEnvConsole] add_service_env_var request tenant=%s service_alias=%s service_id=%s create_status=%s scope=%s name=%s attr_name=%s attr_value=%s is_change=%s",
                    tenant.tenant_name, service.service_alias, service.service_id, service.create_status, scope, name, attr_name, attr_value, is_change)
        attr_name = str(attr_name).strip()
        attr_value = str(attr_value).strip()
        is_pass, msg = self.check_env_attr_name(attr_name)
        if not is_pass:
            logger.info("[PurchaseEnvConsole] add_service_env_var invalid name tenant=%s service_id=%s attr_name=%s msg=%s",
                        tenant.tenant_name, service.service_id, attr_name, msg)
            return 400, msg, None
        if len(str(attr_value)) > 65532:
            attr_value = str(attr_value)[:65532]
        tenantServiceEnvVar = {}
        tenantServiceEnvVar["tenant_id"] = service.tenant_id
        tenantServiceEnvVar["service_id"] = service.service_id
        tenantServiceEnvVar['container_port'] = container_port
        tenantServiceEnvVar["name"] = name
        tenantServiceEnvVar["attr_name"] = attr_name
        tenantServiceEnvVar["attr_value"] = attr_value
        tenantServiceEnvVar["is_change"] = is_change
        tenantServiceEnvVar["scope"] = scope
        env = env_var_repo.get_service_env_by_attr_name(service.tenant_id, service.service_id, attr_name)
        if env:
            logger.info("[PurchaseEnvConsole] add_service_env_var existing env tenant=%s service_alias=%s service_id=%s attr_name=%s existing_env=%s",
                        tenant.tenant_name, service.service_alias, service.service_id, attr_name, self.env_to_log(env))
            return 412, "环境变量{0}已存在".format(attr_name), env
        # 判断是否需要再region端添加
        if service.create_status == "complete":
            attr = {
                "container_port": container_port,
                "tenant_id": service.tenant_id,
                "service_id": service.service_id,
                "name": name,
                "attr_name": attr_name,
                "attr_value": str(attr_value),
                "is_change": True,
                "scope": scope,
                "env_name": attr_name,
                "env_value": str(attr_value),
                "enterprise_id": tenant.enterprise_id,
                "operator": user_name
            }
            logger.info("[PurchaseEnvConsole] add_service_env_var sync region request tenant=%s service_alias=%s service_id=%s region=%s body=%s",
                        tenant.tenant_name, service.service_alias, service.service_id, service.service_region,
                        json.dumps(attr, ensure_ascii=False))
            region_api.add_service_env(service.service_region, tenant.tenant_name, service.service_alias, attr)
        new_env = env_var_repo.add_service_env(**tenantServiceEnvVar)
        logger.info("[PurchaseEnvConsole] add_service_env_var created env tenant=%s service_alias=%s service_id=%s env=%s",
                    tenant.tenant_name, service.service_alias, service.service_id, self.env_to_log(new_env))
        return 200, 'success', new_env

    def get_env_var(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id)

    def get_self_define_env(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id).exclude(container_port=-1, scope="outer")

    def get_service_inner_env(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id).filter(scope="inner")

    def get_service_outer_env(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id).filter(scope__in=("outer", "both"))

    def get_service_build_envs(self, service):
        if service:
            return env_var_repo.get_service_env_by_scope(service.tenant_id, service.service_id, scope="build")

    def add_service_build_env_var(self, tenant, service, container_port, name, attr_name, attr_value, is_change, scope="build"):
        attr_name = str(attr_name).strip()
        attr_value = str(attr_value).strip()
        is_pass, msg = self.check_env_attr_name(attr_name)
        if not is_pass:
            return 400, msg, None
        if len(str(attr_value)) > 65532:
            attr_value = str(attr_value)[:65532]

        tenant_service_env_var = dict()
        tenant_service_env_var["tenant_id"] = service.tenant_id
        tenant_service_env_var["service_id"] = service.service_id
        tenant_service_env_var['container_port'] = container_port
        tenant_service_env_var["name"] = name
        tenant_service_env_var["attr_name"] = attr_name
        tenant_service_env_var["attr_value"] = attr_value
        tenant_service_env_var["is_change"] = is_change
        tenant_service_env_var["scope"] = scope

        new_env = env_var_repo.add_service_env(**tenant_service_env_var)
        return 200, 'success', new_env

    def get_changeable_env(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id).exclude(is_change=False)

    def delete_env_by_attr_name(self, tenant, service, attr_name):
        if service.create_status == "complete":
            region_api.delete_service_env(service.service_region, tenant.tenant_name, service.service_alias, {
                "env_name": attr_name,
                "enterprise_id": tenant.enterprise_id
            })
        env_var_repo.delete_service_env_by_attr_name(tenant.tenant_id, service.service_id, attr_name)

    def delete_env_by_env_id(self, tenant, service, env_id, user_name=''):
        env = env_var_repo.get_env_by_ids_and_env_id(tenant.tenant_id, service.service_id, env_id)
        if env:
            env_var_repo.delete_service_env_by_attr_name(tenant.tenant_id, service.service_id, env.attr_name)
            if service.create_status == "complete":
                region_api.delete_service_env(service.service_region, tenant.tenant_name, service.service_alias, {
                    "env_name": env.attr_name,
                    "enterprise_id": tenant.enterprise_id,
                    "operator": user_name
                })

    def delete_env_by_container_port(self, tenant, service, container_port, user_name=''):
        envs = env_var_repo.get_service_env_by_port(tenant.tenant_id, service.service_id, container_port)
        if service.create_status == "complete":
            for env in envs:
                data = {"env_name": env.attr_name, "enterprise_id": tenant.enterprise_id, "operator": user_name}
                region_api.delete_service_env(service.service_region, tenant.tenant_name, service.service_alias, data)
        env_var_repo.delete_service_env_by_port(tenant.tenant_id, service.service_id, container_port)

    def get_env_by_attr_name(self, tenant, service, attr_name):
        return env_var_repo.get_service_env_by_attr_name(tenant.tenant_id, service.service_id, attr_name)

    def get_env_by_container_port(self, tenant, service, container_port):
        return env_var_repo.get_service_env_by_port(tenant.tenant_id, service.service_id, container_port)

    def patch_env_scope(self, tenant, service, env_id, scope, user_name=''):
        env = env_var_repo.get_service_env_or_404_by_env_id(tenant.tenant_id, service.service_id, env_id)
        if env:
            if service.create_status == "complete":
                body = {"env_name": env.attr_name, "env_value": env.attr_value, "scope": scope, "operator": user_name}
                region_api.update_service_env(service.service_region, tenant.tenant_name, service.service_alias, body)
            env_var_repo.change_service_env_scope(env, scope)
            return env

    def update_env_by_env_id(self, tenant, service, env_id, name, attr_value, user_name=''):
        env_id = env_id.strip()
        attr_value = attr_value.strip()
        env = env_var_repo.get_env_by_ids_and_env_id(tenant.tenant_id, service.service_id, env_id)
        if not env:
            return 404, "环境变量不存在", None
        logger.info("[PurchaseEnvConsole] update_env_by_env_id request tenant=%s service_alias=%s service_id=%s env_id=%s old_env=%s new_name=%s new_value=%s",
                    tenant.tenant_name, service.service_alias, service.service_id, env_id, self.env_to_log(env), name, attr_value)
        update_params = {"name": name, "attr_value": attr_value}
        if service.create_status == "complete":
            body = {"env_name": env.attr_name, "env_value": attr_value, "scope": env.scope, "operator": user_name}
            logger.info("[PurchaseEnvConsole] update_env_by_env_id sync region request tenant=%s service_alias=%s service_id=%s region=%s body=%s",
                        tenant.tenant_name, service.service_alias, service.service_id, service.service_region,
                        json.dumps(body, ensure_ascii=False))
            region_api.update_service_env(service.service_region, tenant.tenant_name, service.service_alias, body)
        env_var_repo.update_env_var(tenant.tenant_id, service.service_id, env.attr_name, **update_params)
        env.name = name
        env.attr_value = attr_value
        logger.info("[PurchaseEnvConsole] update_env_by_env_id success tenant=%s service_alias=%s service_id=%s updated_env=%s",
                    tenant.tenant_name, service.service_alias, service.service_id, self.env_to_log(env))
        return 200, "success", env

    def delete_service_env(self, tenant, service):
        env_var_repo.delete_service_env(tenant.tenant_id, service.service_id)

    def delete_service_build_env(self, tenant, service):
        env_var_repo.delete_service_build_env(tenant.tenant_id, service.service_id)

    def delete_region_env(self, tenant, service):
        envs = self.get_env_var(service)
        for env in envs:
            data = {"env_name": env.attr_name, "enterprise_id": tenant.enterprise_id}
            try:
                region_api.delete_service_env(service.service_region, tenant.tenant_name, service.service_alias, data)
            except Exception as e:
                logger.exception(e)

    @atomic
    def update_or_create_envs(self, team, service, envs):
        has_envs = env_var_repo.get_service_env(service.tenant_id, service.service_id)
        env_attr_names = {env.attr_name: env for env in has_envs}
        logger.info("[PurchaseEnvConsole] update_or_create_envs request tenant=%s service_alias=%s service_id=%s incoming_envs=%s existing_envs=%s",
                    team.tenant_name, service.service_alias, service.service_id,
                    json.dumps(envs, ensure_ascii=False), self.envs_to_log(has_envs))
        for env in envs:
            if env["name"] in list(env_attr_names.keys()):
                logger.info("[PurchaseEnvConsole] update_or_create_envs choose update tenant=%s service_alias=%s service_id=%s env_name=%s env_id=%s",
                            team.tenant_name, service.service_alias, service.service_id, env["name"], env_attr_names[env["name"]].ID)
                code, msg, env = self.update_env_by_env_id(team, service, str(env_attr_names[env["name"]].ID), env["note"],
                                                           env["value"])
                if code != 200:
                    raise ServiceHandleException(status_code=code, msg="update or create envs error", msg_show=msg)
            else:
                logger.info("[PurchaseEnvConsole] update_or_create_envs choose create tenant=%s service_alias=%s service_id=%s env_name=%s",
                            team.tenant_name, service.service_alias, service.service_id, env["name"])
                code, msg, env = self.add_service_env_var(team, service, 0, env["note"], env["name"], env["value"],
                                                          env["is_change"], env["scope"])
                if code != 200:
                    raise ServiceHandleException(status_code=code, msg="update or create envs error", msg_show=msg)
        total_envs = env_var_repo.get_service_env(service.tenant_id, service.service_id)
        dt = []
        for env in total_envs:
            dt.append({
                "note": env.name,
                "name": env.attr_name,
                "value": env.attr_value,
                "is_change": env.is_change,
                "scope": env.scope,
            })
        logger.info("[PurchaseEnvConsole] update_or_create_envs result tenant=%s service_alias=%s service_id=%s total_envs=%s",
                    team.tenant_name, service.service_alias, service.service_id, json.dumps(dt, ensure_ascii=False))
        return {"envs": dt}

    def get_all_envs_incloud_depend_env(self, tenant, service):
        selfenv = self.get_env_var(service)
        dep_service_ids = dep_relation_repo.get_service_dependencies(tenant.tenant_id, service.service_id).values_list(
            "dep_service_id", flat=True)
        envs = env_var_repo.get_depend_outer_envs_by_ids(tenant.tenant_id, dep_service_ids)
        return chain(selfenv, envs)

    @staticmethod
    def create_port_env(port: TenantServicesPort, name, attr_name_suffix, attr_value):
        return TenantServiceEnvVar(
            tenant_id=port.tenant_id,
            service_id=port.service_id,
            container_port=port.container_port,
            name=name,
            attr_name=port.port_alias + "_" + attr_name_suffix,
            attr_value=attr_value,
            is_change=False,
            scope="outer",
            create_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )


class AppEnvService(object):
    def delete_service_compile_env(self, service):
        compile_env_repo.delete_service_compile_env(service.service_id)

    def save_compile_env(self, service, language, check_dependency, user_dependency):
        params = {
            "service_id": service.service_id,
            "language": language,
            "check_dependency": check_dependency,
            "user_dependency": user_dependency
        }
        return compile_env_repo.save_service_compile_env(**params)

    def get_service_compile_env(self, service):
        return compile_env_repo.get_service_compile_env(service.service_id)

    def update_service_compile_env(self, service, **update_params):
        compile_env_repo.update_service_compile_env(service.service_id, **update_params)
        return compile_env_repo.get_service_compile_env(service.service_id)

    def get_service_default_env_by_language(self, language):
        """
        根据指定的语言找到默认的环境变量
        :param language:  语言
        :return: 语言对应的默认的环境变量
        """
        checkJson = {}
        if language == "dockerfile":
            checkJson["language"] = 'dockerfile'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Python":
            checkJson["language"] = 'Python'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Ruby":
            checkJson["language"] = 'Ruby'
            checkJson["runtimes"] = "2.0.0"
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "PHP":
            checkJson["language"] = 'PHP'
            checkJson["runtimes"] = "5.6.11"
            checkJson["procfile"] = "apache"
            dependencies = {}
            checkJson["dependencies"] = dependencies
        elif language == "Java-maven":
            checkJson["language"] = 'Java-maven'
            checkJson["runtimes"] = "1.8"
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Java-war":
            checkJson["language"] = 'Java-war'
            checkJson["runtimes"] = "1.8"
            checkJson["procfile"] = "tomcat7"
            checkJson["dependencies"] = {}
        elif language == "Java-jar":
            checkJson["language"] = 'Java-jar'
            checkJson["runtimes"] = "1.8"
            checkJson["procfile"] = "tomcat7"
            checkJson["dependencies"] = {}
        elif language == "Node.js":
            checkJson["language"] = 'Node.js'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "static":
            checkJson["language"] = 'static'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = "apache"
            checkJson["dependencies"] = {}
        elif language == "Clojure":
            checkJson["language"] = 'Clojure'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Go":
            checkJson["language"] = 'Go'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Gradle":
            checkJson["language"] = 'Gradle'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Play":
            checkJson["language"] = 'Play'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Grails":
            checkJson["language"] = 'Grails'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Scala":
            checkJson["language"] = 'Scala'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        return checkJson
