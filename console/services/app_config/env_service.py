# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
import re
from console.repositories.app_config import env_var_repo, compile_env_repo
from www.apiclient.regionapi import RegionInvokeApi
import logging

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class AppEnvVarService(object):
    SENSITIVE_ENV_NAMES = (
        'TENANT_ID', 'SERVICE_ID', 'TENANT_NAME', 'SERVICE_NAME', 'SERVICE_VERSION', 'MEMORY_SIZE',
        'SERVICE_EXTEND_METHOD',
        'SLUG_URL', 'DEPEND_SERVICE', 'REVERSE_DEPEND_SERVICE', 'POD_ORDER', 'PATH', 'POD_NET_IP', 'LOG_MATCH'
    )

    def check_env_attr_name(self, attr_name):
        if attr_name in self.SENSITIVE_ENV_NAMES:
            return False, u"不允许的变量名{0}".format(attr_name)

        if not re.match(r'^[a-zA-Z0-9_\\-]+$', attr_name):
            return False, u"变量名称{0}不符合规范".format(attr_name)
        return True, u"success"

    def add_service_env_var(self, tenant, service, container_port, name, attr_name, attr_value, isChange,
                            scope="outer"):
        attr_name = str(attr_name).strip()
        attr_value = str(attr_value).strip()
        is_pass, msg = self.check_env_attr_name(attr_name)
        if not is_pass:
            return 400, msg, None
        if len(str(attr_value)) > 512:
            attr_value = str(attr_value)[:512]
        tenantServiceEnvVar = {}
        tenantServiceEnvVar["tenant_id"] = service.tenant_id
        tenantServiceEnvVar["service_id"] = service.service_id
        tenantServiceEnvVar['container_port'] = container_port
        tenantServiceEnvVar["name"] = name
        tenantServiceEnvVar["attr_name"] = attr_name
        tenantServiceEnvVar["attr_value"] = attr_value
        tenantServiceEnvVar["is_change"] = isChange
        tenantServiceEnvVar["scope"] = scope
        env = env_var_repo.get_service_env_by_attr_name(service.tenant_id, service.service_id, attr_name)
        if env:
            return 412, u"环境变量{0}已存在".format(attr_name), None
        # 判断是否需要再region端添加
        if service.create_status == "complete":
            attr = {"container_port": container_port,
                    "tenant_id": service.tenant_id, "service_id": service.service_id, "name": name,
                    "attr_name": attr_name, "attr_value": str(attr_value), "is_change": True, "scope": scope,
                    "env_name": attr_name, "env_value": str(attr_value), "enterprise_id": tenant.enterprise_id
                    }

            region_api.add_service_env(service.service_region, tenant.tenant_name,
                                       service.service_alias, attr)
        new_env = env_var_repo.add_service_env(**tenantServiceEnvVar)
        return 200, 'success', new_env

    def get_env_var(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id)

    def get_self_define_env(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id).exclude(container_port=-1,
                                                                                               scope="outer")

    def get_service_inner_env(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id).filter(scope="inner")

    def get_service_outer_env(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id).filter(
                scope__in=("outer", "both"))

    def get_changeable_env(self, service):
        if service:
            return env_var_repo.get_service_env(service.tenant_id, service.service_id).exclude(is_change=False)

    def delete_env_by_attr_name(self, tenant, service, attr_name):
        if service.create_status == "complete":
            region_api.delete_service_env(service.service_region, tenant.tenant_name,
                                          service.service_alias, {"env_name": attr_name,
                                                                  "enterprise_id": tenant.enterprise_id})
        env_var_repo.delete_service_env_by_attr_name(tenant.tenant_id, service.service_id, attr_name)

    def delete_env_by_container_port(self, tenant, service, container_port):
        envs = env_var_repo.get_service_env_by_port(tenant.tenant_id, service.service_id, container_port)
        if service.create_status == "complete":
            for env in envs:
                data = {"env_name": env.attr_name, "enterprise_id": tenant.enterprise_id}
                region_api.delete_service_env(service.service_region, tenant.tenant_name, service.service_alias, data)
        env_var_repo.delete_service_env_by_port(tenant.tenant_id, service.service_id, container_port)

    def get_env_by_attr_name(self, tenant, service, attr_name):
        return env_var_repo.get_service_env_by_attr_name(tenant.tenant_id, service.service_id, attr_name)

    def get_env_by_container_port(self, tenant, service, container_port):
        return env_var_repo.get_service_env_by_port(tenant.tenant_id, service.service_id, container_port)

    def update_env_by_attr_name(self, tenant, service, attr_name, name, attr_value):
        attr_name = attr_name.strip()
        attr_value = attr_value.strip()
        env = env_var_repo.get_service_env_by_attr_name(tenant.tenant_id, service.service_id, attr_name)
        if not env:
            return 404, "环境变量不存在", None
        if not env.is_change:
            return 409, "环境变量不允许被修改", None
        update_params = {"name": name, "attr_value": attr_value}
        if service.create_status == "complete":
            body = {"env_name": attr_name, "env_value": attr_value}
            region_api.update_service_env(service.service_region, tenant.tenant_name, service.service_alias, body)
        env_var_repo.update_env_var(tenant.tenant_id, service.service_id, attr_name, **update_params)
        env.name = name
        env.attr_value = attr_value
        return 200, "success", env

    def delete_service_env(self, tenant, service):
        env_var_repo.delete_service_env(tenant.tenant_id, service.service_id)

    def delete_region_env(self, tenant, service):
        envs = self.get_env_var(service)
        for env in envs:
            data = {"env_name": env.attr_name, "enterprise_id": tenant.enterprise_id}
            try:
                region_api.delete_service_env(service.service_region, tenant.tenant_name, service.service_alias, data)
            except Exception as e:
                logger.exception(e)


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