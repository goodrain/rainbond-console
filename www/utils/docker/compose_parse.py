#!/usr/bin/env python
# -*- coding: utf8 -*-
from compose import config
from compose.config.environment import Environment
import os
import json
from www.models.compose import *
from www.utils.md5Util import get_md5
import re
import logging

logger = logging.getLogger('default')

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
    try:
        compose_config = parse_compose(file_dir, file_name=file_name)
    except Exception as e:
        return None,str(e)
    # 解析docker compose，转化为goodrain平台信息
    version = compose_config.version
    yaml_info = DockerComposeYaml(version=version,
                                  file_name=file_path,
                                  md5=md5string,
                                  services=compose_config.services,
                                  volumes=compose_config.volumes,
                                  networks=compose_config.networks,
                                  build_args="")
    yaml_info.save()
    # 解析文件
    service_list = []
    if version in ["1", "1.0", "2", "2.0", "2.1"]:
        # 每一个service对应一个tenant_service
        volume_dict = {}
        for service_info in compose_config.services:
            # 检查是否build标签
            if "build" in service_info.keys():
                return None, "now we donot support build!"
            # new docker service
            docker_service = DockerService(compose_id=yaml_info.ID)

            compose_name = service_info.get("name")
            logger.debug("composer_name is %s" %compose_name)
            docker_service.name = compose_name
            compose_image = service_info.get("image")
            docker_service.image = compose_image
            if "command" in service_info.keys():
                compose_command = service_info.get("command")
                docker_service.command = compose_command

            docker_service.build = ""
            docker_service.context = ""
            docker_service.dockerfile = ""
            docker_service.args = ""
            docker_service.cap_add = ""
            docker_service.cap_drop = ""
            docker_service.cgroup_parent = ""
            docker_service.container_name = ""
            docker_service.devices = ""
            docker_service.dns = ""
            docker_service.dns_search = ""
            docker_service.tmpfs = ""
            docker_service.env_file = ""
            docker_service.extends = ""
            docker_service.external_links = ""
            docker_service.extra_hosts = ""
            docker_service.group_add = ""
            docker_service.isolation = ""
            docker_service.logging = ""
            docker_service.entrypoint = ""

            # 处理entrypoint, 如果存在entrypoint 替换空的command
            if service_info.get("entrypoint", None):
                docker_service.command = service_info.get("entrypoint")

            if "environment" in service_info.keys():
                docker_service.environment = json.dumps(service_info.get("environment"))
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
                    if str(info_port).isdigit():
                        result.append(info_port)
                    else:
                        # 去掉ip

                        port_reg = re.compile('\d+\.\d+\.\d+\.\d+:')
                        tmp_port = port_reg.sub("", info_port)
                        # 使用:进行分割
                        port_array = tmp_port.split(":")
                        tmp_port = port_array[0]
                        if tmp_port.isdigit():
                            result.append(tmp_port)
                        else:
                            port_array = tmp_port.split("-")
                            for i in range(int(port_array[0]), int(port_array[1])+1):
                                result.append(i)
                docker_service.ports = json.dumps(result)
            if "expose" in service_info.keys():
                # 内部端口
                docker_service.expose = json.dumps(service_info.get("expose"))
            if "links" in service_info.keys():
                compose_links = service_info.get("links")
                result = []
                for link in compose_links:
                    result.append(link.split(":")[0])
                docker_service.links = json.dumps(result)
            if "volumes" in service_info.keys():
                compose_volumes = service_info.get("volumes")
                volume_path_list = []
                for vol in compose_volumes:
                    volume_path_list.append(vol.internal)
                    if version == 2:
                        volume_dict[vol.external] = service_info
                docker_service.volumes = json.dumps(volume_path_list)

            if "depends_on" in service_info.keys():
                compose_depends = service_info.get("depends_on")
                depend_list = []
                for depend in compose_depends:
                    depend_list.append(depend.split(":")[0])

                docker_service.depends_on = json.dumps(depend_list)
            docker_service.save()
            service_list.append(docker_service)
        if version == 2:
            # 可能存在多个服务共用卷问题
            pass
        return service_list, "success"
    else:
        return None, "docker compose file version is not support!"

#
# if __name__ == "__main__":
#     print "DEMO"
#     base_dir = os.path.abspath(".")
#     compose_config = compose_list(os.path.join(base_dir, "b.yml"))
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
#             result = []
#             # 这里需要解析
#             # - "3000"
#             # - "3000-3005"
#             # - "8000:8000"
#             # - "9090-9091:8080-8081"
#             # - "49100:22"
#             # - "127.0.0.1:8001:8001"
#             # - "127.0.0.1:5000-5010:5000-5010"
#             for info_port in compose_ports:
#                 if info_port.isdigit():
#                     result.append(info_port)
#                 else:
#                     # 去掉ip
#                     port_reg = re.compile('\d+\.\d+\.\d+\.\d+:')
#                     tmp_port = port_reg.sub("", info_port)
#                     # 使用:进行分割
#                     port_array = tmp_port.split(":")
#                     tmp_port = port_array[0]
#                     if tmp_port.isdigit():
#                         result.append(tmp_port)
#                     else:
#                         port_array = tmp_port.split("-")
#                         for i in range(int(port_array[0]), int(port_array[1])+1):
#                             result.append(i)
#
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








