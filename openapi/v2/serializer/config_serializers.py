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
    TITLE = serializers.CharField(max_length=255, required=False)
    LOGO = serializers.CharField(max_length=2097152, required=False)
    REGISTER_STATUS = serializers.CharField(max_length=255, required=False)
    RAINBOND_VERSION = serializers.CharField(max_length=255, required=False)
    ENTERPRISE_ALIAS = serializers.CharField(max_length=255, required=False)


class UpdateBaseConfigReqSerializer(serializers.Serializer):
    TITLE = serializers.CharField(max_length=255, required=False)
    LOGO = serializers.CharField(max_length=255, required=False)
    REGISTER_STATUS = serializers.CharField(max_length=255, required=False)
    RAINBOND_VERSION = serializers.CharField(max_length=255, required=False)
    ENTERPRISE_ALIAS = serializers.CharField(max_length=255, required=False)


class GithubServiceAPIRespSerializer(serializers.Serializer):
    client_secret = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    redirect_uri = serializers.CharField(max_length=2047, allow_null=True, allow_blank=True, required=False)
    client_id = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)


class GithubServiceBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = GithubServiceAPIRespSerializer(required=False)


class GitlabServiceAPIRespSerializer(serializers.Serializer):
    admin_user = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    url = serializers.CharField(max_length=2047, allow_null=True, allow_blank=True, required=False)
    apitype = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    hook_url = serializers.CharField(max_length=2047, allow_null=True, allow_blank=True, required=False)
    admin_password = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    admin_email = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)


class GitlabServiceBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = GitlabServiceAPIRespSerializer(required=False)


class AppStoreImageHubRespSerializer(serializers.Serializer):
    namespace = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    hub_password = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    hub_url = serializers.CharField(max_length=2047, allow_null=True, allow_blank=True, required=False)
    hub_user = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)


class AppStoreImageHubBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = AppStoreImageHubRespSerializer(required=False)


class OpenDataCenterStatusRespSerializer(serializers.Serializer):
    pass


class OpenDataCenterStatusBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = serializers.CharField(max_length=225, allow_null=True, allow_blank=True, required=False)


class OfficialDemoRespSerializer(serializers.Serializer):
    pass


class OfficialDemoBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = serializers.CharField(max_length=225, allow_null=True, allow_blank=True, required=False)


class NewBieGuideRespSerializer(serializers.Serializer):
    pass


class NewBieGuideBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = serializers.CharField(max_length=225, allow_null=True, allow_blank=True, required=False)


class ExportAppRespSerializer(serializers.Serializer):
    pass


class ExportAppBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = serializers.CharField(max_length=225, allow_null=True, allow_blank=True, required=False)


class CloudMarketRespSerializer(serializers.Serializer):
    pass


class CloudMarketBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = serializers.CharField(max_length=225, allow_null=True, allow_blank=True, required=False)


class DocumentRespSerializer(serializers.Serializer):
    platform_url = serializers.CharField(max_length=2047, allow_null=True, allow_blank=True, required=False)


class DocumentBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = DocumentRespSerializer(required=False)


class ObjectStorageRespSerializer(serializers.Serializer):
    provider = serializers.CharField(max_length=255, allow_blank=True)
    endpoint = serializers.CharField(max_length=2047, allow_blank=True)
    access_key = serializers.CharField(max_length=255, allow_blank=True)
    secret_key = serializers.CharField(max_length=255, allow_blank=True)
    bucket_name = serializers.CharField(max_length=255, allow_blank=True)


class ObjectStorageBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = ObjectStorageRespSerializer(required=False)


class OauthServicesRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=True)
    auth_url = serializers.CharField(required=False, max_length=255)
    name = serializers.CharField(max_length=64)
    client_id = serializers.CharField(max_length=255)
    client_secret = serializers.CharField(max_length=255)
    redirect_uri = serializers.CharField(max_length=255)
    is_console = serializers.BooleanField(default=False)
    is_auto_login = serializers.BooleanField(default=False)
    service_id = serializers.IntegerField(required=False, allow_null=True)
    oauth_type = serializers.CharField(max_length=64)
    eid = serializers.CharField(max_length=64)
    home_url = serializers.CharField(max_length=255, allow_null=True, allow_blank=True, required=False)
    access_token_url = serializers.CharField(required=False, max_length=255)
    api_url = serializers.CharField(required=False, max_length=255)
    is_deleted = serializers.BooleanField(default=False)


class OauthServicesBaseRespSerializer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = OauthServicesRespSerializer(required=False, many=True)


class FeatureConfigRespSerializer(serializers.Serializer):
    github = GithubServiceBaseRespSerializer(required=True)
    gitlab = GitlabServiceBaseRespSerializer(required=True)
    appstore_image_hub = AppStoreImageHubBaseRespSerializer(required=True)
    open_data_center_status = OpenDataCenterStatusBaseRespSerializer(required=True)
    official_demo = OfficialDemoBaseRespSerializer(required=True)
    newbie_guide = NewBieGuideBaseRespSerializer(required=True)
    export_app = ExportAppBaseRespSerializer(required=True)
    cloud_market = CloudMarketBaseRespSerializer(required=True)
    document = DocumentBaseRespSerializer(required=True)
    object_storage = ObjectStorageBaseRespSerializer(required=False)
    oauth_services = OauthServicesBaseRespSerializer(required=False)


class UpdateFeatureCfgReqSerializer(serializers.Serializer):
    github = GithubServiceBaseRespSerializer(required=False)
    gitlab = GitlabServiceBaseRespSerializer(required=False)
    appstore_image_hub = AppStoreImageHubBaseRespSerializer(required=False)
    open_data_center_status = OpenDataCenterStatusBaseRespSerializer(required=False)
    official_demo = OfficialDemoBaseRespSerializer(required=False)
    newbie_guide = NewBieGuideBaseRespSerializer(required=False)
    export_app = ExportAppBaseRespSerializer(required=False)
    cloud_market = CloudMarketBaseRespSerializer(required=False)
    document = DocumentBaseRespSerializer(required=False)
    object_storage = ObjectStorageBaseRespSerializer(required=False)
    oauth_services = OauthServicesBaseRespSerializer(required=False)
