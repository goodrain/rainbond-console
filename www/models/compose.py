# -*- coding: utf8 -*-
from django.db import models
from .main import BaseModel


class DockerService(BaseModel):
    class Meta:
        db_table = 'docker_service'

    compose_id = models.IntegerField(help_text="DockerComposeYaml的ID")
    command = models.CharField(max_length=100, null=True, blank=True, help_text="替换默认的command")

    name = models.CharField(max_length=100, help_text="组件的节点名称")
    depends_on = models.CharField(max_length=100, help_text="依赖的组件名称,逗号分割")
    entrypoint = models.CharField(max_length=100, help_text="镜像的启动脚本")

    environment = models.CharField(max_length=500, help_text="镜像的环境参数,dict的json")

    image = models.CharField(max_length=100, help_text="镜像的名称")
    links = models.CharField(max_length=500, help_text="relation，逗号分隔")
    expose = models.CharField(max_length=100, help_text="镜像的对内端口，逗号分割")
    ports = models.CharField(max_length=500, help_text="镜像对外端口，逗号分割")
    volumes = models.CharField(max_length=500, help_text="持久化，逗号分隔")
    volumes_from = models.CharField(max_length=15, help_text="挂载项，逗号分割")

    build = models.CharField(max_length=100, help_text="docker_file的文件路径,暂不支持")
    context = models.CharField(max_length=30, help_text="docker_file的文件路径上下文。,暂不支持")
    dockerfile = models.CharField(max_length=30, help_text="docker_file的文件名称,暂不支持")
    args = models.CharField(max_length=100, help_text="docker_file的args，json格式。,暂不支持")
    cap_add = models.CharField(max_length=100, help_text="逗号分隔,暂不支持")
    cap_drop = models.CharField(max_length=100, help_text="逗号分隔,暂不支持")
    cgroup_parent = models.CharField(max_length=50, help_text=",暂不支持")
    container_name = models.CharField(max_length=50, help_text="自定义容器的名称,暂不支持")
    devices = models.CharField(max_length=50, help_text="容器终端，逗号分隔,暂不支持")
    dns = models.CharField(max_length=50, help_text="dns，逗号分隔,暂不支持")
    dns_search = models.CharField(max_length=50, help_text="dns_search，逗号分隔,暂不支持")
    tmpfs = models.CharField(max_length=50, help_text="挂载临时目录，逗号分隔,暂不支持")
    env_file = models.CharField(max_length=100, help_text="env文件，逗号分隔,暂不支持")
    extends = models.CharField(max_length=100, help_text="扩展信息，逗号分隔,暂不支持")
    external_links = models.CharField(max_length=100, help_text="扩展的外部容器，逗号分隔,暂不支持")
    extra_hosts = models.CharField(max_length=100, help_text="host mapping，逗号分隔,暂不支持")
    group_add = models.CharField(max_length=50, help_text="添加组信息，逗号分隔,暂不支持")
    isolation = models.CharField(max_length=20, help_text="容器的隔离策略，default, process and hyperv。暂不支持")
    logging = models.CharField(max_length=200, help_text="容器的日志配置。暂不支持")

    def is_slug(self):
        return self.build is not None or self.build != ""

    def is_image(self):
        return self.image is not None or self.image != ""


class DockerComposeYaml(BaseModel):
    """ 组件发布表格 """
    class Meta:
        db_table = 'docker_compose_yaml'

    version = models.CharField(max_length=10, default="1", help_text="docker compose version")
    file_name = models.CharField(max_length=100, help_text="docker compose file name")
    md5 = models.CharField(max_length=100, help_text="docker compose file md5")
    services = models.CharField(max_length=3000, help_text="docker compose services")
    volumes = models.CharField(max_length=1000, help_text="docker compose volumes")
    networks = models.CharField(max_length=500, help_text="docker compose networks")
    build_args = models.CharField(max_length=200, help_text="docker compose build_args")
