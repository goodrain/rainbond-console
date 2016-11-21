#!/usr/bin/env python
# -*- coding: utf8 -*-
from compose import config
from compose.config.environment import Environment
from www.models.compose import *
import os
import json
from www.utils.md5Util import get_md5


def get_config_path_from_options(options, environment):
    file_option = options.get('--file')
    if file_option:
        return file_option

    config_files = environment.get('COMPOSE_FILE')
    if config_files:
        return config_files.split(os.pathsep)
    return None


def parse_compose(file_dir, file_name=None):
    options = {}
    if file_name is not None:
        options["--file"] = [file_name]
    environment = Environment.from_env_file(file_dir)
    config_path = get_config_path_from_options(options, environment)
    return config.load(
        config.find(file_dir, config_path, environment)
    )


def compose_list(file_path):
    if not os.path.exists(file_path):
        return None, "docker compose file is not exists!"
    # 计算文件的md5值
    md5string = get_md5(file_path)
    # 检查数据库中是否有记录
    md5num = DockerComposeYaml.objects.filter(md5=md5string).count()
    if md5num == 1:
        # 文件已经解析过
        yaml_info = DockerComposeYaml.objects.get(md5=md5string)
        service_list = DockerService.objects.filter(compose_id=yaml_info.ID)
        return service_list, "success"

    # now parse docker compose
    file_name = os.path.basename(file_path)
    file_dir = os.path.dirname(file_path)
    compose_config = parse_compose(file_dir, file_name=file_name)
    # 解析docker compose，转化未goodrain平台信息
    version = compose_config.version
    yaml_info = DockerComposeYaml(version=version,
                                  file_name=file_path,
                                  md5=md5string,
                                  services=compose_config.services,
                                  volumes=compose_config.volumes,
                                  networks=compose_config.networks,
                                  build_args=compose_config.args)
    yaml_info.save()
    # 解析文件
    if version == 1 or version == 2:
        # 每一个service对应一个tenant_service
        volume_dict = {}
        for service_info in compose_config.services:
            # 检查是否build标签
            if "build" in service_info.keys():
                return None, "now we donot support build!"
            # new docker service
            service_info = DockerService(compose_id=yaml_info.ID)
            # service_cname="",
            # image="",
            # cmd="",
            # info = TenantServiceInfo(service_id="",
            #                          tenant_id="",
            #                          service_key="",
            #                          service_alias="",
            #                          service_region="",
            #                          desc="",
            #                          category="",
            #                          service_port=5000,
            #                          is_web_service=True,
            #                          version="",
            #                          update_version=1,
            #                          setting="",
            #                          extend_method="stateless",
            #                          env="",
            #                          min_node="",
            #                          min_cpu="",
            #                          min_memory="",
            #                          inner_port="",
            #                          volume_mount_path="",
            #                          host_path="",
            #                          deploy_version="",
            #                          code_from="",
            #                          git_url="",
            #                          git_project_id=0,
            #                          is_code_upload=False,
            #                          code_version="",
            #                          service_type="application",
            #                          creater="",
            #                          language="image",
            #                          protocol="",
            #                          total_memory="",
            #                          is_service="",
            #                          namespace="goodrain",
            #                          volume_type="shared",
            #                          port_type="multi_outer",
            #                          service_origin="assistant")
            compose_name = service_info.get("name")
            service_info.name = compose_name
            compose_image = service_info.get("image")
            service_info.image = compose_image
            if "command" in service_info.keys():
                compose_command = service_info.get("command")
                service_info.command = compose_command

            service_info.depends_on = models.CharField(max_length=100, help_text=u"依赖的服务名称,逗号分割")
            service_info.entrypoint = models.CharField(max_length=100, help_text=u"镜像的启动脚本")

            service_info.volumes_from = models.CharField(max_length=15, help_text=u"挂载项，逗号分割")

            service_info.build = ""
            service_info.context = ""
            service_info.dockerfile = ""
            service_info.args = ""
            service_info.cap_add = ""
            service_info.cap_drop = ""
            service_info.cgroup_parent = ""
            service_info.container_name = ""
            service_info.devices = ""
            service_info.dns = ""
            service_info.dns_search = ""
            service_info.tmpfs = ""
            service_info.env_file = ""
            service_info.extends = ""
            service_info.external_links = ""
            service_info.extra_hosts = ""
            service_info.group_add = ""
            service_info.isolation = ""
            service_info.logging = ""

            if "environment" in service_info.keys():
                service_info.environment = json.dumps(service_info.get("environment"))
                # compose_env = service_info.get("environment")
                # if isinstance(compose_env, dict):
                #     for k, v in compose_env.items():
                #         env_var = TenantServiceEnvVar(tenant_id="",
                #                                       service_id="",
                #                                       container_port=-1,
                #                                       name=k,
                #                                       attr_name=k,
                #                                       attr_value=v,
                #                                       is_change=True,
                #                                       scope="both")
            if "ports" in service_info.keys():
                compose_ports = service_info.get("ports")
                result = []
                for info_port in compose_ports:
                    # 这里需要解析
                    # - "3000"
                    # - "3000-3005"
                    # - "8000:8000"
                    # - "9090-9091:8080-8081"
                    # - "49100:22"
                    # - "127.0.0.1:8001:8001"
                    # - "127.0.0.1:5000-5010:5000-5010"
                    # TenantServicesPort(tenant_id="",
                    #                    service_id="",
                    #                    container_port="",
                    #                    mapping_port="",
                    #                    protocol="",
                    #                    port_alias="",
                    #                    is_inner_service=False,
                    #                    is_outer_service=True)
                    result.append(info_port)
                service_info.ports = json.dumps(result)
            if "expose" in service_info.keys():
                # 内部端口
                service_info.expose = json.dumps(service_info.get("expose"))
                # compose_exposes = service_info.get("expose")
                # for expose in compose_exposes:
                #     TenantServicesPort(tenant_id="",
                #                        service_id="",
                #                        container_port=expose,
                #                        mapping_port=expose,
                #                        protocol="",
                #                        port_alias="",
                #                        is_inner_service=True,
                #                        is_outer_service=False)
            if "links" in service_info.keys():
                service_info.links = json.dumps(service_info.get("external_links"))
                # links = service_info.get("external_links")
                # for service_cname in links:
                #     mnt_name = "/mnt/{0}".format(dep_service_name)
                #     mnt_dir = "/grdata/tenant/{0}/service/{1}".format(tenant_id, service_id)
                #     TenantServiceMountRelation(tenant_id="",
                #                                service_id="",
                #                                dep_service_id="",
                #                                mnt_name=mnt_name,
                #                                mnt_dir=mnt_dir)
            if "volumes" in service_info.keys():
                compose_volumes = service_info.get("volumes")
                volume_path_list = []
                for vol in compose_volumes:
                    volume_path_list.append(vol.internal)
                    if version == 2:
                        volume_dict[vol.external] = service_info
                        # volume_path = vol.internal
                        # host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant_id, service_id, volume_path)
                        # TenantServiceVolume(service_id="",
                        #                     category="application",
                        #                     host_path=host_path,
                        #                     volume_path=volume_path)
                service_info.volumes = json.dumps(volume_path_list)

            if "depends_on" in service_info.keys():
                compose_depends = service_info.get("depends_on")
                depend_list = []
                for depend in compose_depends:
                    if ":" in depend:
                        depend_list.append(depend.split(":")[0])
                    else:
                        depend_list.append(depend)
                service_info.depends_on = json.dumps(depend_list)
        if version == 2:
            # 可能存在多个服务共用卷问题
            pass
    else:
        return None, "docker compose file version is not support!"

#
# if __name__ == "__main__":
#     print "DEMO"
#     base_dir = os.path.abspath(".")
#     compose_config = parse_compose(base_dir, file_name="b.yml")
#     # compose_config = custom_compose(base_dir, "a.yml")
#     # print compose_config
#     print(compose_config.version)
#     for service_info in compose_config.services:
#         # print service_info
#         compose_name = service_info.get("name")
#         print compose_name
#         compose_image = service_info.get("image")
#         print compose_image
#
#         # 写入tenant_service_env_var
#         if "environment" in service_info.keys():
#             compose_env = service_info.get("environment")
#             print(compose_env)
#             if isinstance(compose_env, dict):
#                 for k, v in compose_env.items():
#                     print k, v
#
#         if "command" in service_info.keys():
#             compose_command = service_info.get("command")
#             print compose_command
#
#         if "ports" in service_info.keys():
#             compose_ports = service_info.get("ports")
#             print(compose_ports)
#             for info_port in compose_ports:
#                 print info_port
#                 print type(info_port)
#
#         if "volumes" in service_info.keys():
#             compose_volumes = service_info.get("volumes")
#             print (compose_volumes)
#             for vol in compose_volumes:
#                 print vol.external
#                 print vol.internal
#                 print vol.mode
#
#         if "restart" in service_info.keys():
#             compose_restart = service_info.get("restart")
#             print compose_restart.get("MaximumRetryCount")
#             print compose_restart.get("Name")








