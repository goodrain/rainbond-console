# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers


class ConfigBaseSerializer(serializers.Serializer):
    enable = serializers.BooleanField(required=False, default=False)


class MonitorQueryOverviewSeralizer(serializers.Serializer):
    data = serializers.DictField(help_text="查询数据")
    status = serializers.CharField(help_text="查询状态", max_length=64)


class AppStoreImageHubRespSerializer(serializers.Serializer):
    namespace = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    hub_password = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    hub_url = serializers.CharField(max_length=2047, allow_null=True, allow_blank=True, required=False)
    hub_user = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)


class OfficialDemoRespSerializer(serializers.Serializer):
    pass


class NewBieGuideRespSerializer(serializers.Serializer):
    pass


class ExportAppRespSerializer(serializers.Serializer):
    pass


class CloudMarketRespSerializer(serializers.Serializer):
    pass


class DocumentRespSerializer(serializers.Serializer):
    platform_url = serializers.CharField(max_length=2047, allow_null=True, allow_blank=True, required=False)


class ObjectStorageRespSerializer(serializers.Serializer):
    provider = serializers.CharField(max_length=255, allow_blank=True)
    endpoint = serializers.CharField(max_length=2047, allow_blank=True)
    access_key = serializers.CharField(max_length=255, allow_blank=True)
    secret_key = serializers.CharField(max_length=255, allow_blank=True)
    bucket_name = serializers.CharField(max_length=255, allow_blank=True)


class OauthServicesRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=True)
    auth_url = serializers.CharField(required=False, max_length=255)
    name = serializers.CharField(max_length=64)
    is_console = serializers.BooleanField(default=False)
    is_auto_login = serializers.BooleanField(default=False)
    service_id = serializers.IntegerField(required=False, allow_null=True)
    oauth_type = serializers.CharField(max_length=64)
    eid = serializers.CharField(max_length=64)
    home_url = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    access_token_url = serializers.CharField(required=False, max_length=255)
    api_url = serializers.CharField(required=False, max_length=255)
    is_deleted = serializers.BooleanField(default=False)
    is_git = serializers.BooleanField(default=False)


class OfficialDemoBaseRespSerializer(ConfigBaseSerializer):
    enable = serializers.BooleanField(default=False)
    value = serializers.CharField(max_length=225, allow_null=True, allow_blank=True, required=False)


class DocumentBaseRespSerializer(ConfigBaseSerializer):
    value = DocumentRespSerializer(required=False)


class ExportAppBaseRespSerializer(ConfigBaseSerializer):
    value = serializers.CharField(max_length=225, allow_null=True, allow_blank=True, required=False)


class NewBieGuideBaseRespSerializer(ConfigBaseSerializer):
    value = serializers.CharField(max_length=225, allow_null=True, allow_blank=True, required=False)


class AppStoreImageHubBaseRespSerializer(ConfigBaseSerializer):
    value = AppStoreImageHubRespSerializer(required=False)


class ObjectStorageBaseRespSerializer(ConfigBaseSerializer):
    value = ObjectStorageRespSerializer(required=False)


class CloudMarketBaseRespSerializer(ConfigBaseSerializer):
    value = serializers.CharField(max_length=225, allow_null=True, allow_blank=True, required=False)


class AutoSSLSerializer(ConfigBaseSerializer):
    value = serializers.JSONField(allow_null=True)


class OauthServicesBaseRespSerializer(ConfigBaseSerializer):
    value = OauthServicesRespSerializer(required=False, many=True)


class EnterpriseConfigSeralizer(serializers.Serializer):
    export_app = ExportAppBaseRespSerializer(required=False, help_text="新密码")
    auto_ssl = AutoSSLSerializer(required=False, allow_null=True)
    oauth_services = OauthServicesBaseRespSerializer(required=False)
    cloud_market = CloudMarketBaseRespSerializer(required=False)
    object_storage = ObjectStorageBaseRespSerializer(required=False)
    appstore_image_hub = AppStoreImageHubBaseRespSerializer(required=False)
    newbie_guide = NewBieGuideBaseRespSerializer(required=False)



class ResourceOverviewSeralizer(serializers.Serializer):
    nodes = serializers.ListField(help_text="资源级别")
    links = serializers.ListField(help_text="资源关系")