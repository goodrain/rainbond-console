# -*- coding: utf8 -*-
import logging
import re

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Q
from rest_framework.response import Response

from console.exception.exceptions import (NoEnableRegionError, TenantExistError, UserNotExistError)
from console.exception.main import ServiceHandleException
from console.models.main import UserMessage
from console.repositories.app import service_repo
from console.repositories.apply_repo import apply_repo
from console.repositories.enterprise_repo import (enterprise_repo, enterprise_user_perm_repo)
from console.repositories.region_repo import region_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.services.apply_service import apply_service
from console.services.config_service import platform_config_service
from console.services.enterprise_services import \
    enterprise_services as console_enterprise_service
from console.services.enterprise_services import make_uuid
from console.services.perm_services import (role_kind_services, user_kind_role_service)
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.utils.timeutil import time_to_str
from console.views.base import JWTAuthApiView, RegionTenantHeaderView
from goodrain_web.tools import JuncheePaginator
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import Tenants
from www.utils.return_message import error_message, general_message

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


def get_sufix_path(full_url):
    """获取get请求参数路径部分的数据"""
    index = full_url.find("?")
    sufix = ""
    if index != -1:
        sufix = full_url[index:]
    return sufix


class UserFuzSerView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        模糊查询用户
        ---
        parameters:
            - name: query_key
              description: 模糊用户名
              required: true
              type: string
              paramType: query
        """
        query_key = request.GET.get("query_key", None)
        if query_key:
            q_obj = Q(nick_name__icontains=query_key) | Q(email__icontains=query_key)
            users = user_services.get_user_by_filter(args=(q_obj, ))
            user_list = [{
                "nick_name": user_info.nick_name,
                "email": user_info.email,
                "user_id": user_info.user_id
            } for user_info in users]
            result = general_message(200, "query user success", "查询用户成功", list=user_list)
            return Response(result, status=200)
        else:
            result = general_message(200, "query user success", "你没有查询任何用户")
            return Response(result, status=200)


class TeamUserDetaislView(JWTAuthApiView):
    def get(self, request, team_name, user_name, *args, **kwargs):
        """
        用户详情
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: user_name
              description: 用户名
              required: true
              type: string
              paramType: path
        """
        is_team_owner = False
        try:
            team = team_services.get_tenant_by_tenant_name(team_name)
            data = dict()
            data["nick_name"] = self.user.nick_name
            data["email"] = self.user.email
            role_list = user_kind_role_service.get_user_roles(kind="team", kind_id=team.tenant_id, user=self.user)
            data["teams_identity"] = role_list["roles"]
            data["is_enterprise_admin"] = self.is_enterprise_admin
            if team.creater == self.user.user_id:
                is_team_owner = True
            data["is_team_owner"] = is_team_owner
            code = 200
            result = general_message(code, "user details query success.", "用户详情获取成功", bean=data)
            return Response(result, status=code)
        except UserNotExistError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "this user does not exist on this team.", "该用户不存在这个团队")
            return Response(result, status=code)


class AddTeamView(JWTAuthApiView):
    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        """
        新建团队
        ---
        parameters:
            - name: team_alias
              description: 团队名
              required: true
              type: string
              paramType: body
            - name: useable_regions
              description: 可用数据中心 ali-sh,ali-hz
              required: false
              type: string
              paramType: body
        """
        try:
            user = request.user
            team_alias = request.data.get("team_alias", None)
            useable_regions = request.data.get("useable_regions", "")
            regions = []
            if not team_alias:
                result = general_message(400, "failed", "团队名不能为空")
                return Response(result, status=400)
            if useable_regions:
                regions = useable_regions.split(",")
            if Tenants.objects.filter(tenant_alias=team_alias, enterprise_id=user.enterprise_id).exists():
                result = general_message(400, "failed", "该团队名已存在")
                return Response(result, status=400)
            else:
                enterprise = console_enterprise_service.get_enterprise_by_enterprise_id(self.user.enterprise_id)
                if not enterprise:
                    return Response(general_message(500, "user's enterprise is not found", "无企业信息"), status=500)
                team = team_services.create_team(self.user, enterprise, regions, team_alias)
                for r in regions:
                    try:
                        region_services.create_tenant_on_region(enterprise.enterprise_id, team.tenant_name, r)
                    except ServiceHandleException as e:
                        logger.exception(e)
                    except Exception as e:
                        logger.exception(e)
                return Response(general_message(200, "success", "团队添加成功", bean=team.to_dict()))
        except TenantExistError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "team already exists", "该团队已存在")
            return Response(result, status=code)
        except NoEnableRegionError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "no enable region", "无可用数据中心")
            return Response(result, status=code)


class TeamUserView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        """
        获取某团队下的所有用户(每页展示八个用户)
        ---
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: page
              description: 页数
              required: true
              type: string
              paramType: query
        """
        code = 200
        page = request.GET.get("page", 1)
        user_list = team_services.get_tenant_users_by_tenant_name(tenant_name=team_name)
        if not user_list:
            users = []
            total = 0
        else:
            users_list = list()
            for user in user_list:
                # get role list
                role_info_list = user_kind_role_service.get_user_roles(
                    kind="team", kind_id=self.tenant.tenant_id, user=self.user)
                users_list.append({
                    "user_id": user.user_id,
                    "user_name": user.get_name(),
                    "email": user.email,
                    "role_info": role_info_list["roles"]
                })
            paginator = Paginator(users_list, 8)
            total = paginator.count
            try:
                users = paginator.page(page).object_list
            except PageNotAnInteger:
                users = paginator.page(1).object_list
            except EmptyPage:
                users = paginator.page(paginator.num_pages).object_list
        result = general_message(code, "team members query success", "查询成功", list=users, total=total)
        return Response(data=result, status=code)


class NotJoinTeamUserView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 10))
        query = request.GET.get("query")
        tenant = team_repo.get_tenant_by_tenant_name(team_name)
        if not tenant:
            result = general_message(404, "not found", "团队不存在")
            return Response(data=result, status=404)
        enterprise = enterprise_repo.get_enterprise_by_enterprise_id(tenant.enterprise_id)
        user_list = team_services.get_not_join_users(enterprise, tenant, query)
        total = len(user_list)
        data = user_list[(page - 1) * page_size:page * page_size]
        result = general_message(200, None, None, list=data, page=page, page_size=page_size, total=total)
        return Response(data=result, status=200)


class UserDelView(RegionTenantHeaderView):
    def delete(self, request, team_name, *args, **kwargs):
        """
        删除租户内的用户
        (可批量可单个)
        ---
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: user_ids
              description: 用户名 user_id1,user_id2 ...
              required: true
              type: string
              paramType: body
        """
        try:
            user_ids = request.data.get("user_ids", [])
            if not user_ids:
                result = general_message(400, "failed", "删除成员不能为空")
                return Response(result, status=400)

            if request.user.user_id in user_ids:
                result = general_message(400, "failed", "不能删除自己")
                return Response(result, status=400)

            for user_id in user_ids:
                if user_id == self.tenant.creater:
                    result = general_message(400, "failed", "不能删除团队创建者！")
                    return Response(result, status=400)
            try:
                user_services.batch_delete_users(team_name, user_ids)
                result = general_message(200, "delete the success", "删除成功")
            except Tenants.DoesNotExist as e:
                logger.exception(e)
                result = general_message(400, "tenant not exist", "{}团队不存在".format(team_name))
            except Exception as e:
                logger.exception(e)
                result = error_message(e.message)
            return Response(result)
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class TeamNameModView(RegionTenantHeaderView):
    def post(self, request, team_name, *args, **kwargs):
        """
        修改团队名
        ---
        parameters:
            - name: team_name
              description: 旧团队名
              required: true
              type: string
              paramType: path
            - name: new_team_alias
              description: 新团队名
              required: true
              type: string
              paramType: body
        """
        new_team_alias = request.data.get("new_team_alias", "")
        if new_team_alias:
            try:
                code = 200
                team = team_services.update_tenant_alias(tenant_name=team_name, new_team_alias=new_team_alias)
                result = general_message(code, "update success", "团队名修改成功", bean=team.to_dict())
            except Exception as e:
                code = 500
                result = general_message(code, "update failed", "团队名修改失败")
                logger.exception(e)
        else:
            result = general_message(400, "failed", "修改的团队名不能为空")
            code = 400
        return Response(result, status=code)


class TeamDelView(JWTAuthApiView):
    def delete(self, request, team_name, *args, **kwargs):
        """
        删除当前团队
        ---
        parameters:
            - name: team_name
              description: 要删除的团队
              required: true
              type: string
              paramType: path
        """
        tenant = team_services.get_enterprise_tenant_by_tenant_name(
            enterprise_id=self.enterprise.enterprise_id, tenant_name=team_name)
        if tenant is None:
            result = general_message(404, "tenant not exist", "{}团队不存在".format(team_name))
        else:
            team_services.delete_by_tenant_id(self.user, tenant)
            result = general_message(200, "delete a tenant successfully", "删除团队成功")
        return Response(result, status=result["code"])


class TeamExitView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        """
        退出当前团队
        ---
        parameters:
            - name: team_name
              description: 当前所在的团队
              required: true
              type: string
              paramType: path
        """
        if self.is_team_owner:
            return Response(general_message(409, "not allow exit.", "您是当前团队创建者，不能退出此团队"), status=409)
        code, msg_show = team_services.exit_current_team(team_name=team_name, user_id=request.user.user_id)
        if code == 200:
            result = general_message(code=code, msg="success", msg_show=msg_show)
        else:
            result = general_message(code=code, msg="failed", msg_show=msg_show)
        return Response(result, status=result.get("code", 200))


class TeamRegionInitView(JWTAuthApiView):
    def post(self, request):
        """
        初始化团队和数据中心信息
        ---
        parameters:
            - name: team_alias
              description: 团队别名
              required: true
              type: string
              paramType: form
            - name: region_name
              description: 数据中心名称
              required: true
              type: string
              paramType: form
        """
        try:
            team_alias = request.data.get("team_alias", None)
            region_name = request.data.get("region_name", None)
            if not team_alias:
                return Response(general_message(400, "team alias is null", "团队名称不能为空"), status=400)
            if not region_name:
                return Response(general_message(400, "region name is null", "请选择数据中心"), status=400)
            r = re.compile(u'^[a-zA-Z0-9_\\-\u4e00-\u9fa5]+$')
            if not r.match(team_alias.decode("utf-8")):
                return Response(general_message(400, "team alias is not allow", "组名称只支持中英文下划线和中划线"), status=400)
            team = team_services.get_team_by_team_alias(team_alias)
            if team:
                return Response(general_message(409, "region alias is exist", "团队名称{0}已存在".format(team_alias)), status=409)
            region = region_repo.get_region_by_region_name(region_name)
            if not region:
                return Response(general_message(404, "region not exist", "需要开通的数据中心{0}不存在".format(region_name)), status=404)
            enterprise = console_enterprise_service.get_enterprise_by_enterprise_id(self.user.enterprise_id)
            if not enterprise:
                return Response(general_message(404, "user's enterprise is not found", "无法找到用户所在的数据中心"))

            team = team_services.create_team(self.user, enterprise, [region_name], team_alias)
            # 为团队开通默认数据中心并在数据中心创建租户
            tenant_region = region_services.create_tenant_on_region(enterprise.enterprise_id, team.tenant_name, team.region)
            # 公有云，如果没有领过资源包，为开通的数据中心领取免费资源包
            if settings.MODULES.get('SSO_LOGIN'):
                result = region_services.get_enterprise_free_resource(tenant_region.tenant_id, enterprise.enterprise_id,
                                                                      tenant_region.region_name, self.user.nick_name)
                logger.debug("get free resource on [{}] to team {}: {}".format(tenant_region.region_name, team.tenant_name,
                                                                               result))
            self.user.is_active = True
            self.user.save()

            result = general_message(200, "success", "初始化成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class ApplicantsView(RegionTenantHeaderView):
    def get(self, request, team_name, *args, **kwargs):
        """
        初始化团队和数据中心信息
        ---
        parameters:
            - name: team_name
              description: 团队别名
              required: true
              type: string
              paramType: path
            - name: page_num
              description: 页码
              required: false
              type: string
              paramType: query
            - name: page_size
              description: 每页数量
              required: false
              type: string
              paramType: query
        """
        page_num = int(request.GET.get("page_num", 1))
        page_size = int(request.GET.get("page_size", 5))
        rt_list = []
        applicants = apply_repo.get_applicants(team_name=team_name)
        for applicant in applicants:
            is_pass = applicant.is_pass
            if is_pass == 0:
                rt_list.append(applicant.to_dict())
        apc_paginator = JuncheePaginator(rt_list, int(page_size))
        total = apc_paginator.count
        page_aplic = apc_paginator.page(page_num)
        rt_list = [apc for apc in page_aplic]
        # 返回
        result = general_message(200, "success", "查询成功", list=rt_list, total=total)
        return Response(result, status=result["code"])

    def put(self, request, team_name, *args, **kwargs):
        """管理员审核用户"""
        user_id = request.data.get("user_id")
        action = request.data.get("action")
        role_ids = request.data.get("role_ids")
        join = apply_repo.get_applicants_by_id_team_name(user_id=user_id, team_name=team_name)
        if action is True:
            join.update(is_pass=1)
            team = team_repo.get_team_by_team_name(team_name=team_name)
            team_services.add_user_to_team(tenant=team, user_id=user_id, role_ids=role_ids)
            # 发送通知
            info = "同意"
            self.send_user_message_for_apply_info(user_id=user_id, team_name=team.tenant_name, info=info)
            return Response(general_message(200, "join success", "加入成功"), status=200)
        else:
            join.update(is_pass=2)
            info = "拒绝"
            self.send_user_message_for_apply_info(user_id=user_id, team_name=team_name, info=info)
            return Response(general_message(200, "join rejected", "拒绝成功"), status=200)

    # 用户加入团队，发送站内信给用户
    def send_user_message_for_apply_info(self, user_id, team_name, info):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=team_name)
        message_id = make_uuid()
        content = '{0}团队{1}您加入该团队'.format(tenant.tenant_alias, info)
        UserMessage.objects.create(
            message_id=message_id, receiver_id=user_id, content=content, msg_type="warn", title="用户加入团队信息")


class RegisterStatusView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        try:
            register_config = platform_config_service.get_config_by_key("IS_REGIST")
            if register_config.enable is False:
                return Response(general_message(200, "status is close", "注册关闭状态", bean={"is_regist": False}), status=200)
            else:
                return Response(general_message(200, "status is open", "注册开启状态", bean={"is_regist": True}), status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        """
        修改开启、关闭注册状态
        """
        try:
            user_id = request.user.user_id
            enterprise_id = request.user.enterprise_id
            admin = enterprise_user_perm_repo.get_user_enterprise_perm(user_id=user_id, enterprise_id=enterprise_id)
            is_regist = request.data.get("is_regist")
            if admin:

                if is_regist is False:
                    # 修改全局配置
                    platform_config_service.update_config("IS_REGIST", {"enable": False, "value": None})

                    return Response(general_message(200, "close register", "关闭注册"), status=200)
                else:
                    platform_config_service.update_config("IS_REGIST", {"enable": True, "value": None})
                    return Response(general_message(200, "open register", "开启注册"), status=200)
            else:
                return Response(general_message(400, "no jurisdiction", "没有权限"), status=400)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])


class EnterpriseInfoView(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        查询企业信息
        """
        enter = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id=self.team.enterprise_id)
        ent = enter.to_dict()
        is_ent = False
        try:
            res, body = region_api.get_api_version_v2(self.team.tenant_name, self.response_region)
            if res.status == 200 and body is not None and "enterprise" in body["raw"]:
                is_ent = True
        except region_api.CallApiError as e:
            logger.warning("数据中心{0}不可达,无法获取相关信息: {1}".format(self.response_region.region_name, e.message))
        ent["is_enterprise"] = is_ent

        result = general_message(200, "success", "查询成功", bean=ent)
        return Response(result, status=result["code"])


class UserApplyStatusView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """查询用户的申请状态"""
        try:
            user_id = request.GET.get("user_id", None)
            if user_id:
                user_list = apply_repo.get_applicants_team(user_id=user_id)
                status_list = [user_status.to_dict() for user_status in user_list]
                result = general_message(200, "success", "查询成功", list=status_list)
                return Response(result, status=result["code"])
            else:
                user_list = apply_repo.get_applicants_team(user_id=self.user.user_id)
                status_list = [user_status.to_dict() for user_status in user_list]
                result = general_message(200, "success", "查询成功", list=status_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class JoinTeamView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """查看指定用户加入的团队的状态"""
        user_id = request.GET.get("user_id", None)
        if user_id:
            apply_user = apply_repo.get_applicants_team(user_id=user_id)
            team_list = [team.to_dict() for team in apply_user]
            result = general_message(200, "success", "查询成功", list=team_list)
        else:
            apply_user = apply_repo.get_applicants_team(user_id=self.user.user_id)
            team_list = [team.to_dict() for team in apply_user]
            result = general_message(200, "success", "查询成功", list=team_list)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        """指定用户加入指定团队"""
        user_id = self.user.user_id
        team_name = request.data.get("team_name")
        tenant = Tenants.objects.filter(tenant_name=team_name).first()
        info = apply_service.create_applicants(user_id=user_id, team_name=team_name)
        result = general_message(200, "apply success", "申请加入")
        if info:
            admins = team_repo.get_tenant_admin_by_tenant_id(tenant)
            self.send_user_message_to_tenantadmin(admins=admins, team_name=team_name, nick_name=self.user.get_name())
        return Response(result, status=result["code"])

    def put(self, request, *args, **kwargs):
        user_id = self.user.user_id
        team_name = request.data.get("team_name")
        apply_service.delete_applicants(user_id=user_id, team_name=team_name)
        result = general_message(200, "success", None)
        return Response(result, status=200)

    # 用户加入团队，给管理员发送站内信
    def send_user_message_to_tenantadmin(self, admins, team_name, nick_name):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=team_name)
        logger.debug('---------admin---------->{0}'.format(admins))
        for admin in admins:
            message_id = make_uuid()
            content = '{0}用户申请加入{1}团队'.format(nick_name, tenant.tenant_alias)
            UserMessage.objects.create(
                message_id=message_id, receiver_id=admin.user_id, content=content, msg_type="warn", title="团队加入信息")

    def delete(self, request, *args, **kwargs):
        """
        删除用户加入团队被拒绝记录
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        logger.debug('-------3333------->{0}'.format(request.data))
        user_id = request.data.get("user_id", None)
        team_names = request.data.get("team_name", None)
        is_pass = request.data.get("is_pass", 0)
        if not team_names:
            return Response(general_message(400, "team name is null", "参数错误"), status=400)
        teams_name = team_names.split('-')
        for team_name in teams_name:
            if team_name:
                if user_id:
                    apply_repo.delete_applicants_record(user_id=user_id, team_name=team_name, is_pass=int(is_pass))
                else:
                    user_id = self.user.user_id
                    apply_repo.delete_applicants_record(user_id=user_id, team_name=team_name, is_pass=int(is_pass))
        result = general_message(200, "success", "删除成功")
        return Response(result, status=result["code"])


class TeamUserCanJoin(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        """指定用户可以加入哪些团队"""
        tenants = team_repo.get_tenants_by_user_id(user_id=self.user.user_id)
        team_names = tenants.values("tenant_name")
        # 已加入的团队
        team_name_list = [t_name.get("tenant_name") for t_name in team_names]
        team_list = team_repo.get_teams_by_enterprise_id(enterprise_id)
        apply_team = apply_repo.get_append_applicants_team(user_id=self.user.user_id)
        # 已申请过的团队
        applied_team = [team_name.team_name for team_name in apply_team]
        can_join_team_list = []
        for join_team in team_list:
            if join_team.tenant_name not in applied_team and join_team.tenant_name not in team_name_list:
                can_join_team_list.append(join_team)
        join_list = [{
            "team_name": j_team.tenant_name,
            "team_alias": j_team.tenant_alias,
            "team_id": j_team.tenant_id
        } for j_team in team_repo.get_team_by_team_names(can_join_team_list)]
        result = general_message(200, "success", "查询成功", list=join_list)
        return Response(result, status=result["code"])


class AllUserView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        获取企业下用户信息列表
        """
        try:
            enterprise_id = request.GET.get("enterprise_id", None)
            page_num = int(request.GET.get("page_num", 1))
            page_size = int(request.GET.get("page_size", 5))
            user_name = request.GET.get("user_name", None)
            if not enterprise_id:
                enter = console_enterprise_service.get_enterprise_by_id(enterprise_id=self.user.enterprise_id)
                enterprise_id = enter.enterprise_id
            enter = console_enterprise_service.get_enterprise_by_id(enterprise_id=enterprise_id)
            if user_name:
                euser = user_services.get_user_by_user_name(enterprise_id, user_name)
                list = []
                if not euser:
                    result = general_message("0000", "success", "查询成功", list=list, total=0)
                    return Response(result)
                result_map = dict()
                result_map["user_id"] = euser.user_id
                result_map["email"] = euser.email
                result_map["nick_name"] = euser.nick_name
                result_map["phone"] = euser.phone if euser.phone else "暂无"
                result_map["create_time"] = time_to_str(euser.create_time, "%Y-%m-%d %H:%M:%S")
                tenant_list = user_services.get_user_tenants(euser.user_id)
                result_map["tenants"] = tenant_list
                result_map["enterprise_alias"] = enter.enterprise_alias
                list.append(result_map)
                result = general_message("0000", "success", "查询成功", list=list, total=1)
                return Response(result)
            user_list = user_repo.get_user_by_enterprise_id(enterprise_id=enterprise_id)
            for user1 in user_list:
                if user1.nick_name == self.user.nick_name:
                    user_list.delete(user1)
            user_paginator = JuncheePaginator(user_list, int(page_size))
            users = user_paginator.page(int(page_num))
            list = []
            for user in users:
                result_map = dict()
                result_map["user_id"] = user.user_id
                result_map["email"] = user.email
                result_map["nick_name"] = user.nick_name
                result_map["phone"] = user.phone if user.phone else "暂无"
                result_map["create_time"] = time_to_str(user.create_time, "%Y-%m-%d %H:%M:%S")
                tenant_list = user_services.get_user_tenants(user.user_id)
                result_map["tenants"] = tenant_list
                result_map["enterprise_alias"] = enter.enterprise_alias
                list.append(result_map)

            result = general_message("0000", "success", "查询成功", list=list, total=user_paginator.count)

        except Exception as e:
            logger.debug(e)
            result = error_message()
        return Response(result)

    def delete(self, request, tenant_name, user_id, *args, **kwargs):
        """
        删除用户
        ---
        parameters:
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: path
            - name: user_id
              description: 用户名
              required: true
              type: string
              paramType: path

        """
        try:
            user_services.delete_user(user_id)
            result = general_message("0000", "success", "删除成功")
        except Exception as e:
            logger.exception(e)
            result = general_message("9999", "system error", "系统异常")
        return Response(result)


# 企业管理员添加用户
class AdminAddUserView(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        """
        parameters:
            - name: tenant_name
              description: 租户名称
              required: true
              type: string
              paramType: path
            - name: user_name
              description: 用户名
              required: true
              type: string
              paramType: form
            - name: phone
              description: 手机号
              required: true
              type: string
              paramType: form
            - name: email
              description: 邮件地址
              required: true
              type: string
              paramType: form
            - name: password
              description: 密码
              required: true
              type: string
              paramType: form
            - name: re_password
              description: 重复密码
              required: true
              type: string
              paramType: form
            - name: identity
              description: 用户在租户的身份
              required: true
              type: string
              paramType: form

        """
        tenant_name = request.data.get("tenant_name", None)
        user_name = request.data.get("user_name", None)
        email = request.data.get("email", None)
        password = request.data.get("password", None)
        re_password = request.data.get("re_password", None)
        role_ids = request.data.get("role_ids", None)
        if len(password) < 8:
            result = general_message(400, "len error", "密码长度最少为8位")
            return Response(result)
        if not tenant_name:
            result = general_message(400, "not tenant", "团队不能为空")
            return Response(result)
        if role_ids and tenant_name:
            team = team_services.get_tenant_by_tenant_name(tenant_name)
            if not team:
                raise ServiceHandleException(msg_show=u"团队不存在", msg="no found team", status_code=404)
            # 校验用户信息
            is_pass, msg = user_services.check_params(user_name, email, password, re_password, self.user.enterprise_id)
            if not is_pass:
                result = general_message(403, "user information is not passed", msg)
                return Response(result)
            client_ip = user_services.get_client_ip(request)
            enterprise = console_enterprise_service.get_enterprise_by_enterprise_id(self.user.enterprise_id)
            # 创建用户
            user = user_services.create_user_set_password(user_name, email, password, "admin add", enterprise, client_ip)
            # 创建用户团队关系表
            team_services.add_user_role_to_team(tenant=team, user_ids=[user.user_id], role_ids=role_ids)
            user.is_active = True
            user.save()
            result = general_message(200, "success", "添加用户成功")
        else:
            result = general_message(400, "not role", "创建用户时角色不能为空")
        return Response(result)


class CertificateView(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        bean = {"is_certificate": 1}
        result = general_message(200, "success", "获取成功", bean=bean)
        return Response(result)


class TeamSortDomainQueryView(RegionTenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        """
        获取团队下域名访问量排序
        ---
        parameters:
            - name: team_name
              description: team name
              required: true
              type: string
              paramType: path
        """
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 5))
        repo = request.GET.get("repo", "1")
        if repo == "1":
            total_traffic = 0
            total = 0
            domain_list = []
            query = "?query=sort_desc(sum(%20ceil(increase("\
                + "gateway_requests%7Bnamespace%3D%22{0}%22%7D%5B1h%5D)))%20by%20(host))"
            sufix = query.format(self.tenant.tenant_id)
            start = (page - 1) * page_size
            end = page * page_size
            try:
                res, body = region_api.get_query_domain_access(region_name, team_name, sufix)
                total = len(body["data"]["result"])
                domains = body["data"]["result"]
                for domain in domains:
                    total_traffic += int(domain["value"][1])
                    domain_list = body["data"]["result"][start:end]
            except Exception as e:
                logger.debug(e)
            bean = {"total": total, "total_traffic": total_traffic}
            result = general_message(200, "success", "查询成功", list=domain_list, bean=bean)
            return Response(result, status=200)
        else:
            start = request.GET.get("start", None)
            end = request.GET.get("end", None)
            body = {}
            sufix = "?query=ceil(sum(increase(gateway_requests%7B" \
                + "namespace%3D%22{0}%22%7D%5B1h%5D)))&start={1}&end={2}&step=60".format(self.tenant.tenant_id, start, end)
            try:
                res, body = region_api.get_query_range_data(region_name, team_name, sufix)
            except Exception as e:
                logger.exception(e)
            result = general_message(200, "success", "查询成功", bean=body)
            return Response(result, status=200)


class TeamSortServiceQueryView(RegionTenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        """
        获取团队下组件访问量排序
        ---
        parameters:
            - name: team_name
              description: team name
              required: true
              type: string
              paramType: path
        """
        sufix_outer = "?query=sort_desc(sum(%20ceil(increase("\
            + "gateway_requests%7Bnamespace%3D%22{0}%22%7D%5B1h%5D)))%20by%20(service))".format(self.tenant.tenant_id)

        sufix_inner = "?query=sort_desc(sum(ceil(increase(app_request%7B"\
            + "tenant_id%3D%22{0}%22%2Cmethod%3D%22total%22%7D%5B1h%5D)))by%20(service_id))".format(self.tenant.tenant_id)
        # 对外组件访问量
        try:
            res, body = region_api.get_query_service_access(region_name, team_name, sufix_outer)
            outer_service_list = body["data"]["result"][0:10]
        except Exception as e:
            logger.debug(e)
            outer_service_list = []
        # 对外组件访问量
        try:
            res, body = region_api.get_query_service_access(region_name, team_name, sufix_inner)
            inner_service_list = body["data"]["result"][0:10]
        except Exception as e:
            logger.debug(e)
            inner_service_list = []

        # 合并
        service_id_list = []
        for service in outer_service_list:
            service_id_list.append(service["metric"]["service"])
        for service_oj in inner_service_list:
            if service_oj["metric"]["service"] not in service_id_list:
                service_id_list.append(service_oj["metric"]["service"])
        service_traffic_list = []
        for service_id in service_id_list:
            service_dict = dict()
            metric = dict()
            value = []
            service_dict["metric"] = metric
            service_dict["value"] = value
            traffic_num = 0
            v1 = 0
            for service in outer_service_list:
                if service["metric"]["service"] == service_id:
                    traffic_num += int(service["value"][1])
                    v1 = service["value"][0]
            for service_oj in inner_service_list:
                if service_oj["metric"]["service"] == service_id:
                    traffic_num += int(service_oj["value"][1])
                    v1 = service_oj["value"][0]
            metric["service"] = service_id
            value.append(v1)
            value.append(traffic_num)
            service_traffic_list.append(service_dict)
        for service_traffic in service_traffic_list[::-1]:
            service_obj = service_repo.get_service_by_service_id(service_traffic["metric"]["service"])
            if service_obj:
                service_traffic["metric"]["service_cname"] = service_obj.service_cname
                service_traffic["metric"]["service_alias"] = service_obj.service_alias
            if not service_obj:
                service_traffic_list.remove(service_traffic)
        # 排序取前十
        service_list = sorted(service_traffic_list, key=lambda x: x["value"][1], reverse=True)[0:10]

        result = general_message(200, "success", "查询成功", list=service_list)
        return Response(result, status=result["code"])
