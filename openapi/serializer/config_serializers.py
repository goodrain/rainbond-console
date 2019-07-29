# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers


class ConfigSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=32)
    type = serializers.CharField(max_length=32)
    value = serializers.CharField(max_length=4096)
    desc = serializers.CharField(max_length=40)
    enable = serializers.BooleanField()
    create_time = serializers.DateTimeField()


class RegionServiceAPISerializer(serializers.Serializer):
    url = serializers.CharField(max_length=255)
    token = serializers.CharField(max_length=255, allow_null=True, required=False)
    enable = serializers.BooleanField(help_text="是否启用: true->启用, false->不启用")
    region_name = serializers.CharField(max_length=255, help_text="数据中心名称")
    region_alias = serializers.CharField(max_length=255, help_text="数据中心别名")


class BaseConfigRespSerializer(serializers.Serializer):
    REGION_SERVICE_API = RegionServiceAPISerializer(many=True, required=False)
    TITLE = serializers.CharField(max_length=255, required=False)
    LOGO = serializers.CharField(max_length=255, required=False)
    REGISTER_STATUS = serializers.CharField(max_length=255, required=False)
    RAINBOND_VERSION = serializers.CharField(max_length=255, required=False)
    enterprise_alias = serializers.CharField(max_length=255, required=False)


class UpdateBaseConfigReqSerializer(serializers.Serializer):
    REGION_SERVICE_API = RegionServiceAPISerializer(many=True, required=False)
    TITLE = serializers.CharField(max_length=255, required=False)
    LOGO = serializers.CharField(max_length=255, required=False)
    REGISTER_STATUS = serializers.CharField(max_length=255, required=False)
    RAINBOND_VERSION = serializers.CharField(max_length=255, required=False)


class GithubServiceAPIRespSerializer(serializers.Serializer):
    client_secret = serializers.CharField(max_length=255)
    redirect_uri = serializers.CharField(max_length=255)
    client_id = serializers.CharField(max_length=255)


class GitlabServiceAPIRespSerializer(serializers.Serializer):
    admin_user = serializers.CharField(max_length=255)
    url = serializers.CharField(max_length=255)
    apitype = serializers.CharField(max_length=255)
    hook_url = serializers.CharField(max_length=255)
    admin_password = serializers.CharField(max_length=255)
    admin_email = serializers.CharField(max_length=255)


class UpdateFeatureCfgReqSerializer(serializers.Serializer):
    GITHUB_SERVICE_API = GithubServiceAPIRespSerializer(required=False)
    GITLAB_SERVICE_API = GitlabServiceAPIRespSerializer(required=False)


class FeatureConfigRespSerializer(serializers.Serializer):
    GITHUB_SERVICE_API = GithubServiceAPIRespSerializer(required=False)
    GITLAB_SERVICE_API = GitlabServiceAPIRespSerializer(required=False)
