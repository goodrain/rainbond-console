# -*- coding: utf8 -*-
import logging

from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from rest_framework.response import Response
import re

from backends.services.configservice import config_service
from backends.services.exceptions import *
from backends.services.resultservice import *
from console.models import UserMessage
from console.repositories.apply_repo import apply_repo
from console.repositories.enterprise_repo import enterprise_user_perm_repo, enterprise_repo
from console.repositories.team_repo import team_repo
from console.repositories.user_repo import user_repo
from console.services.apply_service import apply_service
from console.services.enterprise_services import enterprise_services, make_uuid
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.services.perm_services import perm_services
from console.services.region_services import region_services
from console.views.base import JWTAuthApiView
from goodrain_web.tools import JuncheePaginator
from www.models import Tenants
from www.perms import PermActions, get_highest_identity
from www.utils.return_message import general_message, error_message
from console.repositories.perm_repo import role_repo
from console.repositories.region_repo import region_repo
from console.utils.timeutil import time_to_str
from backends.services.userservice import user_service
from console.services.enterprise_services import enterprise_services as console_enterprise_service
from www.apiclient.regionapi import RegionInvokeApi
from console.repositories.app import service_repo

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
        try:
            query_key = request.GET.get("query_key", None)
            if query_key:
                q_obj = Q(nick_name__icontains=query_key) | Q(email__icontains=query_key)
                users = user_services.get_user_by_filter(args=(q_obj,))
                user_list = [
                    {
                        "nick_name": user_info.nick_name,
                        "email": user_info.email,
                        "user_id": user_info.user_id
                    }
                    for user_info in users
                ]
                result = general_message(200, "query user success", "查询用户成功", list=user_list)
                return Response(result, status=200)
            else:
                result = general_message(200, "query user success", "你没有查询任何用户")
                return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class TeamUserDetaislView(JWTAuthApiView):

    def get_highest_identity(self, identitys):
        identity_map = {"access": 1, "viewer": 2, "developer": 3, "admin": 4, "owner": 5}
        final_identity = identitys[0]
        identity_num = -1
        for i in identitys:
            num = identity_map.get(final_identity)
            if num > identity_num:
                final_identity = i
                identity_num = num
        return final_identity

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
        try:
            # u, perms = user_services.get_user_detail(tenant_name=team_name, nick_name=user_name)
            team = team_services.get_tenant_by_tenant_name(team_name)
            is_user_enter_amdin = user_services.is_user_admin_in_current_enterprise(self.user, team.enterprise_id)
            perms = team_services.get_user_perm_identitys_in_permtenant(self.user.user_id, team_name)
            role_list = team_services.get_user_perm_role_in_permtenant(user_id=self.user.user_id, tenant_name=team_name)
            # teams = [{"team_identity": perm.identity} for perm in perms]
            data = dict()
            data["nick_name"] = self.user.nick_name
            data["email"] = self.user.email
            # data["teams_identity"] = teams[0]["team_identity"]
            data["teams_identity"] = perms + role_list
            data["is_user_enter_amdin"] = is_user_enter_amdin
            code = 200
            result = general_message(code, "user details query success.", "用户详情获取成功", bean=data)
            return Response(result, status=code)
        except UserNotExistError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "this user does not exist on this team.", "该用户不存在这个团队")
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class UserAllTeamView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        获取当前用户所加入的所有团队
        ---

        """
        user = request.user
        code = 200
        try:
            tenants = team_services.get_current_user_tenants(user_id=user.user_id)
            if tenants:
                teams_list = list()
                for tenant in tenants:
                    teams_list.append(
                        {
                            "team_name": tenant.tenant_name,
                            "team_alias": tenant.tenant_alias,
                            "team_id": tenant.tenant_id,
                            "create_time": tenant.create_time
                        }
                    )
                result = general_message(200, "team query success", "成功获取该用户加入的团队", list=teams_list)
            else:
                teams_list = []
                result = general_message(200, "team query success", "该用户没有加入团队", bean=teams_list)
        except Exception as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "failed", "请求失败")
        return Response(result, status=code)


class AddTeamView(JWTAuthApiView):
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
                enterprise = enterprise_services.get_enterprise_by_enterprise_id(self.user.enterprise_id)
                if not enterprise:
                    return Response(general_message(500, "user's enterprise is not found", "无企业信息"), status=500)
                code, msg, team = team_services.create_team(self.user, enterprise, regions, team_alias)

                role_obj = role_repo.get_default_role_by_role_name(role_name="owner", is_default=True)

                # 创建用户在团队的权限
                perm_info = {
                    "user_id": user.user_id,
                    "tenant_id": team.ID,
                    "enterprise_id": enterprise.pk,
                    # 创建团队时给创建用户添加owner的角色
                    "role_id": role_obj.pk
                }
                perm_services.add_user_tenant_perm(perm_info)
                for r in regions:
                    code, msg, tenant_region = region_services.create_tenant_on_region(team.tenant_name, r)
                    if code != 200:
                        team_services.delete_tenant(team.tenant_name)
                        return Response(general_message(code, "add team error", msg), status=code)
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
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class TeamUserView(JWTAuthApiView):
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
        try:
            code = 200
            page = request.GET.get("page", 1)
            # 获得租户/团队 对象
            user_list = team_services.get_tenant_users_by_tenant_name(tenant_name=team_name)
            users_list = list()
            for user in user_list:
                # 获取一个用户在一个团队中的身份列表
                perms_identitys_list = team_services.get_user_perm_identitys_in_permtenant(user_id=user.user_id,
                                                                                           tenant_name=team_name)
                # 获取一个用户在一个团队中的角色ID列表
                perms_role_list = team_services.get_user_perm_role_id_in_permtenant(user_id=user.user_id,
                                                                                    tenant_name=team_name)

                role_info_list = []

                for identity in perms_identitys_list:
                    if identity == "access":
                        role_info_list.append({"role_name": identity, "role_id": None})
                    else:
                        role_id = role_repo.get_role_id_by_role_name(identity)
                        role_info_list.append({"role_name": identity, "role_id": role_id})
                for role in perms_role_list:
                    role_name = role_repo.get_role_name_by_role_id(role)
                    role_info_list.append({"role_name": role_name, "role_id": role})

                users_list.append(
                    {
                        "user_id": user.user_id,
                        "user_name": user.nick_name,
                        "email": user.email,
                        "role_info": role_info_list
                    }
                )
            paginator = Paginator(users_list, 8)
            try:
                users = paginator.page(page).object_list
            except PageNotAnInteger:
                users = paginator.page(1).object_list
            except EmptyPage:
                users = paginator.page(paginator.num_pages).object_list
            result = general_message(code, "team members query success", "查询成功", list=users, total=paginator.count)
        except UserNotExistError as e:
            code = 400
            logger.exception(e)
            result = general_message(code, "user not exist", e.message)
        except TenantNotExistError as e:
            code = 400
            logger.exception(e)
            result = general_message(code, "tenant not exist", "{}团队不存在".format(team_name))
        except Exception as e:
            code = 500
            logger.exception(e)
            result = general_message(code, "system error", "系统异常")
        return Response(data=result, status=code)


class TeamUserAddView(JWTAuthApiView):
    def post(self, request, team_name, *args, **kwargs):
        """
        团队中添加新用户
        ---
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: user_ids
              description: 添加成员id 格式 {'user_ids':'1,2'}
              required: true
              type: string
              paramType: body
            - name: identitys
              description: 选择权限(当前用户是管理员'admin'或者创建者'owner'就展示权限选择列表，不是管理员就没有这个选项, 默认被邀请用户权限是'access') 格式{"identitys": "viewer,access"}
              required: true
              type: string
              paramType: body
        """
        perm_list = team_services.get_user_perm_identitys_in_permtenant(
            user_id=request.user.user_id,
            tenant_name=team_name
        )
        # 根据用户在一个团队的角色来获取这个角色对应的所有权限操作
        role_perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)
        if perm_list:
            no_auth = ("owner" not in perm_list) and ("admin" not in perm_list)
        else:
            no_auth = "manage_team_member_permissions" not in role_perm_tuple
        if no_auth:
            code = 400
            result = general_message(code, "no identity", "您不是管理员，没有权限做此操作")
            return Response(result, status=code)
        try:
            user_ids = request.data.get('user_ids', None)
            identitys = request.data.get('identitys', None)
            identitys = identitys.split(',') if identitys else []
            if not user_ids:
                raise ParamsError("用户名为空")
            code = 200
            team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
            user_ids = user_ids.split(',')
            if identitys:
                team_services.add_user_to_team(request=request, tenant=team, user_ids=user_ids, identitys=identitys)
                result = general_message(code, "success", "用户添加到{}成功".format(team_name))
            else:
                team_services.add_user_to_team(request=request, tenant=team, user_ids=user_ids, identitys='access')
                result = general_message(code, "success", "用户添加到{}成功".format(team_name))
        except PermTenantsExistError as e:
            code = 400
            result = general_message(code, "permtenant exist", e.message)
        except ParamsError as e:
            logging.exception(e)
            code = 400
            result = general_message(code, "params user_id is empty", e.message)
        except UserNotExistError as e:
            code = 400
            result = general_message(code, "user not exist", e.message)
        except Tenants.DoesNotExist as e:
            code = 400
            logger.exception(e)
            result = general_message(code, "tenant not exist", "{}团队不存在".format(team_name))
        except UserExistError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "user already exist", e.message)
        except Exception as e:
            code = 500
            logger.exception(e)
            print(str(e))
            result = general_message(code, "system error", "系统异常")
        return Response(result, status=code)


class UserDelView(JWTAuthApiView):
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
            identitys = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )

            perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)

            if "owner" not in identitys and "admin" not in identitys and "manage_team_member_permissions" not in perm_tuple:
                code = 400
                result = general_message(code, "no identity", "没有权限")
                return Response(result, status=code)

            user_ids = str(request.data.get("user_ids", None))
            if not user_ids:
                result = general_message(400, "failed", "删除成员不能为空")
                return Response(result, status=400)

            try:
                user_id_list = [int(user_id) for user_id in user_ids.split(",")]
            except Exception as e:
                logger.exception(e)
                result = general_message(200, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=400)

            if request.user.user_id in user_id_list:
                result = general_message(400, "failed", "不能删除自己")
                return Response(result, status=400)

            for user_id in user_id_list:
                print user_id
                role_name_list = team_services.get_user_perm_role_in_permtenant(user_id=user_id, tenant_name=team_name)
                identity_list = team_services.get_user_perm_identitys_in_permtenant(user_id=user_id,
                                                                                    tenant_name=team_name)
                print role_name_list
                if "owner" in role_name_list or "owner" in identity_list:
                    result = general_message(400, "failed", "不能删除团队创建者！")
                    return Response(result, status=400)
            try:
                user_services.batch_delete_users(team_name, user_id_list)
                result = general_message(200, "delete the success", "删除成功")
            except Tenants.DoesNotExist as e:
                logger.exception(e)
                result = generate_result(400, "tenant not exist", "{}团队不存在".format(team_name))
            except Exception as e:
                logger.exception(e)
                result = error_message(e.message)
            return Response(result)
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class TeamNameModView(JWTAuthApiView):
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
        try:
            perms = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)

            no_auth = True

            if "owner" in perms or "modify_team_name" in perm_tuple:
                no_auth = False

            if no_auth:
                code = 400
                result = general_message(code, "no identity", "权限不足不能修改团队名")
            else:
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
        except Exception as e:
            code = 500
            result = general_message(code, "update failed", "团队名修改失败")
            logger.exception(e)
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
        code = 200

        identity_list = team_services.get_user_perm_identitys_in_permtenant(
            user_id=request.user.user_id,
            tenant_name=team_name
        )
        perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)
        team = team_services.get_tenant_by_tenant_name(team_name)
        if not user_services.is_user_admin_in_current_enterprise(request.user, team.enterprise_id):
            if "owner" not in identity_list and "drop_tenant" not in perm_tuple:
                code = 400
                result = general_message(code, "no identity", "您不是最高管理员，不能删除团队")
                return Response(result, status=code)
        try:
            service_count = team_services.get_team_service_count_by_team_name(team_name=team_name)
            if service_count >= 1:
                result = general_message(400, "failed", "当前团队内有应用,不可以删除")
                return Response(result, status=400)
            status = team_services.delete_tenant(tenant_name=team_name)
            if not status:
                result = general_message(code, "delete a tenant successfully", "删除团队成功")
            else:
                code = 400
                result = general_message(code, "delete a tenant failed", "删除团队失败")
        except Tenants.DoesNotExist as e:
            code = 400
            logger.exception(e)
            result = generate_result(code, "tenant not exist", "{}团队不存在".format(team_name))
        except Exception as e:
            code = 500
            result = general_message(code, "sys exception", "系统异常")
            logger.exception(e)
        return Response(result, status=code)


class TeamInvView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        邀请注册，弹框的详情
        ---
        parameters:
            - name: team_name
              description: 邀请进入的团队id
              required: true
              type: string
              paramType: path
        """
        try:
            team = team_services.get_tenant_by_tenant_name(tenant_name=team_name)
            team_id = str(team.ID)
            data = dict()
            # url = "http://" + request.get_host() + '/console/users/register?tag=' + team_id
            data["register_type"] = "invitation"
            data["value"] = team_id
            result = general_message(200, "success", "成功获得邀请码", bean=data)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class TeamExitView(JWTAuthApiView):
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

        identity_list = team_services.get_user_perm_identitys_in_permtenant(
            user_id=request.user.user_id,
            tenant_name=team_name
        )

        role_name_list = team_services.get_user_perm_role_in_permtenant(user_id=request.user.user_id,
                                                                        tenant_name=team_name)

        if "owner" in identity_list:
            result = general_message(409, "not allow exit.", "您是当前团队创建者，不能退出此团队")
            return Response(result, status=409)
        if "admin" in identity_list:
            result = general_message(409, "not allow exit.", "您是当前团队管理员，不能退出此团队")
            return Response(result, status=409)

        if "owner" in role_name_list:
            result = general_message(409, "not allow exit.", "您是当前团队创建者，不能退出此团队")
            return Response(result, status=409)
        if "admin" in role_name_list:
            result = general_message(409, "not allow exit.", "您是当前团队管理员，不能退出此团队")
            return Response(result, status=409)

        try:
            if request.user.nick_name == "rainbond-demo" and team_name == "a5qw69mz":
                return Response(general_message(403, "permission denied!","您无法退出此团队"),status=403)

            code, msg_show = team_services.exit_current_team(team_name=team_name, user_id=request.user.user_id)
            if code == 200:
                result = general_message(code=code, msg="success", msg_show=msg_show)
            else:
                result = general_message(code=code, msg="failed", msg_show=msg_show)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class TeamDetailView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        获取团队详情
        ---
        parameters:
            - name: team_name
              description: team name
              required: true
              type: string
              paramType: path
        """
        try:

            tenant = team_services.get_tenant_by_tenant_name(team_name)
            if not tenant:
                return Response(general_message(404, "team not exist", "团队{0}不存在".format(team_name)), status=404)
            user_team_perm = team_services.get_user_perms_in_permtenant(self.user.user_id, team_name)
            tenant_info = dict()
            team_region_list = region_services.get_region_list_by_team_name(request=request,
                                                                            team_name=team_name)
            p = PermActions()
            tenant_info["team_id"] = tenant.ID
            tenant_info["team_name"] = tenant.tenant_name
            tenant_info["team_alias"] = tenant.tenant_alias
            tenant_info["limit_memory"] = tenant.limit_memory
            tenant_info["pay_level"] = tenant.pay_level
            tenant_info["region"] = team_region_list
            tenant_info["creater"] = tenant.creater
            tenant_info["create_time"] = tenant.create_time

            if not user_team_perm:
                if not self.user.is_sys_admin and team_name != "grdemo":
                    return Response(general_message(403, "you right to see this team", "您无权查看此团队"), 403)
                else:
                    tenant_info["identity"] = "viewer"
                    perms = p.keys('tenant_{0}_actions'.format("viewer"))
                    tenant_info["tenant_actions"] = perms
            else:
                perms_list = team_services.get_user_perm_identitys_in_permtenant(user_id=self.user.user_id,
                                                                                 tenant_name=tenant.tenant_name)
                role_name_list = team_services.get_user_perm_role_in_permtenant(user_id=self.user.user_id,
                                                                                tenant_name=tenant.tenant_name)

                role_perms_tuple = team_services.get_user_perm_in_tenant(user_id=self.user.user_id,
                                                                         tenant_name=tenant.tenant_name)

                tenant_actions = ()
                tenant_info["identity"] = perms_list + role_name_list
                if perms_list:
                    final_identity = get_highest_identity(perms_list)
                    perms = p.keys('tenant_{0}_actions'.format(final_identity))
                    tenant_actions += perms
                tenant_actions += role_perms_tuple
                tenant_info["tenant_actions"] = tuple(set(tenant_actions))

            return Response(general_message(200, "success", "查询成功", bean=tenant_info), status=200)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])


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
                return Response(general_message(409, "region alias is exist", "团队名称{0}已存在".format(team_alias)),
                                status=409)
            region = region_repo.get_region_by_region_name(region_name)
            if not region:
                return Response(general_message(404, "region not exist", "需要开通的数据中心{0}不存在".format(region_name)),
                                status=404)
            enterprise = enterprise_services.get_enterprise_by_enterprise_id(self.user.enterprise_id)
            if not enterprise:
                return Response(general_message(404, "user's enterprise is not found", "无法找到用户所在的数据中心"))

            code, msg, team = team_services.create_team(self.user, enterprise, [region_name], team_alias)
            if not code:
                return Response(general_message(code, "create team error", msg), status=code)
            perm_info = {
                "user_id": self.user.user_id,
                "tenant_id": team.ID,
                "identity": "owner",
                "enterprise_id": enterprise.pk
            }
            perm_services.add_user_tenant_perm(perm_info)
            # 创建用户在企业的权限
            # user_services.make_user_as_admin_for_enterprise(self.user.user_id, enterprise.enterprise_id)
            # 为团队开通默认数据中心并在数据中心创建租户
            code, msg, tenant_region = region_services.create_tenant_on_region(team.tenant_name, team.region)
            if code != 200:
                return Response(general_message(code, "create tenant on region error", msg), status=code)
            # 公有云，如果没有领过资源包，为开通的数据中心领取免费资源包
            if settings.MODULES.get('SSO_LOGIN'):
                result = region_services.get_enterprise_free_resource(tenant_region.tenant_id, enterprise.enterprise_id,
                                                                      tenant_region.region_name, self.user.nick_name)
                logger.debug("get free resource on [{}] to team {}: {}".format(tenant_region.region_name,
                                                                               team.tenant_name,
                                                                               result))
            self.user.is_active = True
            self.user.save()

            result = general_message(200, "success", "初始化成功")

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class ApplicantsView(JWTAuthApiView):

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
        try:
            # 判断角色
            identity_list = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            page_num = int(request.GET.get("page_num", 1))
            page_size = int(request.GET.get("page_size", 5))
            rt_list = []
            total = 0
            # 是管理员
            if "owner" or "admin" in identity_list:
                # 查询申请用户
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
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    def put(self, request, team_name, *args, **kwargs):
        """管理员审核用户"""
        try:
            # 判断角色
            identity_list = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            if "owner" or "admin" in identity_list:
                user_id = request.data.get("user_id")
                action = request.data.get("action")
                join = apply_repo.get_applicants_by_id_team_name(user_id=user_id, team_name=team_name)
                if action is True:
                    join.update(is_pass=1)
                    team = team_repo.get_team_by_team_name(team_name=team_name)
                    team_services.add_user_to_team_by_viewer(tenant=team, user_id=user_id)
                    # 发送通知
                    info = "同意"
                    self.send_user_message_for_apply_info(user_id=user_id, team_name=team.tenant_name, info=info)
                    return Response(general_message(200, "join success", "加入成功"), status=200)
                else:
                    join.update(is_pass=2)
                    info = "拒绝"
                    self.send_user_message_for_apply_info(user_id=user_id, team_name=team_name, info=info)
                    return Response(general_message(200, "join rejected", "拒绝成功"), status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])

    # 用户加入团队，发送站内信给用户
    def send_user_message_for_apply_info(self, user_id, team_name, info):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=team_name)
        message_id = make_uuid()
        content = '{0}团队{1}您加入该团队'.format(tenant.tenant_alias, info)
        UserMessage.objects.create(message_id=message_id, receiver_id=user_id, content=content,
                                   msg_type="warn", title="用户加入团队信息")


class AllTeamsView(JWTAuthApiView):

    def get(self, request, *args, **kwargs):
        """
        获取企业可加入的团队列表
        """
        try:
            enterprise_id = request.GET.get("enterprise_id", None)
            tenant_alias = request.GET.get("tenant_alias", None)
            page_num = int(request.GET.get("page_num", 1))
            page_size = int(request.GET.get("page_size", 5))
            if not enterprise_id:
                enter = enterprise_services.get_enterprise_by_id(enterprise_id=self.user.enterprise_id)
                enterprise_id = enter.enterprise_id
            if tenant_alias:
                team_list = team_services.get_fuzzy_tenants_by_tenant_alias_and_enterprise_id(enterprise_id=enterprise_id, tenant_alias=tenant_alias)
            else:
                team_list = team_services.get_enterprise_teams(enterprise_id)
            team_paginator = JuncheePaginator(team_list, int(page_size))
            total = team_paginator.count
            page_team = team_paginator.page(page_num)
            t_list = [{
                "enterprise_id": team_info.enterprise_id,
                "create_time": team_info.create_time,
                "team_name": team_info.tenant_name,
                "team_alias": team_info.tenant_alias,
                "owner": user_repo.get_user_nickname_by_id(user_id=team_info.creater)
            } for team_info in page_team]
            result = general_message(200, "success", "查询成功", list=t_list, total=total)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class RegisterStatusView(JWTAuthApiView):

    def get(self, request, *args, **kwargs):
        try:
            register_config = config_service.get_regist_status()
            if register_config != "yes":
                return Response(general_message(200, "status is close", "注册关闭状态", bean={"is_regist": False}),
                                status=200)
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
                    config_service.update_config("REGISTER_STATUS", "no")

                    return Response(general_message(200, "close register", "关闭注册"), status=200)
                else:
                    config_service.update_config("REGISTER_STATUS", "yes")
                    return Response(general_message(200, "open register", "开启注册"), status=200)
            else:
                return Response(general_message(400, "no jurisdiction", "没有权限"), status=400)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])


class EnterpriseInfoView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        查询企业信息
        """
        try:
            team_name = request.GET.get("team_name", None)
            if not team_name:
                return Response(general_message(400, "team name is null", "参数错误"), status=400)

            team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)

            enter = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id=team.enterprise_id)
            enterprise_id = enter.enterprise_id
            enterprise_info = enterprise_repo.get_enterprise_by_enterprise_id(enterprise_id=enterprise_id)
            result = general_message(200, "success", "查询成功", bean=enterprise_info.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
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
        try:
            user_id = request.GET.get("user_id", None)
            if user_id:
                apply_user = apply_repo.get_applicants_team(user_id=user_id)
                team_list = [team.to_dict() for team in apply_user]
                result = general_message(200, "success", "查询成功", list=team_list)
            else:
                apply_user = apply_repo.get_applicants_team(user_id=self.user.user_id)
                team_list = [team.to_dict() for team in apply_user]
                result = general_message(200, "success", "查询成功", list=team_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    def post(self, request, *args, **kwargs):
        """指定用户加入指定团队"""
        try:
            user_id = self.user.user_id
            team_name = request.data.get("team_name")
            tenant = Tenants.objects.filter(tenant_name=team_name).first()
            info = apply_service.create_applicants(user_id=user_id, team_name=team_name)
            if not info:
                result = general_message(200, "already apply", "已申请")
                return Response(result, status=result["code"])
            else:
                result = general_message(200, "apply success", "申请加入")
                logger.debug('--------tenant.ID-------->{0}'.format(tenant.ID))
                admins = team_repo.get_tenant_admin_by_tenant_id(tenant_id=tenant.ID)
                self.send_user_message_to_tenantadmin(admins=admins, team_name=team_name, nick_name=self.user.nick_name)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    # 用户加入团队，给管理员发送站内信
    def send_user_message_to_tenantadmin(self, admins, team_name, nick_name):
        tenant = team_repo.get_tenant_by_tenant_name(tenant_name=team_name)
        logger.debug('---------admin---------->{0}'.format(admins))
        for admin in admins:
            # nick_name = user_repo.get_user_by_user_id(user.user_id)
            message_id = make_uuid()
            content = '{0}用户申请加入{1}团队'.format(nick_name, tenant.tenant_alias)
            UserMessage.objects.create(message_id=message_id, receiver_id=admin.user_id, content=content,
                                       msg_type="warn", title="团队加入信息")

    def delete(self, request, *args, **kwargs):
        """
        删除用户加入团队被拒绝记录
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
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
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class TeamUserCanJoin(JWTAuthApiView):

    def get(self, request, *args, **kwargs):
        """指定用户可以加入哪些团队"""
        try:
            tenants = team_repo.get_tenants_by_user_id(user_id=self.user.user_id)
            team_names = tenants.values("tenant_name")
            # 已加入的团队
            team_name_list = [t_name.get("tenant_name") for t_name in team_names]

            user_id = request.GET.get("user_id", None)
            if user_id:
                enterprise_id = user_repo.get_by_user_id(user_id=user_id).enterprise_id
                team_list = team_repo.get_teams_by_enterprise_id(enterprise_id)
                apply_team = apply_repo.get_applicants_team(user_id=user_id)
            else:
                enterprise_id = user_repo.get_by_user_id(user_id=self.user.user_id).enterprise_id
                team_list = team_repo.get_teams_by_enterprise_id(enterprise_id)
                apply_team = apply_repo.get_applicants_team(user_id=self.user.user_id)
            # 已申请过的团队
            applied_team = [team_repo.get_team_by_team_name(team_name=team_name) for team_name in
                            [team_name.team_name for team_name in apply_team]]
            join_list = []
            for join_team in team_list:
                if join_team not in applied_team and join_team.tenant_name not in team_name_list:
                    join_list.append(join_team)
            join_list = [{
                "team_name": j_team.tenant_name,
                "team_alias": j_team.tenant_alias,
                "team_id": j_team.tenant_id
            } for j_team in join_list]
            result = general_message(200, "success", "查询成功", list=join_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
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
                enter = enterprise_services.get_enterprise_by_id(enterprise_id=self.user.enterprise_id)
                enterprise_id = enter.enterprise_id
            enter = enterprise_services.get_enterprise_by_id(enterprise_id=enterprise_id)
            if user_name:
                euser = user_services.get_user_by_user_name(user_name)
                list = []
                if not euser:
                    result = generate_result("0000", "success", "查询成功", list=list, total=0)
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
                result = generate_result("0000", "success", "查询成功", list=list, total=1)
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

            result = generate_result("0000", "success", "查询成功", list=list, total=user_paginator.count)

        except Exception as e:
            logger.debug(e)
            result = generate_error_result()
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
            result = generate_result(
                "0000", "success", "删除成功"
            )
        except Exception as e:
            logger.exception(e)
            result = generate_result("9999", "system error", "系统异常")
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
        try:
            tenant_name = request.data.get("tenant_name", None)
            user_name = request.data.get("user_name", None)
            phone = request.data.get("phone", None)
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
            if role_ids:
                try:
                    role_id_list = [int(id) for id in role_ids.split(",")]
                except Exception as e:
                    logger.exception(e)
                    code = 400
                    result = general_message(code, "params is empty", "参数格式不正确")
                    return Response(result, status=code)
                for id in role_id_list:
                    if id not in team_services.get_all_team_role_id(tenant_name=tenant_name):
                        code = 400
                        result = general_message(code, "The role does not exist", "该角色在团队中不存在")
                        return Response(result, status=code)
                # 校验用户信息
                is_pass, msg = user_service.check_params(user_name, email, password, re_password)
                if not is_pass:
                    result = general_message(403, "user information is not passed", msg)
                    return Response(result)
                client_ip = user_service.get_client_ip(request)
                enterprise = console_enterprise_service.get_enterprise_by_enterprise_id(self.user.enterprise_id)
                # 创建用户
                user = user_service.create_user(user_name, phone, email, password, "admin add", enterprise, client_ip)
                # 创建用户团队关系表
                team_services.create_tenant_role(user_id=user.user_id, tenant_name=tenant_name,
                                                 role_id_list=role_id_list)
                user.is_active = True
                user.save()
                result = general_message(200, "success", "添加用户成功")
            else:
                result = general_message(400, "not role", "创建用户时角色不能为空")
        except Exception as e:
            logger.exception(e)
            result = general_message(500, e.message, "系统异常")
        return Response(result)


class TeamUserAdminView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        try:
            perm_list = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            if not perm_list:
                result = general_message(200, "success", "暂无权限")
                return Response(result)
            if "owner" in perm_list or "admin" in perm_list:
                result = general_message(200, "success", "查询成功", bean={"is_access": True})
            else:
                result = general_message(200, "success", "查询成功", bean={"is_access": False})
        except Exception as e:
            logger.exception(e)
            result = general_message(500, e.message, "系统异常")
        return Response(result)


class CertificateView(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        bean = {
            "is_certificate": 1
        }
        result = generate_result(200, "success", "获取成功", bean=bean)
        return Response(result)


class TeamSortDomainQueryView(JWTAuthApiView):
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
        try:
            team = team_services.get_tenant_by_tenant_name(team_name)
            if not team:
                result = general_message(400, "team id null", "团队不存在")
                return Response(result, status=400)
            if repo == "1":
                sufix = "?query=sort_desc(sum(%20ceil(increase(gateway_requests%7Bnamespace%3D%22{0}%22%7D%5B1h%5D)))%20by%20(host))".format(team.tenant_id)
                res, body = region_api.get_query_domain_access(region_name, team_name, sufix)
                logger.debug('=====body======>{0}'.format(body))
                total = len(body["data"]["result"])
                domains = body["data"]["result"]
                total_traffic = 0
                for domain in domains:
                    total_traffic += int(domain["value"][1])
                start = (page - 1) * page_size
                end = page * page_size
                bean = {"total": total, "total_traffic": total_traffic}
                domain_list = body["data"]["result"][start: end]
                result = general_message(200, "success", "查询成功", list=domain_list, bean=bean)
                return Response(result, status=200)
            else:
                start = request.GET.get("start", None)
                end = request.GET.get("end", None)
                sufix = "?query=ceil(sum(increase(gateway_requests%7Bnamespace%3D%22{0}%22%7D%5B1h%5D)))&start={1}&end={2}&step=60".format(
                    team.tenant_id, start, end)
                logger.debug('--------->{0}'.format(sufix))
                res, body = region_api.get_query_range_data(region_name, team_name, sufix)
                logger.debug('=====body=1=====>{0}'.format(body))
                result = general_message(200, "success", "查询成功", bean=body)
                return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = general_message(400, e.message, "查询失败")
            return Response(result, status=result["code"])


class TeamSortServiceQueryView(JWTAuthApiView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        """
        获取团队下服务访问量排序
        ---
        parameters:
            - name: team_name
              description: team name
              required: true
              type: string
              paramType: path
        """
        try:
            team = team_services.get_tenant_by_tenant_name(team_name)
            if not team:
                result = general_message(400, "team id null", "团队不存在")
                return Response(result, status=400)
            sufix_outer = "?query=sort_desc(sum(%20ceil(increase(gateway_requests%7Bnamespace%3D%22{0}%22%7D%5B1h%5D)))%20by%20(service))".format(team.tenant_id)

            sufix_inner = "?query=sort_desc(sum(ceil(increase(app_request%7Btenant_id%3D%22{0}%22%2Cmethod%3D%22total%22%7D%5B1h%5D)))by%20(service_id))".format(team.tenant_id)
            # 对外服务访问量
            res, body = region_api.get_query_service_access(region_name, team_name, sufix_outer)
            outer_service_list = body["data"]["result"][0: 10]
            import json
            logger.debug('=====body======>{0}'.format(json.dumps(outer_service_list)))

            # 对外服务访问量
            res, body = region_api.get_query_service_access(region_name, team_name, sufix_inner)
            inner_service_list = body["data"]["result"][0: 10]
            logger.debug('=====body======>{0}'.format(json.dumps(inner_service_list)))

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
            service_list = sorted(service_traffic_list, key=lambda x: x["value"][1], reverse=True)[0: 10]

            result = general_message(200, "success", "查询成功", list=service_list)
        except Exception as e:
            logger.exception(e)
            result = general_message(400, e.message, "查询失败")
        return Response(result, status=result["code"])