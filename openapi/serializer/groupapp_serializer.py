# -*- coding: utf-8 -*-
# create by: panda-zxs

from rest_framework import serializers

from openapi.serializer.app_serializer import ServiceBaseInfoSerializer


class CompomentBuildSourceSerializer(serializers.Serializer):
    version = serializers.CharField(max_length=32, allow_null=True, help_text="版本")
    language = serializers.CharField(max_length=64, allow_null=True, help_text="语言")
    code_from = serializers.CharField(max_length=32, allow_null=True, help_text="构建类型")
    service_source = serializers.CharField(max_length=32, allow_null=True, help_text="应用来源")


class CompomentDockerImageBuildSourceSerializer(CompomentBuildSourceSerializer):
    docker_cmd = serializers.CharField(max_length=1024, allow_null=True, help_text="docker_cmd")
    image = serializers.CharField(max_length=200, allow_null=True, help_text="镜像")
    password = serializers.CharField(max_length=255, allow_null=True, help_text="密码")
    user_name = serializers.CharField(max_length=255, allow_null=True, help_text="用户名")


class CompomentMarketBuildSourceSerializer(CompomentBuildSourceSerializer):
    rain_app_name = serializers.CharField(max_length=64, allow_null=True, help_text="应用包名")


class CompomentCodeBuildSourceSerializer(CompomentBuildSourceSerializer):
    code_version = serializers.CharField(max_length=32, allow_null=True, help_text="版本")
    git_url = serializers.CharField(max_length=2047, allow_null=True, help_text="git地址")
    full_name = serializers.CharField(max_length=64, allow_null=True, help_text="git仓库full_name")
    service_id = serializers.CharField(max_length=32, allow_null=True, help_text="id")
    oauth_service_id = serializers.IntegerField(allow_null=True, help_text="OAuth服务id")
    user_name = serializers.CharField(max_length=255, allow_null=True, help_text="用户名")
    password = serializers.CharField(max_length=255, allow_null=True, help_text="密码")


class AppCopyLSerializer(serializers.Serializer):
    build_source = serializers.SerializerMethodField()
    update_time = serializers.DateTimeField(help_text="更新日期", allow_null=True)
    deploy_version = serializers.CharField(max_length=32, help_text="构建版本", allow_null=True)
    create_status = serializers.CharField(max_length=32, allow_null=True, help_text="创建状态")
    service_alias = serializers.CharField(max_length=64, allow_null=True, help_text="组件昵称")
    service_cname = serializers.CharField(max_length=128, allow_null=True, help_text="组件中文名称")
    version = serializers.CharField(max_length=32, allow_null=True, help_text="版本")
    service_type = serializers.CharField(max_length=64, allow_null=True, help_text="组件类型")
    service_id = serializers.CharField(max_length=32, allow_null=True, help_text="id")
    app_name = serializers.CharField(max_length=64, allow_null=True, help_text="应用名称")
    min_memory = serializers.CharField(max_length=32, allow_null=True, help_text="组件运行内存")

    def to_internal_value(self, data):
        return data

    def get_build_source(self, instance):
        build_source = instance.get("build_source")
        service_source = build_source.get("service_source")
        if service_source == "docker_image":
            serializer = CompomentDockerImageBuildSourceSerializer(data=build_source)
            serializer.is_valid(raise_exception=True)
        elif service_source == "market":
            serializer = CompomentMarketBuildSourceSerializer(data=build_source)
            serializer.is_valid(raise_exception=True)
        elif service_source == "source_code":
            serializer = CompomentCodeBuildSourceSerializer(data=build_source)
            serializer.is_valid(raise_exception=True)
        else:
            serializer = CompomentBuildSourceSerializer(data=build_source)
            serializer.is_valid(raise_exception=True)
        return serializer.data


class AppChangeBuildSourceSerializer(serializers.Serializer):
    version = serializers.CharField(max_length=32, allow_null=True, help_text="版本")


class AppModifyInfoSerializer(serializers.Serializer):
    build_source = serializers.SerializerMethodField()

    def get_build_source(self, instance):
        default_build_source = {"version": None}
        build_source = instance.get("build_source")
        if not build_source:
            return default_build_source
        else:
            serializer = AppChangeBuildSourceSerializer(data=build_source)
            serializer.is_valid(raise_exception=True)
            return serializer.data

    def to_internal_value(self, data):
        return data


class AppCopyModifySerializer(serializers.Serializer):
    service_id = serializers.CharField(max_length=32, help_text="id")
    change = serializers.SerializerMethodField()

    def get_change(self, instance):
        default_change = {"build_source": {"version": None}}
        change = instance.get("change")
        if not change:
            return default_change
        else:
            serializer = AppModifyInfoSerializer(data=change)
            serializer.is_valid(raise_exception=True)
            return serializer.data


class AppCopyCSerializer(serializers.Serializer):
    services = AppCopyModifySerializer(many=True)
    target_team_name = serializers.CharField(max_length=32, help_text="团队名称")
    target_region_name = serializers.CharField(max_length=32, help_text="数据中心名称")
    target_app_id = serializers.IntegerField(help_text="应用id")

    def to_internal_value(self, data):
        return data


class AppCopyCResSerializer(serializers.Serializer):
    services = ServiceBaseInfoSerializer(many=True)

    def to_internal_value(self, data):
        return data
