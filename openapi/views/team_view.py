# -*- coding: utf-8 -*-
# creater by: barnett
import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response

from backends.services.exceptions import UserNotExistError
from console.services.enterprise_services import enterprise_services
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.user_services import user_services
from openapi.serializer.team_serializer import CreateTeamReqSerializer
from openapi.serializer.team_serializer import CreateTeamUserReqSerializer
from openapi.serializer.team_serializer import ListTeamRespSerializer
from openapi.serializer.team_serializer import RoleInfoRespSerializer
from openapi.serializer.team_serializer import TeamInfoSerializer
from openapi.serializer.team_serializer import UpdateTeamInfoReqSerializer
from openapi.serializer.user_serializer import ListTeamUsersRespSerializer
from openapi.views.base import BaseOpenAPIView
from openapi.views.base import ListAPIView
from www.models.main import PermRelTenant
from www.models.main import Tenants

logger = logging.getLogger("default")


class ListTeamInfo(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取团队列表",
        manual_parameters=[
            openapi.Parameter("eid", openapi.IN_QUERY, description="企业ID", type=openapi.TYPE_STRING),
            openapi.Parameter("query", openapi.IN_QUERY, description="团队名称搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: ListTeamRespSerializer()},
        tags=['openapi-team'],
    )
    def get(self, req, *args, **kwargs):
        eid = req.GET.get("eid", "")
        if not eid:
            raise serializers.ValidationError("缺少'eid'字段")
        query = req.GET.get("query", "")
        try:
            page = int(req.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(req.GET.get("page_size", 10))
        except ValueError:
            page_size = 10

        data, total = team_services.list_teams_v2(
            eid, query=query, page=page, page_size=page_size)
        result = {"tenants": data, "total": total}
        serializer = ListTeamRespSerializer(data=result)
        serializer.is_valid(raise_exception=True)
        return Response(result, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="add team",
        request_body=CreateTeamReqSerializer(),
        responses={
            status.HTTP_201_CREATED: None,
            status.HTTP_500_INTERNAL_SERVER_ERROR: None,
            status.HTTP_400_BAD_REQUEST: None,
        },
        tags=['openapi-team'],
    )
    def post(self, request):
        serializer = CreateTeamReqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team_data = serializer.data

        en = enterprise_services.get_enterprise_by_enterprise_id(request.data.get("enterprise_id"))
        if not en:
            raise serializers.ValidationError("指定企业不存在")
        region = None
        if team_data.get("region_name", None):
            region = region_services.get_region_by_region_name(team_data.get("region_name"))
            if not region:
                raise serializers.ValidationError("指定数据中心不存在")
        try:
            user = user_services.get_user_by_user_id(team_data.get("user_id", 0))
        except UserNotExistError:
            user = request.user
        code, msg, team = team_services.create_team(user, en, team_alias=team_data["tenant_name"])
        if code == 200 and region:
            code, message, bean = region_services.create_tenant_on_region(team.tenant_name, region.region_name)
            if code != 200:
                team.delete()
                raise serializers.ValidationError("数据中心创建团队时发生错误")
            return Response(None, status=status.HTTP_201_CREATED)
        elif code == 200:
            return Response(None, status=status.HTTP_201_CREATED)
        else:
            return Response(None, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TeamInfo(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="获取团队",
        responses={
            status.HTTP_200_OK: TeamInfoSerializer(),
            status.HTTP_404_NOT_FOUND: None,
            status.HTTP_500_INTERNAL_SERVER_ERROR: None
        },
        tags=['openapi-team'],
    )
    def get(self, request, team_id):
        queryset = team_services.get_team_by_team_id(team_id)
        if queryset is None:
            return Response(None, status.HTTP_404_NOT_FOUND)
        serializer = TeamInfoSerializer(queryset)
        return Response(serializer.data, status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="删除团队",
        responses={
            status.HTTP_200_OK: None,
            status.HTTP_404_NOT_FOUND: None,
            status.HTTP_500_INTERNAL_SERVER_ERROR: None
        },
        tags=['openapi-team'],
    )
    def delete(self, req, team_id,  *args, **kwargs):
        try:
            service_count = team_services.count_by_tenant_id(tenant_id=team_id)
            if service_count >= 1:
                raise serializers.ValidationError("当前团队内有应用,不可以删除")

            res = team_services.delete_by_tenant_id(tenant_id=team_id)
            if res:
                return Response(None, status.HTTP_200_OK)
            else:
                return Response(None, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Tenants.DoesNotExist as e:
            logger.exception("failed to delete tenant: {}".format(e.message))
            return Response(None, status=status.HTTP_404_NOT_FOUND)
        except PermRelTenant as e:
            logger.exception("failed to delete tenant: {}".format(e.message))
            return Response(None, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="更新团队信息",
        request_body=UpdateTeamInfoReqSerializer,
        responses={
            status.HTTP_200_OK: None,
            status.HTTP_404_NOT_FOUND: None,
        },
        tags=['openapi-team'],
    )
    def put(self, req, team_id, *args, **kwargs):
        serializer = UpdateTeamInfoReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)

        if req.data.get("enterprise_id", ""):
            ent = enterprise_services.get_enterprise_by_enterprise_id()
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


class ListTeamUsersInfo(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取团队用户列表",
        manual_parameters=[
            openapi.Parameter("query", openapi.IN_QUERY, description="用户名、邮箱、手机号搜索", type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: ListTeamUsersRespSerializer()},
        tags=['openapi-team'],
    )
    def get(self, req, team_id, *args, **kwargs):
        try:
            page = int(req.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(req.GET.get("page_size", 10))
        except ValueError:
            page_size = 10
        query = req.GET.get("query", "")
        users, total = user_services.list_users_by_tenant_id(
            tenant_id=team_id, page=page, size=page_size, query=query)
        serializer = ListTeamUsersRespSerializer(data={"users": users, "total": total})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status.HTTP_200_OK)


class TeamUserInfoView(BaseOpenAPIView):
    @swagger_auto_schema(
        operation_description="将用户从团队中移除",
        responses={
            status.HTTP_200_OK: None,
            status.HTTP_404_NOT_FOUND: None,
            status.HTTP_500_INTERNAL_SERVER_ERROR: None
        },
        tags=['openapi-team'],
    )
    def delete(self, req, team_id, user_id):
        if req.user.user_id == user_id:
            raise serializers.ValidationError("不能删除自己", status.HTTP_400_BAD_REQUEST)
        role_name = user_services.get_user_role_names(team_id, user_id)
        if "owner" in role_name:
            raise serializers.ValidationError("不能删除团队拥有者！", status.HTTP_400_BAD_REQUEST)
        try:
            user_services.batch_delete_users(team_id, [user_id])
            return Response(None, status.HTTP_200_OK)
        except Tenants.DoesNotExist:
            return Response(None, status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="add team user",
        request_body=CreateTeamUserReqSerializer(),
        responses={
            status.HTTP_201_CREATED: None,
            status.HTTP_500_INTERNAL_SERVER_ERROR: None,
            status.HTTP_400_BAD_REQUEST: None,
        },
        tags=['openapi-team'],
    )
    def post(self, req, team_id, user_id):
        serializer = CreateTeamUserReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)

        role_ids = req.data["role_ids"].replace(" ", "").split(",")
        roleids = team_services.get_all_team_role_id(tenant_name=team_id)
        for role_id in role_ids:
            if int(role_id) not in roleids:
                raise serializers.ValidationError("角色{}不存在".format(role_id), status.HTTP_404_NOT_FOUND)

        flag = team_services.user_is_exist_in_team(user_list=[user_id], tenant_name=team_id)
        if flag:
            user_obj = user_services.get_user_by_user_id(user_id=user_id)
            raise serializers.ValidationError("用户{}已经存在".format(user_obj.nick_name), status.HTTP_400_BAD_REQUEST)

        team = team_services.get_team_by_team_id(team_id)
        team_services.add_user_role_to_team(tenant=team, user_ids=[user_id], role_ids=role_ids)

        return Response(None, status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="update team user",
        request_body=CreateTeamUserReqSerializer(),
        responses={
            status.HTTP_200_OK: None,
            status.HTTP_500_INTERNAL_SERVER_ERROR: None,
            status.HTTP_400_BAD_REQUEST: None,
            status.HTTP_404_NOT_FOUND: None,
        },
        tags=['openapi-team'],
    )
    def put(self, req, team_id, user_id):
        if req.user.user_id == user_id:
            raise serializers.ValidationError("您不能修改自己的权限!", status=status.HTTP_400_BAD_REQUEST)

        serializer = CreateTeamUserReqSerializer(data=req.data)
        serializer.is_valid(raise_exception=True)

        role_ids = req.data["role_ids"].replace(" ", "").split(",")
        roleids = team_services.get_all_team_role_id(tenant_name=team_id)
        for role_id in role_ids:
            if int(role_id) not in roleids:
                raise serializers.ValidationError("角色{}不存在".format(role_id), status.HTTP_404_NOT_FOUND)

        try:
            role_name = user_services.get_user_role_names(team_id, user_id)
        except UserNotExistError:
            raise serializers.ValidationError("用户{}不存在于团队{}中".format(user_id, team_id),
                                              status.HTTP_404_NOT_FOUND)
        if "owner" in role_name:
            raise serializers.ValidationError("不能修改团队拥有者的权限！", status.HTTP_400_BAD_REQUEST)

        team_services.change_tenant_role(user_id=user_id, tenant_name=team_id, role_id_list=role_ids)

        return Response(None, status.HTTP_200_OK)


class ListUserRolesView(ListAPIView):
    @swagger_auto_schema(
        operation_description="获取用户角色列表",
        manual_parameters=[
            openapi.Parameter("page", openapi.IN_QUERY, description="页码", type=openapi.TYPE_STRING),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_STRING),
        ],
        responses={200: RoleInfoRespSerializer(many=True)},
        tags=['openapi-user-role'],
    )
    def get(self, req, team_id, *args, **kwargs):
        try:
            page = int(req.GET.get("page", 1))
        except ValueError:
            page = 1
        try:
            page_size = int(req.GET.get("page_size", 10))
        except ValueError:
            page_size = 10

        role_list = team_services.get_tenant_roles(team_id, page, page_size)
        serializer = RoleInfoRespSerializer(data=role_list, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status.HTTP_200_OK)
