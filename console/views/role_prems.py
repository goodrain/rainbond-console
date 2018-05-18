# -*- coding: utf-8 -*-
import logging

import re
from rest_framework.response import Response
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.cache import never_cache
from backends.services.exceptions import *
from backends.services.resultservice import *
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.views.base import JWTAuthApiView, AlowAnyApiView
from www.decorator import perm_required
from www.models import Tenants
from console.repositories.perm_repo import role_repo, role_perm_repo
from console.views.app_config.base import AppBaseView
from www.utils.return_message import general_message, error_message
from console.services.perm_services import app_perm_service

logger = logging.getLogger("default")


class PermOptionsView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        可选权限操作展示
        ---

        """
        try:
            options_list = role_perm_repo.get_permission_options()

            result = general_message(200, "get permissions success", "获取权限选项成功", list=options_list)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class TeamAddRoleView(JWTAuthApiView):
    @perm_required('tenant_manage_role')
    def post(self, request, team_name, *args, **kwargs):
        """
        新建一个角色
        ------
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: role_name
              description: 角色名称 格式 {'role_name':'DBA'}
              required: true
              type: string
              paramType: body
            - name: options_id_list
              description: 权限id列表 格式 {'options_id_list':'1,2,3,4'}
              required: true
              type: string
              paramType: body
        """

        try:
            role_name = request.data.get("role_name", None)
            options_id_list = request.data.get("options_id_list", None)

            if not role_name:
                raise ParamsError("角色名为空")
            if not options_id_list:
                raise ParamsError("权限选项为空")
            try:
                premission_id_list = options_id_list.split(",")
                premission_id_list = map(lambda x: int(x), premission_id_list)
            except Exception as e:
                logging.exception(e)
                code = 400
                result = general_message(code, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=code)

            r = re.compile(u'^[a-zA-Z0-9_\\-\u4e00-\u9fa5]+$')
            if not r.match(role_name.decode("utf-8")) or len(role_name) > 30:
                code = 400
                result = general_message(code, "failed", "角色名称只能是30个字符内任意数字,字母,中文字符,下划线的组合")
                return Response(result, status=code)
            if role_name in role_repo.get_default_role():
                code = 400
                result = general_message(code, "failed", "角色名称不能与系统默认相同")
                return Response(result, status=code)
            if role_repo.team_role_is_exist_by_role_name_team_id_2(role_name=role_name, tenant_name=team_name):
                code = 400
                result = general_message(code, "failed", "该角色已经存在")
                return Response(result, status=code)

            select_perm_list = role_perm_repo.get_select_perm_list()
            for i in premission_id_list:
                if i not in select_perm_list:
                    result = general_message(400, "failed", "权限列表中有权限不可选")
                    return Response(result, status=400)

            role_obj = team_services.add_role_by_team_name_perm_list(role_name=role_name, tenant_name=team_name,
                                                                     perm_id_list=premission_id_list)
            if role_obj:
                code = 200
                role_info = {"role_id": role_obj.pk, "role_name": role_obj.role_name, "is_default": role_obj.is_default}
                result = general_message(code, "success", "创建角色成功", bean=role_info)
            else:
                code = 400
                result = general_message(code, "failed", "创建角色失败")
        except ParamsError as e:
            logging.exception(e)
            code = 400
            result = general_message(code, "params is empty", e.message)
        except Tenants.DoesNotExist as e:
            code = 200
            logger.exception(e)
            print(str(e))
            result = generate_result(code, "tenant not exist", "团队不存在")
        except Exception as e:
            code = 500
            logger.exception(e)
            print(str(e))
            result = general_message(code, "system error", "系统异常")
        return Response(result, status=code)


class TeamDelRoleView(JWTAuthApiView):
    @perm_required('tenant_manage_role')
    def delete(self, request, team_name, *args, **kwargs):
        """
        删除自定义角色
        ------
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: role_id
              description: 角色ID 格式 {'role_id':'1'}
              required: true
              type: string
              paramType: body
        """
        try:
            role_id = request.data.get("role_id", None)

            if not role_id:
                raise ParamsError("角色ID为空")
            try:
                role_id = int(role_id)
            except ValueError as e:
                logging.exception(e)
                code = 400
                result = general_message(code, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=code)
            if role_id in role_repo.get_default_role_id():
                code = 400
                result = general_message(code, "failed", "不可删除系统默认角色")
                return Response(result, status=code)
            if not role_repo.team_role_is_exist_by_role_name_team_id(tenant_name=team_name,
                                                                     role_id=role_id):
                code = 400
                result = general_message(code, "failed", "该角色不存在")
                return Response(result, status=code)

            if role_repo.team_user_is_exist_by_role_id_tenant_name(role_id=role_id, tenant_name=team_name):
                code = 400
                result = general_message(code, "failed", "有团队成员拥有该角色，不能删除")
                return Response(result, status=code)

            try:
                team_services.del_role_by_team_name_role_name_role_id(tenant_name=team_name,
                                                                      role_id=role_id)
                code = 200
                result = general_message(code, "success", "删除角色成功")

            except Exception as e:
                logging.exception(e)
                code = 400
                result = general_message(code, "failed", "删除角色失败")
                return Response(result, status=code)

        except ParamsError as e:
            logging.exception(e)
            code = 400
            result = general_message(code, "params is empty", e.message)

        except Tenants.DoesNotExist as e:
            code = 200
            logger.exception(e)
            print(str(e))
            result = generate_result(code, "tenant not exist", "团队不存在")

        except Exception as e:
            code = 500
            logger.exception(e)
            print(str(e))
            result = general_message(code, "system error", "系统异常")
        return Response(result, status=code)


class UserUpdatePemView(JWTAuthApiView):
    @perm_required('tenant_manage_role')
    def post(self, request, team_name, *args, **kwargs):
        """
        修改角色名称及对应的权限
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: role_id
              description: 角色ID {'role_id':'1'}
              required: true
              type: string
              paramType: body
            - name: new_role_name
              description: 新的的角色名称
              required: true
              type: string
              paramType: body
            - name: new_options_id_list
              description: 新的权限ID列表 格式 {'new_options_id_list':'1,2,3,4'}
              required: true
              type: string
              paramType: body
        """
        try:
            role_id = request.data.get("role_id", None)
            new_role_name = request.data.get("new_role_name", None)
            new_options_id_list = request.data.get("new_options_id_list", None)

            if not role_id:
                raise ParamsError("原角色ID为空")
            if not new_role_name:
                raise ParamsError("新角色名为空")
            if not new_options_id_list:
                raise ParamsError("权限选项为空")

            try:
                role_id = int(role_id)
                perm_id_list = [int(perm_id) for perm_id in new_options_id_list.split(",")]
            except Exception as e:
                logging.exception(e)
                code = 400
                result = general_message(code, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=code)

            r = re.compile(u'^[a-zA-Z0-9_\\-\u4e00-\u9fa5]+$')
            if not r.match(new_role_name.decode("utf-8")) or len(new_role_name) > 30:
                code = 400
                result = general_message(code, "failed", "角色名称只能是30个字符内任意数字,字母,中文字符,下划线的组合")
                return Response(result, status=code)

            if new_role_name in role_repo.get_default_role():
                code = 400
                result = general_message(code, "failed", "角色名称不能与系统默认相同")
                return Response(result, status=code)
            if not role_repo.team_role_is_exist_by_role_name_team_id(tenant_name=team_name,
                                                                     role_id=role_id):
                code = 400
                result = general_message(code, "failed", "原角色不存在")
                return Response(result, status=code)

            select_perm_list = role_perm_repo.get_select_perm_list()
            for i in perm_id_list:
                if i not in select_perm_list:
                    result = general_message(400, "failed", "权限列表中有权限不可选")
                    return Response(result, status=400)

            try:
                role_obj = team_services.update_role_by_team_name_role_name_perm_list(
                    new_role_name=new_role_name,
                    role_id=role_id,
                    tenant_name=team_name,
                    perm_id_list=perm_id_list)
                if role_obj:
                    code = 200
                    role_info = {"role_id": role_obj.pk, "role_name": role_obj.role_name,
                                 "is_default": role_obj.is_default}
                    result = general_message(code, "success", "更新角色权限成功", bean=role_info)
                else:
                    code = 400
                    result = general_message(code, "failed", "更新角色权限失败")
            except Exception as e:
                logging.exception(e)
                code = 400
                print(str(e))
                result = general_message(code, "failed", "更新角色权限失败")
                return Response(result, status=code)
        except ParamsError as e:
            logging.exception(e)
            code = 400
            result = general_message(code, "params is empty", e.message)
        except Tenants.DoesNotExist as e:
            code = 200
            logger.exception(e)
            print(str(e))
            result = generate_result(code, "tenant not exist", "团队不存在")
        except Exception as e:
            code = 500
            logger.exception(e)
            print(str(e))
            result = general_message(code, "system error", "系统异常")
        return Response(result, status=code)


class UserRoleView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        一个团队所有可展示的的角色及角色对应的权限信息展示(不含owner)
        （每页展示八个角色）
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
        - name: page_size
          description: 每页展示个数(默认8个)
          required: false
          type: string
          paramType: query
        """

        try:
            page = request.GET.get("page", 1)
            page_size = request.GET.get("page_size", 8)
            role_list = team_services.get_tenant_role_by_tenant_name(tenant_name=team_name)

            try:
                page_size = int(page_size)
            except Exception as e:
                logger.exception(e)
                result = general_message(400, "Incorrect parameter format", "参数page_size格式错误")
                return Response(result, status=500)

            paginator = Paginator(role_list, page_size)
            try:
                role_list = paginator.page(int(page)).object_list
            except PageNotAnInteger:
                page = 1
                role_list = paginator.page(1).object_list
            except EmptyPage:
                page = paginator.num_pages
                role_list = paginator.page(paginator.num_pages).object_list
            result = general_message(200, "get permissions success", "获取权限成功", list=role_list, total=paginator.count,
                                     num_pages=paginator.num_pages, current_page=page, page_size=page_size)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class UserModifyPemView(JWTAuthApiView):
    @perm_required('manage_team_member_permissions')
    def post(self, request, team_name, user_name, *args, **kwargs):
        """
        修改团队成员角色
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: user_name
              description: 被修改权限的团队成员
              required: true
              type: string
              paramType: path
            - name: role_ids
              description: 角色  格式 {"role_ids": "1,2,3"}
              required: true
              type: string
              paramType: body
        """
        try:
            perm_list = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)

            no_auth = ("owner" not in perm_list) and (
                    "admin" not in perm_list) and "manage_team_member_permissions" not in perm_tuple

            if no_auth:
                code = 400
                result = general_message(code, "no identity", "您没有权限做此操作")
            else:
                code = 200
                role_ids = request.data.get("role_ids", None)
                if role_ids:
                    try:
                        role_id_list = [int(id) for id in role_ids.split(",")]
                    except Exception as e:
                        logger.exception(e)
                        code = 400
                        result = general_message(code, "params is empty", "参数格式不正确")
                        return Response(result, status=code)

                    other_user = user_services.get_user_by_username(user_name=user_name)
                    if other_user.user_id == request.user.user_id:
                        result = general_message(400, "failed", "您不能修改自己的权限！")
                        return Response(result, status=400)

                    for id in role_id_list:
                        if id not in team_services.get_all_team_role_id(tenant_name=team_name):
                            code = 400
                            result = general_message(code, "The role does not exist", "该角色在团队中不存在")
                            return Response(result, status=code)

                    identity_list = team_services.get_user_perm_identitys_in_permtenant(user_id=other_user.user_id,
                                                                                        tenant_name=team_name)

                    role_name_list = team_services.get_user_perm_role_in_permtenant(user_id=other_user.user_id,
                                                                                    tenant_name=team_name)
                    if "owner" in identity_list or "owner" in role_name_list:
                        result = general_message(400, "failed", "您不能修改创建者的权限！")
                        return Response(result, status=400)

                    team_services.change_tenant_role(user_id=other_user.user_id, tenant_name=team_name,
                                                     role_id_list=role_id_list)
                    result = general_message(code, "identity modify success", "{}角色修改成功".format(user_name))
                else:
                    result = general_message(400, "identity failed", "修改角色时，角色不能为空")
        except UserNotExistError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "users not exist", "该用户不存在")
        except Exception as e:
            logger.exception(e)
            code = 500
            result = error_message(e.message)
        return Response(result, status=code)


class TeamAddUserView(JWTAuthApiView):
    @perm_required('manage_team_member_permissions')
    def post(self, request, team_name, *args, **kwargs):
        """
        团队中添加新用户给用户分配一个角色
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
            - name: role_ids
              description: 选择角色 格式{"role_ids": "1,2,3"}
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

        no_auth = ("owner" not in perm_list) and (
                "admin" not in perm_list) and "manage_team_member_permissions" not in role_perm_tuple

        if no_auth:
            code = 400
            result = general_message(code, "no identity", "您没有权限做此操作")
            return Response(result, status=code)
        try:
            user_ids = request.data.get('user_ids', None)
            role_ids = request.data.get('role_ids', None)
            if not user_ids:
                raise ParamsError("用户名为空")
            if not role_ids:
                raise ParamsError("角色ID为空")
            try:
                user_ids = [int(user_id) for user_id in user_ids.split(",")]
                role_ids = [int(user_id) for user_id in role_ids.split(",")]
            except Exception as e:
                code = 400
                logger.exception(e)
                result = general_message(code, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=code)
            for role_id in role_ids:
                if role_id not in team_services.get_all_team_role_id(tenant_name=team_name):
                    code = 400
                    result = general_message(code, "The role does not exist", "该角色在团队中不存在")
                    return Response(result, status=code)

            user_id = team_services.user_is_exist_in_team(user_list=user_ids, tenant_name=team_name)
            if user_id:
                user_obj = user_services.get_user_by_user_id(user_id=user_id)
                code = 400
                result = general_message(code, "user already exist", "用户{}已经存在".format(user_obj.nick_name))
                return Response(result, status=code)

            code = 200
            team = team_services.get_tenant(tenant_name=team_name)

            team_services.add_user_role_to_team(request=request, tenant=team, user_ids=user_ids, role_ids=role_ids)
            result = general_message(code, "success", "用户添加到{}成功".format(team_name))

        except ParamsError as e:
            logging.exception(e)
            code = 400
            result = general_message(code, "params is empty", e.message)
        except UserNotExistError as e:
            code = 400
            result = general_message(code, "user not exist", e.message)
        except Tenants.DoesNotExist as e:
            code = 400
            logger.exception(e)
            result = general_message(code, "tenant not exist", "{}团队不存在".format(team_name))
        except Exception as e:
            code = 500
            logger.exception(e)
            print(str(e))
            result = general_message(code, "system error", "系统异常")
        return Response(result, status=code)


class ServicePermissionView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取一个应用中存在的成员及他们的权限
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path

        """
        try:
            perm_list = app_perm_service.get_user_service_perm_info(self.service)
            result = general_message(200, "success", "查询成功", list=perm_list)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_member_perms')
    def post(self, request, *args, **kwargs):
        """
        为应用添加的用户权限，可单个可批量
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: user_ids
              description: 用户id 格式{"user_ids":1,2,3}
              required: true
              type: string
              paramType: form
            - name: perm_ids
              description: 权限id  {"perm_ids":1,2,3}
              required: true
              type: string
              paramType: form

        """
        try:
            perm_ids = request.data.get("perm_ids", None)
            user_ids = request.data.get("user_ids", None)
            if not perm_ids or not perm_ids:
                return Response(general_message(400, "params error", "却少参数"), status=400)

            try:
                perm_list = [int(perm) for perm in perm_ids.split(",")]
                user_list = [int(user_id) for user_id in user_ids.split(",")]
            except Exception as e:
                logging.exception(e)
                code = 400
                result = general_message(code, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=code)

            code, msg, service_perm = app_perm_service.add_user_service_perm(self.user, user_list, self.tenant,
                                                                             self.service,
                                                                             perm_list)
            if code != 200:
                return Response(general_message(code, "add service perm error", msg), status=400)
            result = general_message(code, "success", "添加应用成员成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_member_perms')
    def put(self, request, *args, **kwargs):
        """
        修改用户在应用中的权限
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: user_id
              description: 用户id
              required: true
              type: string
              paramType: form
            - name: perm_ids
              description: 权限id 格式{'perm_ids':'1,2,3'}
              required: true
              type: string
              paramType: form

        """
        try:
            perm_ids = request.data.get("perm_ids", None)
            user_id = request.data.get("user_id", None)
            if not perm_ids or not user_id:
                return Response(general_message(400, "params error", "参数异常"), status=400)

            try:
                perm_list = [int(perm_id) for perm_id in perm_ids.split(",")]
                user_id = int(user_id)
            except Exception as e:
                logging.exception(e)
                code = 400
                result = general_message(code, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=code)

            code, msg, service_perm = app_perm_service.update_user_service_perm(self.user, user_id,
                                                                                self.service,
                                                                                perm_list)
            if code != 200:
                return Response(general_message(code, "update service perm error", msg), status=400)
            result = general_message(code, "success", "修改成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_member_perms')
    def delete(self, request, *args, **kwargs):
        """
        删除应用添加的权限
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: user_id
              description: 用户id
              required: true
              type: string
              paramType: form

        """
        try:
            user_id = request.data.get("user_id", None)
            if not user_id:
                return Response(general_message(400, "params error", "参数不能为空"), status=400)

            try:
                user_id = int(user_id)
            except Exception as e:
                logging.exception(e)
                code = 400
                result = general_message(code, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=code)
            code, msg = app_perm_service.delete_user_service_perm(self.user, user_id,
                                                                  self.service)
            if code != 200:
                return Response(general_message(code, "delete service perm error", msg), status=400)
            result = general_message(code, "success", "删除应用成员成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
