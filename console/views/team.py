# -*- coding: utf8 -*-
import logging

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from rest_framework.response import Response

from backends.services.exceptions import *
from backends.services.resultservice import *
from console.repositories.perm_repo import perms_repo
from console.services.enterprise_services import enterprise_services
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.views.base import JWTAuthApiView
from www.models import Tenants
from www.utils.return_message import general_message, error_message

logger = logging.getLogger("default")


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
            u, perms = user_services.get_user_detail(tenant_name=team_name, nick_name=user_name)
            teams = [{"team_identity": perm.identity} for perm in perms]
            data = dict()
            data["nick_name"] = u.nick_name
            data["email"] = u.email
            data["teams_identity"] = teams[0]["team_identity"]
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
            if Tenants.objects.filter(tenant_alias=team_alias).exists():
                result = general_message(400, "failed", "该团队名已存在")
                return Response(result, status=400)
            else:
                enterprise = enterprise_services.get_enterprise_first()
                code, msg, team = team_services.add_team(team_alias=team_alias, user=user, region_names=regions)
                if team:
                    perm = perms_repo.add_user_tenant_perm(
                        perm_info={
                            "user_id": user.user_id,
                            "tenant_id": team.ID,
                            "identity": "owner",
                            "enterprise_id": enterprise.ID
                        }
                    )
                    if not perm:
                        result = general_message(400, "invited failed", "团队关联失败，注册失败")
                        return Response(result, status=400)
                if code == "200":
                    data = {"team_name": team.tenant_name, "team_id": team.tenant_id, "team_ID": team.ID,
                            "team_alisa": team.tenant_alias, "creater": team.creater, "user_num": 1,
                            "enterprise_id": team.enterprise_id}
                    result = general_message(code, "create new team success", "新建团队成功", bean=data)
                    return Response(result, status=code)
                else:
                    result = general_message(code, 'failed', msg_show=msg)
                    return Response(result, status=code)
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
            user_list = team_services.get_tenant_users_by_tenant_name(tenant_name=team_name)
            users_list = list()
            for user in user_list:
                perms_list = team_services.get_user_perm_identitys_in_permtenant(user_id=user.user_id,
                                                                                 tenant_name=team_name)
                users_list.append(
                    {
                        "user_id": user.user_id,
                        "user_name": user.nick_name,
                        "email": user.email,
                        "identity": perms_list
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
              description: 选择权限(当前用户是管理员'admin'或者创建者'owner'就展示权限选择列表，不是管理员就没有这个选项, 默认被邀请用户权限是'acess') 格式{"identitys": "viewer,access"}
              required: true
              type: string
              paramType: body
        """
        perm_list = team_services.get_user_perm_identitys_in_permtenant(
            user_id=request.user.user_id,
            tenant_name=team_name
        )
        no_auth = ("owner" not in perm_list) and ("admin" not in perm_list)
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
            no_auth = "owner" not in team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            if no_auth:
                code = 400
                result = general_message(code, "no identity", "没有权限")
            else:
                user_ids = str(request.data.get("user_ids", None))
                if not user_ids:
                    result = general_message(400, "failed", "删除成员不能为空")
                    return Response(result, status=400)
                if str(request.user.user_id) in user_ids:
                    result = general_message(400, "failed", "不能删除自己")
                    return Response(result, status=400)
                try:
                    user_id_list = user_ids.split(",")
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
            no_auth = "owner" not in team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
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
        if "owner" not in team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
        ):
            code = 400
            result = general_message(code, "no identity", "您不是最高管理员，不能删除团队")
        else:
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
        if "owner" in team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
        ):
            result = general_message(409, "not allow exit.", "您是当前团队最高管理员，不能退出此团队")
        else:
            try:
                code, msg_show = team_services.exit_current_team(team_name=team_name, user_id=request.user.user_id)
                if code == 200:
                    result = general_message(code=code, msg="success", msg_show=msg_show)
                else:
                    result = general_message(code=code, msg="failed", msg_show=msg_show)
            except Exception as e:
                logger.exception(e)
                result = error_message(e.message)
        return Response(result, status=result["code"])
