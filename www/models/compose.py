# -*- coding: utf8 -*-
import re
from django.db import models
from django.utils.crypto import salted_hmac
from www.utils.crypt import encrypt_passwd, make_tenant_id
from django.db.models.fields import DateTimeField
from datetime import datetime
from main import BaseModel


class DockerService(BaseModel):
    class Meta:
        db_table = 'docker_service'
    compose_id = models.IntegerField(help_text=u"DockerComposeYaml的ID")
    command = models.CharField(max_length=100, null=True, blank=True, help_text=u"替换默认的command")

    name = models.CharField(max_length=100, help_text=u"服务的节点名称")
    depends_on = models.CharField(max_length=100, help_text=u"依赖的服务名称,逗号分割")
    entrypoint = models.CharField(max_length=100, help_text=u"镜像的启动脚本")

    environment = models.CharField(max_length=500, help_text=u"镜像的环境参数,dict的json")

    image = models.CharField(max_length=100, help_text=u"镜像的名称")
    links = models.CharField(max_length=500, help_text=u"relation，逗号分隔")
    expose = models.CharField(max_length=100, help_text=u"镜像的对内端口，逗号分割")
    ports = models.CharField(max_length=500, help_text=u"镜像对外端口，逗号分割")
    volumes = models.CharField(max_length=500, help_text=u"持久化，逗号分隔")
    volumes_from = models.CharField(max_length=15, help_text=u"挂载项，逗号分割")

    build = models.CharField(max_length=100, help_text=u"docker_file的文件路径,暂不支持")
    context = models.CharField(max_length=30, help_text=u"docker_file的文件路径上下文。,暂不支持")
    dockerfile = models.CharField(max_length=30, help_text=u"docker_file的文件名称,暂不支持")
    args = models.CharField(max_length=100, help_text=u"docker_file的args，json格式。,暂不支持")
    cap_add = models.CharField(max_length=100, help_text=u"逗号分隔,暂不支持")
    cap_drop = models.CharField(max_length=100, help_text=u"逗号分隔,暂不支持")
    cgroup_parent = models.CharField(max_length=50, help_text=u",暂不支持")
    container_name = models.CharField(max_length=50, help_text=u"自定义容器的名称,暂不支持")
    devices = models.CharField(max_length=50, help_text=u"容器终端，逗号分隔,暂不支持")
    dns = models.CharField(max_length=50, help_text=u"dns，逗号分隔,暂不支持")
    dns_search = models.CharField(max_length=50, help_text=u"dns_search，逗号分隔,暂不支持")
    tmpfs = models.CharField(max_length=50, help_text=u"挂载临时目录，逗号分隔,暂不支持")
    env_file = models.CharField(max_length=100, help_text=u"env文件，逗号分隔,暂不支持")
    extends = models.CharField(max_length=100, help_text=u"扩展信息，逗号分隔,暂不支持")
    external_links = models.CharField(max_length=100, help_text=u"扩展的外部容器，逗号分隔,暂不支持")
    extra_hosts = models.CharField(max_length=100, help_text=u"host mapping，逗号分隔,暂不支持")
    group_add = models.CharField(max_length=50, help_text=u"添加组信息，逗号分隔,暂不支持")
    isolation = models.CharField(max_length=20, help_text=u"容器的隔离策略，default, process and hyperv。暂不支持")
    logging = models.CharField(max_length=200, help_text=u"容器的日志配置。暂不支持")

    def is_slug(self):
        return self.build is not None or self.build != ""

    def is_image(self):
        return self.image is not None or self.image != ""


class DockerComposeYaml(BaseModel):
    """ 服务发布表格 """
    class Meta:
        db_table = 'docker_compose_yaml'

    version = models.CharField(max_length=10, default="1", help_text=u"docker compose version")
    file_name = models.CharField(max_length=100, help_text=u"docker compose file name")
    md5 = models.CharField(max_length=100, help_text=u"docker compose file md5")
    services = models.CharField(max_length=3000, help_text=u"docker compose services")
    volumes = models.CharField(max_length=1000, help_text=u"docker compose volumes")
    networks = models.CharField(max_length=500, help_text=u"docker compose networks")
    build_args = models.CharField(max_length=200, help_text=u"docker compose build_args")
