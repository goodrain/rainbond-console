# -*- coding: utf-8 -*-
# creater by: barnett
from rest_framework import serializers

from openapi.serializer.utils import DateCharField
from openapi.serializer.role_serializer import RoleInfoSerializer


class TeamInfoPostSerializer(serializers.Serializer):
    tenant_name = serializers.CharField(max_length=24, help_text="团队名称")
    team_owner = serializers.IntegerField(help_text="团队拥有者用户ID")


class TeamBaseInfoSerializer(serializers.Serializer):
    tenant_id = serializers.CharField(max_length=64, help_text="租户id")
    tenant_name = serializers.CharField(max_length=64, help_text="租户名称")
    region = serializers.CharField(max_length=64, default='', help_text="区域中心,弃用")
    is_active = serializers.BooleanField(default=True, help_text="激活状态")
    create_time = DateCharField(max_length=64, help_text="创建时间")
    creater = serializers.IntegerField(help_text="租户创建者", default=0)
    limit_memory = serializers.IntegerField(help_text="内存大小单位（M）", default=1024)
    update_time = DateCharField(max_length=64, help_text="更新时间")
    expired_time = DateCharField(max_length=64, help_text="过期时间")
    tenant_alias = serializers.CharField(max_length=64, allow_null=True, default='', help_text="团队别名")
    enterprise_id = serializers.CharField(max_length=32, allow_null=True, default='', help_text="企业id")


class TeamInfoSerializer(serializers.Serializer):
    tenant_id = serializers.CharField(max_length=32, help_text="团队ID")
    tenant_name = serializers.CharField(max_length=24, help_text="团队名称")
    tenant_alias = serializers.CharField(max_length=24, help_text="团队别名")
    enterprise_id = serializers.CharField(max_length=32, help_text="企业ID")
    is_active = serializers.BooleanField(help_text="是否激活", required=False)
    create_time = DateCharField(help_text="创建时间", required=False)
    creater = serializers.CharField(help_text="团队拥有者用户", required=False)
    service_num = serializers.IntegerField(help_text="团队的组件数量", required=False)
    region_num = serializers.IntegerField(help_text="团队开通的数据中心数量", required=False)
    role_infos = RoleInfoSerializer(many=True, help_text="用户在团队中拥有的角色", required=False)


class ListTeamRespSerializer(serializers.Serializer):
    total = serializers.IntegerField(required=False)
    tenants = TeamInfoSerializer(many=True)


class CreateTeamReqSerializer(serializers.Serializer):
    tenant_name = serializers.CharField(max_length=24, help_text="团队名称")
    region = serializers.CharField(max_length=24, help_text="默认开通的数据中心，未指定则不开通", required=False)


class TeamRegionReqSerializer(serializers.Serializer):
    region = serializers.CharField(max_length=24, help_text="数据中心名称", required=False)


class UpdateTeamInfoReqSerializer(serializers.Serializer):
    region = serializers.CharField(max_length=24, help_text="数据中心名称", required=False)
    is_active = serializers.BooleanField(help_text="是否激活", required=False)
    creater = serializers.IntegerField(help_text="团队拥有者用户ID", required=False)
    tenant_alias = serializers.CharField(max_length=24, help_text="团队别名", required=False)
    enterprise_id = serializers.CharField(max_length=32, help_text="企业ID", required=False)


class RoleInfoRespSerializer(serializers.Serializer):
    role_id = serializers.IntegerField(help_text="角色ID")
    role_name = serializers.CharField(max_length=32, help_text="角色名称")


class CreateTeamUserReqSerializer(serializers.Serializer):
    role_ids = serializers.CharField(max_length=255, help_text="角色ID列表")

    def validate_role_ids(self, role_ids):
        role_ids = role_ids.replace(" ", "")
        for role_id in role_ids.split(","):
            try:
                int(role_id)
            except ValueError:
                raise serializers.ValidationError("角色ID格式不正确")


class TeamRegionsRespSerializer(serializers.Serializer):
    region_id = serializers.CharField(max_length=36, help_text="region id")
    region_name = serializers.CharField(max_length=32, help_text="数据中心名称")
    region_alias = serializers.CharField(max_length=32, help_text="数据中心别名")
    tenant_name = serializers.CharField(max_length=32, help_text="租户名称")
    url = serializers.CharField(max_length=256, help_text="数据中心API url")
    wsurl = serializers.CharField(max_length=256, help_text="数据中心Websocket url")
    httpdomain = serializers.CharField(max_length=256, help_text="数据中心http应用访问根域名")
    tcpdomain = serializers.CharField(max_length=256, help_text="数据中心tcp应用访问根域名")
    token = serializers.CharField(max_length=127, allow_null=True, allow_blank=True, default="", help_text="数据中心token")
    status = serializers.CharField(max_length=2, help_text="数据中心状态 0：编辑中 1:启用 2：停用 3:维护中")
    desc = serializers.CharField(max_length=128, allow_blank=True, help_text="数据中心描述")
    scope = serializers.CharField(max_length=10, default="private", help_text="数据中心范围 private|public")


class ListTeamRegionsRespSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    regions = TeamRegionsRespSerializer(many=True)


class TeamServicesRespSerializer(serializers.Serializer):
    update_time = DateCharField(max_length=64, help_text="更新日期")
    deploy_version = serializers.CharField(max_length=32, allow_blank=True, allow_null=True, help_text="组件版本")
    service_alias = serializers.CharField(max_length=32, allow_blank=True, allow_null=True, help_text="组件昵称")
    service_cname = serializers.CharField(max_length=255, allow_blank=True, allow_null=True, help_text="组件名称")
    group_name = serializers.CharField(max_length=255, allow_blank=True, allow_null=True, help_text="应用名称")
    service_type = serializers.CharField(max_length=255, allow_blank=True, allow_null=True, help_text="组件类型")
    service_id = serializers.CharField(max_length=64, allow_blank=True, allow_null=True, help_text="组件id")
    group_id = serializers.CharField(max_length=32, allow_blank=True, allow_null=True, help_text="组id")
    tenant_name = serializers.CharField(max_length=32, allow_blank=True, allow_null=True, help_text="租户名称")
    region_id = serializers.CharField(max_length=36, allow_blank=True, allow_null=True, help_text="数据中心id")


class ListRegionTeamServicesSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    services = TeamServicesRespSerializer(many=True)


class CertificatesRSerializer(serializers.Serializer):
    has_expired = serializers.BooleanField(help_text="是否过期")
    issued_to = serializers.ListField(help_text="域名列表")
    alias = serializers.CharField(max_length=64, help_text="证书名称")
    certificate_type = serializers.CharField(max_length=32, help_text="证书类型")
    end_data = serializers.CharField(max_length=64, help_text="过期时间")
    id = serializers.IntegerField(help_text="id")
    issued_by = serializers.CharField(max_length=32, help_text="证书来源")


class TeamCertificatesLSerializer(serializers.Serializer):
    list = CertificatesRSerializer(many=True)
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()


class TeamCertificatesCSerializer(serializers.Serializer):
    alias = serializers.CharField(max_length=64, help_text="证书名称")
    private_key = serializers.CharField(max_length=8192, help_text="证书")
    certificate = serializers.CharField(max_length=8192, help_text="证书key")
    certificate_type = serializers.CharField(max_length=32, help_text="证书类型")


class TeamCertificatesRSerializer(serializers.Serializer):
    alias = serializers.CharField(max_length=64, help_text="证书名称")
    private_key = serializers.CharField(max_length=8192, help_text="证书")
    certificate = serializers.CharField(max_length=8192, help_text="证书key")
    certificate_type = serializers.CharField(max_length=32, help_text="证书类型")
    id = serializers.IntegerField(help_text="id")


class TeamAppsResourceSerializer(serializers.Serializer):
    total_cpu = serializers.IntegerField(help_text="cpu总额", default=0)
    total_memory = serializers.IntegerField(help_text="内存总额", default=0)
    used_cpu = serializers.IntegerField(help_text="占用cpu", default=0)
    used_memory = serializers.IntegerField(help_text="占用内存", default=0)
    used_cpu_percentage = serializers.FloatField(help_text="占用cpu百分比", default=0)
    used_memory_percentage = serializers.FloatField(help_text="占用内存百分比", default=0)
    team_id = serializers.CharField(max_length=64, help_text="团队ID")
    team_name = serializers.CharField(max_length=64, help_text="团队名称")
    team_alias = serializers.CharField(max_length=64, help_text="团队昵称")


class TeamOverviewSerializer(serializers.Serializer):
    total_cpu = serializers.IntegerField(help_text="cpu总额", default=0)
    total_memory = serializers.IntegerField(help_text="内存总额", default=0)
    used_cpu = serializers.IntegerField(help_text="占用cpu", default=0)
    used_memory = serializers.IntegerField(help_text="占用内存", default=0)
    app_nums = serializers.IntegerField(help_text="应用总数", default=0)
    component_nums = serializers.IntegerField(help_text="组件总数", default=0)


class TenantRegionListSerializer(serializers.Serializer):
    tenant_id = serializers.CharField(help_text="租户id")
    region_name = serializers.CharField(help_text="数据中心名称")
