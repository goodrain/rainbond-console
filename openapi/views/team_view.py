# -*- coding: utf-8 -*-
# creater by: barnett
import json
import logging
import time

from console.exception.exceptions import UserNotExistError
from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig, RainbondCenterApp, RainbondCenterAppVersion
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.user_repo import user_repo
from console.services.app_actions import event_service
from console.services.app_config import domain_service
from console.services.enterprise_services import enterprise_services
from console.services.exception import ErrTenantRegionNotFound
from console.services.perm_services import user_kind_role_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.user_services import user_services
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.serializer.base_serializer import FailSerializer
from openapi.serializer.team_serializer import (
    CreateTeamReqSerializer, CreateTeamUserReqSerializer, ListRegionTeamServicesSerializer, ListTeamRegionsRespSerializer,
    ListTeamRespSerializer, TeamAppsResourceSerializer, TeamBaseInfoSerializer, TeamCertificatesCSerializer,
    TeamCertificatesLSerializer, TeamCertificatesRSerializer, TeamEventLogSerializer, TeamInfoSerializer,
    TeamOverviewSerializer, TeamRegionReqSerializer, TenantRegionListSerializer, UpdateTeamInfoReqSerializer)
from openapi.serializer.utils import pagination
from openapi.views.base import (BaseOpenAPIView, TeamAPIView, TeamNoRegionAPIView)
from openapi.views.exceptions import ErrRegionNotFound, ErrTeamNotFound
from rest_framework import exceptions, serializers, status
from rest_framework.response import Response
from www.models.main import PermRelTenant, TenantRegionInfo, Tenants
from www.utils.crypt import make_uuid, make_uuid3

logger = logging.getLogger("default")


class EntAppModelView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="创建或更新应用模板",
        responses={200: None},
        tags=['openapi-entreprise'],
    )
    def post(self, request):
        try:
            # 获取请求参数
            app_name = request.data.get("app_name")
            apps = request.data.get("apps")
            version = request.data.get("version")
            app_version_info = request.data.get("app_version_info", "")
            arch = request.data.get("arch", "amd64")

            if not app_name or not apps or not version:
                return Response({"msg": "参数不完整"}, status=status.HTTP_400_BAD_REQUEST)

            # 生成应用ID
            app_id = make_uuid3(app_name)

            # 更新app_template中的group_key
            if isinstance(apps, str):
                apps = json.loads(apps)

            app_template = {}
            app_template["apps"] = apps
            app_template["group_key"] = app_id
            app_template["template_version"] = "v2"
            app_template["group_name"] = app_name
            app_template["group_version"] = version
            # 获取第一条记录的enterprise_id
            enterprise_id = self.enterprise.enterprise_id

            # 检查应用是否已存在
            rainbond_app = rainbond_app_repo.get_rainbond_app_by_app_id(app_id)
            if not rainbond_app:
                # 创建应用
                center_app = {
                    "app_id": app_id,
                    "app_name": app_name,
                    "create_team": "",
                    "source": "openapi",
                    "scope": "enterprise",
                    "pic": "",
                    "describe": "",
                    "enterprise_id": enterprise_id,
                    "details": "",
                    "arch": arch,
                    "is_version": True,
                }
                rainbond_app = RainbondCenterApp(**center_app)
                rainbond_app.save()

            # 检查版本是否存在
            try:
                app_version = RainbondCenterAppVersion.objects.get(app_id=app_id, version=version)
                # 版本存在，更新版本信息
                app_version.app_version_info = app_version_info
                app_version.app_template = json.dumps(app_template)
                app_version.arch = arch
                app_version.upgrade_time = time.time()
                app_version.save()
                msg = "版本已更新"
            except RainbondCenterAppVersion.DoesNotExist:
                # 版本不存在，创建新版本
                app_version = RainbondCenterAppVersion(
                    app_id=app_id,
                    version=version,
                    version_alias="",
                    app_version_info=app_version_info,
                    template_type="",
                    record_id=0,
                    share_user=1,
                    share_team="",
                    source="openapi",
                    scope="enterprise",
                    app_template=json.dumps(app_template),
                    template_version="v2",
                    enterprise_id=enterprise_id,
                    arch=arch,
                    is_complete=True,
                    upgrade_time=time.time()
                )
                app_version.save()
                msg = "版本已创建"

            return Response({"msg": msg, "app_id": app_id}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(e)
            return Response({"msg": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListTeamInfo(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取用户所在团队列表",
        manual_parameters=[
            openapi.Parameter("query", openapi.IN_QUERY, description="团队名称搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: ListTeamRespSerializer()},
        tags=['openapi-team'],
    )
    def get(self, req, *args, **kwargs):
        query = req.GET.get("query", "")
        try:
            page = int(req.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(req.GET.get("page_size", 10))
        except ValueError:
            page_size = 10
        tenants, total = team_services.list_teams_by_user_id(
            eid=self.enterprise.enterprise_id, user_id=req.user.user_id, query=query, page=page, page_size=page_size)
        result = {"tenants": tenants, "total": total, "page": page, "page_size": page_size}
        serializer = ListTeamRespSerializer(data=result)
        return Response(serializer.initial_data, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="add team",
        request_body=CreateTeamReqSerializer(),
        responses={
            status.HTTP_201_CREATED: TeamBaseInfoSerializer(),
        },
        tags=['openapi-team'],
    )
    def post(self, request):
        serializer = CreateTeamReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team_data = serializer.data
        team_data["creater"] = self.user.user_id
        team_data["enterprise_id"] = self.enterprise.enterprise_id

        en = self.enterprise
        if not en:
            raise serializers.ValidationError("指定企业不存在")
        region = None
        if team_data.get("region", None):
            region = region_services.get_region_by_region_name(team_data.get("region"))
            if not region:
                raise ErrRegionNotFound
        try:
            user = user_services.get_user_by_user_id(team_data.get("creater", 0))
        except UserNotExistError:
            user = request.user
        team = team_services.create_team(user, en, team_alias=team_data["tenant_name"])
        if region:
            region_services.create_tenant_on_region(self.enterprise.enterprise_id, team.tenant_name, region.region_name,
                                                    team.namespace)
        re = TeamBaseInfoSerializer(team)
        return Response(re.data, status=status.HTTP_201_CREATED)


class TeamInfo(TeamNoRegionAPIView):
    @swagger_auto_schema(
        operation_description="获取团队",
        responses={
            status.HTTP_200_OK: TeamInfoSerializer(),
        },
        tags=['openapi-team'],
    )
    def get(self, request, team_id, *args, **kwargs):
        try:
            queryset = team_services.get_team_by_team_id(team_id.strip())
            serializer = TeamInfoSerializer(queryset)
            return Response(serializer.data, status.HTTP_200_OK)
        except Tenants.DoesNotExist:
            raise ErrTeamNotFound

    @swagger_auto_schema(
        operation_description="删除团队",
        responses={},
        tags=['openapi-team'],
    )
    def delete(self, req, team_id, *args, **kwargs):
        try:
            team_services.delete_by_tenant_id(self.user, self.team)
            return Response(None, status.HTTP_200_OK)
        except Tenants.DoesNotExist as e:
            logger.exception("failed to delete tenant: {}".format(e.message))
            return Response(None, status=status.HTTP_404_NOT_FOUND)
        except PermRelTenant as e:
            logger.exception("failed to delete tenant: {}".format(e.message))
            return Response(None, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="更新团队信息",
        request_body=UpdateTeamInfoReqSerializer,
        responses={},
        tags=['openapi-team'],
    )
    def put(self, req, team_id, *args, **kwargs):
        serializer = UpdateTeamInfoReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)

        if req.data.get("enterprise_id", ""):
            ent = enterprise_services.get_enterprise_by_enterprise_id(req.data["enterprise_id"])
            if not ent:
                raise serializers.ValidationError("指定企业不存在", status.HTTP_404_NOT_FOUND)
        if req.data.get("creator", 0):
            try:
                ent = user_services.get_user_by_user_id(req.data.get("creator"))
            except UserNotExistError:
                raise serializers.ValidationError("指定用户不存在", status.HTTP_404_NOT_FOUND)

        try:
            team_services.update(team_id, req.data)
            return Response(None, status.HTTP_200_OK)
        except Tenants.DoesNotExist:
            return Response(None, status.HTTP_404_NOT_FOUND)


class TeamUserInfoView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="将用户从团队中移除",
        responses={
            status.HTTP_404_NOT_FOUND: FailSerializer(),
        },
        tags=['openapi-team'],
    )
    def delete(self, req, team_id, user_id):
        if req.user.user_id == user_id:
            raise serializers.ValidationError("不能删除自己", status.HTTP_400_BAD_REQUEST)

        try:
            user_services.get_user_by_tenant_id(team_id, user_id)
            user_services.batch_delete_users(team_id, [user_id])
            return Response(None, status.HTTP_200_OK)
        except UserNotExistError as e:
            return Response({"msg": e.message}, status.HTTP_404_NOT_FOUND)
        except Tenants.DoesNotExist:
            return Response({"msg": "团队不存在"}, status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="add team user",
        request_body=CreateTeamUserReqSerializer(),
        responses={},
        tags=['openapi-team'],
    )
    def post(self, req, team_id, user_id):
        serializer = CreateTeamUserReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)
        role_ids = req.data["role_ids"].replace(" ", "").split(",")
        team_services.add_user_role_to_team(tenant=self.team, user_ids=[user_id], role_ids=role_ids)
        return Response(None, status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="update team user",
        request_body=CreateTeamUserReqSerializer(),
        responses={
            status.HTTP_404_NOT_FOUND: FailSerializer(),
        },
        tags=['openapi-team'],
    )
    # TODO 修改权限控制
    def put(self, req, team_id, user_id):
        if req.user.user_id == user_id:
            raise serializers.ValidationError("您不能修改自己的权限!", status.HTTP_400_BAD_REQUEST)

        serializer = CreateTeamUserReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)

        role_ids = req.data["role_ids"].replace(" ", "").split(",")
        user = user_repo.get_by_user_id(user_id)
        user_kind_role_service.update_user_roles(kind="team", kind_id=self.team.tenant_id, user=user, role_ids=role_ids)
        return Response(None, status.HTTP_200_OK)


class ListRegionsView(TeamNoRegionAPIView):
    @swagger_auto_schema(
        operation_description="获取团队开通的数据中心列表",
        manual_parameters=[
            openapi.Parameter("query", openapi.IN_QUERY, description="根据数据中心名称搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: ListTeamRegionsRespSerializer()},
        tags=['openapi-team-region'],
    )
    def get(self, req, team_id, *args, **kwargs):
        query = req.GET.get("query", "")
        try:
            page = int(req.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(req.GET.get("page_size", 10))
        except ValueError:
            page_size = 10

        regions, total = region_services.list_by_tenant_id(self.team.tenant_id, query, page, page_size)

        data = {"regions": regions, "total": total}

        serializer = ListTeamRegionsRespSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="开通数据中心",
        request_body=TeamRegionReqSerializer(),
        responses={
            status.HTTP_201_CREATED: TeamBaseInfoSerializer(),
        },
        tags=['openapi-team-region'],
    )
    def post(self, request, team_id, *args, **kwargs):
        serializer = TeamRegionReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team_data = serializer.data

        region = None
        if team_data.get("region", None):
            region = region_services.get_region_by_region_name(team_data.get("region"))
            if not region:
                raise ErrRegionNotFound
        team = team_services.get_team_by_team_id(team_id)
        region_services.create_tenant_on_region(self.enterprise.enterprise_id, team.tenant_name, region.region_name,
                                                team.namespace)
        re = TeamBaseInfoSerializer(team)
        return Response(re.data, status=status.HTTP_201_CREATED)


class TeamRegionView(TeamNoRegionAPIView):
    @swagger_auto_schema(
        operation_description="关闭数据中心",
        responses={},
        tags=['openapi-team-region'],
    )
    def delete(self, request, team_id):
        serializer = TeamRegionReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team_data = serializer.data
        region = team_data.get("region", None)
        if region:
            region = region_services.get_region_by_region_name(region)
            if not region:
                raise serializers.ValidationError("指定数据中心不存在")
        code, msg, team = team_services.delete_team_region(self.team.tenant_id, region)
        if code == 200:
            re = TeamBaseInfoSerializer(team)
            return Response(re.data, status=status.HTTP_200_OK)
        else:
            return Response(None, status=status.HTTP_404_NOT_FOUND)


class ListRegionTeamServicesView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取团队下指定数据中心组件信息",
        manual_parameters=[
            openapi.Parameter("eid", openapi.IN_QUERY, description="根据数据中心名称搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("team_name", openapi.IN_QUERY, description="根据数据中心名称搜索", type=openapi.TYPE_STRING),
        ],
        responses={200: ListRegionTeamServicesSerializer()},
        tags=['openapi-team'],
    )
    def get(self, req, team_id, region_name, *args, **kwargs):
        services = region_services.list_services_by_tenant_name(region_name, team_id)
        total = len(services)
        data = {"services": services, "total": total}
        serializer = ListRegionTeamServicesSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status.HTTP_200_OK)

    def delete(self, request, team_id, region_name):
        try:
            team_services.delete_team_region(team_id, region_name)
        except (Tenants.DoesNotExist, RegionConfig.DoesNotExist, ErrTenantRegionNotFound):
            raise exceptions.NotFound()

        return Response(None, status=status.HTTP_200_OK)


class TeamCertificatesLCView(TeamNoRegionAPIView):
    @swagger_auto_schema(
        operation_description="获取团队下证书列表",
        manual_parameters=[
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_NUMBER),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_NUMBER),
        ],
        responses={200: TeamCertificatesLSerializer()},
        tags=['openapi-team'],
    )
    def get(self, request, team_id, *args, **kwargs):
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        certificates, nums = domain_service.get_certificate(self.team, page, page_size)
        data = pagination(certificates, nums, page, page_size)
        serializer = TeamCertificatesLSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="添加证书",
        request_body=TeamCertificatesCSerializer(),
        responses={
            status.HTTP_200_OK: TeamCertificatesRSerializer(),
        },
        tags=['openapi-team'],
    )
    def post(self, request, team_id, *args, **kwargs):
        serializer = TeamCertificatesCSerializer(data=request.data)
        serializer.is_valid()
        data = serializer.data
        data.update({"tenant": self.team, "certificate_id": make_uuid(), "region": None})
        new_c = domain_service.add_certificate(**data)
        rst = new_c.to_dict()
        rst["id"] = rst["ID"]
        if isinstance(rst["certificate"], bytes):
            rst["certificate"] = rst["certificate"].decode()
        rst_serializer = TeamCertificatesRSerializer(data=rst)
        rst_serializer.is_valid(raise_exception=True)
        return Response(rst_serializer.data, status=status.HTTP_200_OK)


class TeamCertificatesRUDView(TeamNoRegionAPIView):
    @swagger_auto_schema(
        operation_description="获取团队下证书列表",
        responses={200: TeamCertificatesRSerializer()},
        tags=['openapi-team'],
    )
    def get(self, request, team_id, certificate_id, *args, **kwargs):
        code, msg, certificate = domain_service.get_certificate_by_pk(certificate_id)
        if code != 200:
            raise ServiceHandleException(msg=None, status_code=code, msg_show=msg)
        serializer = TeamCertificatesRSerializer(data=certificate)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="更新证书",
        request_body=TeamCertificatesCSerializer(),
        responses={
            status.HTTP_200_OK: TeamCertificatesRSerializer(),
        },
        tags=['openapi-team'],
    )
    def put(self, request, team_id, certificate_id, *args, **kwargs):
        serializer = TeamCertificatesCSerializer(data=request.data)

        serializer.is_valid()
        data = serializer.data
        data.update({"tenant": self.team, "certificate_id": certificate_id, "region": None})
        new_c = domain_service.update_certificate(**data)
        rst = new_c.to_dict()
        rst["id"] = rst["ID"]
        if isinstance(rst["certificate"], bytes):
            rst["certificate"] = rst["certificate"].decode()
        rst_serializer = TeamCertificatesRSerializer(data=rst)
        rst_serializer.is_valid(raise_exception=True)
        return Response(rst_serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除证书",
        responses={},
        tags=['openapi-team'],
    )
    def delete(self, request, team_id, certificate_id, *args, **kwargs):
        domain_service.delete_certificate_by_pk(None, self.team, certificate_id)
        return Response(data=None, status=status.HTTP_200_OK)


class TeamAppsResourceView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="获取团队资源统计",
        responses={
            status.HTTP_200_OK: TeamAppsResourceSerializer(),
        },
        tags=['openapi-team'],
    )
    def get(self, request, team_id, region_name, *args, **kwargs):
        data = team_services.get_tenant_resource(self.team, self.region_name)
        serializer = TeamAppsResourceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=200)


class TeamOverviewView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="团队统计",
        responses={
            status.HTTP_200_OK: TeamAppsResourceSerializer(),
        },
        tags=['openapi-team'],
    )
    def get(self, request, team_id, region_name, *args, **kwargs):
        data = team_services.overview(self.team, self.region_name)
        serializer = TeamOverviewSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=200)


class TeamsResourceView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="批量获取团队资源统计列表",
        request_body=TenantRegionListSerializer(many=True),
        responses={
            status.HTTP_200_OK: TeamAppsResourceSerializer(many=True),
        },
        tags=['openapi-team'],
    )
    def post(self, request, *args, **kwargs):
        resources = []
        serializer = TenantRegionListSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        for tenant in serializer.data:
            team = None
            region_name = tenant.get("region_name")
            tenant_id = tenant.get("tenant_id")
            team_region = TenantRegionInfo.objects.filter(
                tenant_id=tenant_id, enterprise_id=self.enterprise.enterprise_id, region_name=region_name).first()
            if team_region:
                team = team_services.get_team_by_team_id(tenant_id)
            data = team_services.get_tenant_resource(team, region_name)
            if data:
                resources.append(data)
        serializer = TeamAppsResourceSerializer(data=resources, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=200)


class TeamEventLogView(TeamAPIView):
    @swagger_auto_schema(
        operation_description="获取事件日志",
        manual_parameters=[
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队ID、名称", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="数据中心名称", type=openapi.TYPE_STRING),
            openapi.Parameter("event_id", openapi.IN_PATH, description="事件ID", type=openapi.TYPE_STRING),
        ],
        responses={
            status.HTTP_200_OK: TeamEventLogSerializer(),
        },
        tags=['openapi-team'],
    )
    def get(self, request, team_id, region_name, event_id, *args, **kwargs):
        log_content = event_service.get_event_log(self.team, region_name, event_id)
        re = TeamEventLogSerializer(data={"logs": log_content})
        re.is_valid(raise_exception=True)
        return Response(re.data, status=200)
