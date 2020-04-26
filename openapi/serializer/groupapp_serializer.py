# -*- coding: utf-8 -*-
# create by: panda-zxs

from rest_framework import serializers


class CompomentBuildSourceSerializer(serializers.Serializer):
    oauth_service_id = serializers.IntegerField(allow_null=True, help_text="OAuth服务id")
    version = serializers.CharField(max_length=32, allow_null=True, help_text="版本")
    language = serializers.CharField(max_length=32, allow_null=True, help_text="语言")
    code_from = serializers.CharField(max_length=32, allow_null=True, help_text="构建类型")
    image = serializers.CharField(max_length=32, allow_null=True, help_text="镜像")
    cmd = serializers.CharField(max_length=32, allow_null=True, help_text="cmd")
    server_type = serializers.CharField(max_length=32, allow_null=True, help_text="服务类型")
    docker_cmd = serializers.CharField(max_length=32, allow_null=True, help_text="docker_cmd")
    create_time = serializers.DateTimeField(allow_null=True, help_text="创建日期")
    git_url = serializers.CharField(max_length=32, allow_null=True, help_text="git地址")
    full_name = serializers.CharField(max_length=32, allow_null=True, help_text="git仓库full_name")
    service_id = serializers.CharField(max_length=32, allow_null=True, help_text="id")
    password = serializers.CharField(max_length=32, allow_null=True, help_text="密码")
    user_name = serializers.CharField(max_length=32, allow_null=True, help_text="用户名")
    code_version = serializers.CharField(max_length=32, allow_null=True, help_text="代码版本")
    service_source = serializers.CharField(max_length=32, allow_null=True, help_text="应用来源")


class GroupAppCopyLSerializer(serializers.Serializer):
    build_source = CompomentBuildSourceSerializer()
    update_time = serializers.DateTimeField(help_text="更新日期",  allow_null=True)
    deploy_version = serializers.CharField(max_length=32, help_text="构建版本", allow_null=True)
    create_status = serializers.CharField(max_length=32, allow_null=True, help_text="创建状态")
    service_alias = serializers.CharField(max_length=32, allow_null=True, help_text="组件昵称")
    service_cname = serializers.CharField(max_length=32, allow_null=True, help_text="组件中文名称")
    version = serializers.CharField(max_length=32, allow_null=True, help_text="版本")
    service_type = serializers.CharField(max_length=32, allow_null=True, help_text="组件类型")
    service_id = serializers.CharField(max_length=32, allow_null=True, help_text="id")
    group_name = serializers.CharField(max_length=32, allow_null=True, help_text="应用名称")
    min_memory = serializers.CharField(max_length=32, allow_null=True, help_text="组件运行内存")

    def to_internal_value(self, data):
        self._writable_fields.pop(0)
        internal = super(GroupAppCopyLSerializer, self).to_internal_value(data)
        ser = CompomentBuildSourceSerializer(data["build_source"])
        internal["build_source"] = ser.data
        return internal


class GroupAppChangeBuildSourceSerializer(serializers.Serializer):
    version = serializers.CharField(max_length=32, allow_null=True, help_text="版本")


class GroupAppModifyInfoSerializer(serializers.Serializer):
    build_source = GroupAppChangeBuildSourceSerializer()


class GroupAppCopyModifySerializer(serializers.Serializer):
    service_id = serializers.CharField(max_length=32, help_text="id")
    change = GroupAppModifyInfoSerializer()


class GroupAppCopyCSerializer(serializers.Serializer):
    services = GroupAppCopyModifySerializer(many=True)
    tar_team_name = serializers.CharField(max_length=32, help_text="团队id")
    tar_region_name = serializers.CharField(max_length=32, help_text="数据中心名称")
    tar_group_id = serializers.IntegerField(help_text="应用id")


class GroupAppCopyCResSerializer(serializers.Serializer):
    group_app_url = serializers.CharField(max_length=128, help_text="应用路由")
