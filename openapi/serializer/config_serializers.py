# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers


class ConfigBaseSerializer(serializers.Serializer):
    enable = serializers.BooleanField(required=False, default=False)


class MonitorQueryOverviewSeralizer(serializers.Serializer):
    data = serializers.DictField(help_text="查询数据")
    status = serializers.CharField(help_text="查询状态", max_length=64)

class AppRankOverviewSeralizer(serializers.Serializer):
    visits = serializers.IntegerField(help_text="实时访问数[每5分钟]", default=0)
    memory = serializers.IntegerField(help_text="使用内存", default=0)
    app_name = serializers.CharField(help_text="应用名", max_length=64)
    team_alias = serializers.CharField(help_text="团队名", max_length=64)
    region_alias = serializers.CharField(help_text="集群名", max_length=64)


class MonitorMessageOverviewSeralizer(serializers.Serializer):
    event_type = serializers.CharField(help_text="事件类型", max_length=64)
    event_nums = serializers.IntegerField(help_text="事件发生次数", default=0)
    team_alias = serializers.CharField(help_text="团队名", max_length=64)
    app_name = serializers.CharField(help_text="应用名", max_length=64)
    component_name = serializers.CharField(help_text="组件名", max_length=64)
    region_alias = serializers.CharField(help_text="集群名", max_length=64)

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


class VisualMonitorURLSeralizer(serializers.Serializer):
    home_url = serializers.CharField(help_text="监控主页地址")
    cluster_monitor_suffix = serializers.CharField(help_text="集群监控拼接后缀")
    node_monitor_suffix = serializers.CharField(help_text="节点监控拼接后缀")
    component_monitor_suffix = serializers.CharField(help_text="组件监控拼接后缀")
    slo_monitor_suffix = serializers.CharField(help_text="服务监控拼接后缀")


class VisualMonitorSeralizer(serializers.Serializer):
    enable = serializers.BooleanField(default=False)
    value = VisualMonitorURLSeralizer()


class EnterpriseOverviewSeralizer(serializers.Serializer):
    teams = serializers.IntegerField(help_text="团队数", default=0)
    apps = serializers.IntegerField(help_text="应用数", default=0)
    components = serializers.IntegerField(help_text="组件数", default=0)
    instances = serializers.IntegerField(help_text="实例数", default=0)
    nodes = serializers.IntegerField(help_text="节点数", default=0)
    visual_monitor = VisualMonitorSeralizer()



class ResourceOverviewSeralizer(serializers.Serializer):
    nodes = serializers.ListField(help_text="资源级别")
    links = serializers.ListField(help_text="资源关系")


class ServieOveriewSeralizer(serializers.Serializer):
    abnormal_service_num = serializers.IntegerField(help_text="异常的组件个数")
    closed_service_num = serializers.IntegerField(help_text="关闭的组件个数")
    started_service_num = serializers.IntegerField(help_text="启动的组件个数")


class PerformanceOverviewSeralizer(serializers.Serializer):
    cpu_use_sum = serializers.IntegerField(help_text="CPU使用总量")
    memory_use_sum = serializers.IntegerField(help_text="内存使用总量")
    disk_use_sum = serializers.IntegerField(help_text="磁盘使用总量")
    node_number = serializers.IntegerField(help_text="节点总数")
    service_number = serializers.IntegerField(help_text="组件总数")


class RegionMonitorOverviewSeralizer(serializers.Serializer):
    region_alias = serializers.CharField(help_text="集群名", max_length=64)
    node_name = serializers.CharField(help_text="节点名", max_length=64)
    exception_type = serializers.CharField(help_text="异常类型", max_length=64)
    reason = serializers.CharField(help_text="异常原因")


class InstancesMonitorOverviewSeralizer(serializers.Serializer):
    instance_status = serializers.CharField(help_text="实例状态", max_length=64)
    team_alias = serializers.CharField(help_text="团队名", max_length=64)
    app_name = serializers.CharField(help_text="应用名", max_length=64)
    component_name = serializers.CharField(help_text="组件名", max_length=64)
    disk_usage = serializers.IntegerField(help_text="磁盘使用量")
    memory_usage = serializers.IntegerField(help_text="内存使用量")
    cpu_usage = serializers.IntegerField(help_text="CPU使用量")


class ComponentMemoryOverviewSeralizer(serializers.Serializer):
    nodes = serializers.ListField(help_text="组件内存级别")
    links = serializers.ListField(help_text="组件内存关系")
