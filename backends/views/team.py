# -*- coding: utf8 -*-
import logging
import json
import datetime

from rest_framework.response import Response
from django.db import connection

from backends.services.exceptions import *
from backends.services.resultservice import *
from backends.services.tenantservice import tenant_service
from backends.services.userservice import user_service
from backends.services.regionservice import region_service
from console.services.team_services import team_services as console_team_service
from base import BaseAPIView
from www.models import Tenants, PermRelTenant
from console.services.enterprise_services import enterprise_services
from console.services.perm_services import perm_services as console_perm_service
from console.services.region_services import region_services as console_region_service
from django.db import transaction
from console.services.team_services import team_services
from console.repositories.user_repo import user_repo
from www.service_http import RegionServiceApi
from backends.services.httpclient import HttpInvokeApi
from console.repositories.region_repo import region_repo
from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.services.user_services import user_services
from console.models.main import EnterpriseUserPerm
from console.utils.timeutil import time_to_str

logger = logging.getLogger("default")
http_client = HttpInvokeApi()
regionClient = RegionServiceApi()


class AllTeamView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取团队信息
        ---
        parameters:
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
            - name: enterprise_alias
              description: 企业别名
              required: false
              type: string
              paramType: query
            - name: tenant_alias
              description: 团队别名
              required: false
              type: string
              paramType: query
            - name: tenant_name
              description: 团队名称
              required: false
              type: string
              paramType: query

        """
        try:
            page = int(request.GET.get("page_num", 1))
            page_size = int(request.GET.get("page_size", 10))
            enterprise_alias = request.GET.get("enterprise_alias", None)
            tenant_alias = request.GET.get("tenant_alias", None)
            if enterprise_alias:
                enter = enterprise_services.get_enterprise_by_enterprise_alias(enterprise_alias)
                if not enter:
                    return Response(
                        generate_result("0404", "enterprise is not found", "企业{0}不存在".format(enterprise_alias)))
            list1 = []
            tenants_num = Tenants.objects.count()
            start = (page-1)*10
            remaining_num = tenants_num - (page-1)*10
            end = 10
            if remaining_num < page_size:
                end = remaining_num
            # 通过别名来搜索团队(排序分页)
            if tenant_alias:
                cursor = connection.cursor()
                cursor.execute(
                    "select t.tenant_name, t.tenant_alias,t.region,t.limit_memory,t.enterprise_id, t.tenant_id,u.nick_name as creater,count(s.ID) as num from tenant_info t LEFT JOIN tenant_service s on t.tenant_id=s.tenant_id,user_info u where t.creater=u.user_id and t.tenant_alias LIKE '%{0}%' group by tenant_id order by num desc LIMIT {1},{2};".format(
                        tenant_alias, start, end))
                tenant_tuples = cursor.fetchall()
            else:
                cursor = connection.cursor()
                cursor.execute(
                    "select t.tenant_name, t.tenant_alias,t.region,t.limit_memory,t.enterprise_id, t.tenant_id,u.nick_name as creater,count(s.ID) as num from tenant_info t LEFT JOIN tenant_service s on t.tenant_id=s.tenant_id,user_info u where t.creater=u.user_id group by tenant_id order by num desc LIMIT {0},{1};".format(
                        start, end))
                tenant_tuples = cursor.fetchall()
            try:
                # 查询所有团队有哪些数据中心
                region_list = []
                for tenant in tenant_tuples:
                    tenant_id = tenant[5]
                    tenant_region_list = tenant_service.get_all_tenant_region_by_tenant_id(tenant_id)
                    if len(tenant_region_list) != 0:
                        for tenant_region in tenant_region_list:
                            if not tenant_region.region_name in region_list:
                                region_list.append(tenant_region.region_name)
            except Exception as e:
                logger.exception(e)
                result = generate_result("1111", "2.faild", "{0}".format(e.message))
                return Response(result)
            try:
                resources_dicts = {}
                run_app_num_dicts = {}
                for region_name in region_list:
                    time1 = datetime.datetime.now()
                    logger.debug('````````````11111`````````````````{0}'.format(time1))
                    try:
                        region_obj = region_repo.get_region_by_region_name(region_name)
                        if not region_obj:
                            continue
                        tenant_name_list = []
                        # 循环查询哪些团队开通了该数据中心，将团队名放进列表中
                        for tenant in tenant_tuples:
                            tenant_region_list = tenant_service.get_all_tenant_region_by_tenant_id(tenant[5])
                            for tenant_regions in tenant_region_list:
                                tenant_region_name = tenant_regions.region_name
                                if tenant_region_name == region_name:
                                    tenant_name_list.append(tenant[0])
                                else:
                                    continue
                        # 获取数据中心下每个团队的使用资源和运行的应用数量
                        time2 = datetime.datetime.now()
                        logger.debug('```````````222222``````````````````{0}'.format(time2))
                        res, body = http_client.get_tenant_limit_memory(region_obj, json.dumps({"tenant_name": tenant_name_list}))
                        logger.debug("======111===={0}".format(body["list"]))
                        if int(res.status) >= 400:
                            continue
                        if not body.get("list"):
                            continue
                        tenant_resources_list = body.get("list")
                        time3 = datetime.datetime.now()
                        logger.debug('`````````````33333````````````````{0}'.format(time3))

                        tenant_resources_dict = {}
                        for tenant_resources in tenant_resources_list:
                            run_app_num = tenant_resources["service_running_num"]
                            for tenant in tenant_tuples:
                                tenant_id = tenant[5]
                                if tenant_id == tenant_resources["tenant_id"]:
                                    if tenant_id not in run_app_num_dicts:
                                        run_app_num_dicts[tenant_id] = {"run_app_num": [run_app_num]}
                                    else:
                                        run_app_num_dicts[tenant_id]["run_app_num"].append(run_app_num)
                            tenant_resources_dict[tenant_resources["tenant_id"]] = tenant_resources

                        # tenant_resources_dict = {id:{}, id:{}}

                        for tenant in tenant_tuples:
                            tenant_region = {}
                            tenant_id = tenant[5]
                            if tenant_id in tenant_resources_dict:
                                # tenant_region["name1"] = {"cpu_total":0, "cpu_use":0}
                                tenant_region[region_obj.region_alias] = tenant_resources_dict[tenant_id]
                                if tenant_id not in resources_dicts:
                                    resources_dicts[tenant_id] = {"resources": tenant_region}
                                else:
                                    resources_dicts[tenant_id]["resources"].update(tenant_region)
                        time4 = datetime.datetime.now()
                        logger.debug('``````````````4444```````````````{0}'.format(time4))
                    except Exception as e:
                        logger.exception(e)
                        continue
            except Exception as e:
                logger.exception(e)
                result = generate_result("1111", "2.6-faild", "{0}".format(e.message))
                return Response(result)

            for tenant in tenant_tuples:
                tenant_info = {}
                # 为每个团队拼接信息
                tenant_id = tenant[5]
                for key in run_app_num_dicts:
                    if key == tenant_id:
                        tenant_info["run_app_num"] = run_app_num_dicts[key]["run_app_num"]
                for key in resources_dicts:
                    if key == tenant_id:
                        tenant_info["resources"] = resources_dicts[key]["resources"]
                tenant_info["total_app"] = tenant[7]
                user_list = tenant_service.get_tenant_users(tenant[0])
                tenant_info["user_num"] = len(user_list)
                tenant_info["tenant_creater"] = tenant[6]
                tenant_info["tenant_alias"] = tenant[1]
                tenant_info["tenant_name"] = tenant[0]
                tenant_info["region"] = tenant[2]
                tenant_info["tenant_id"] = tenant[5]
                tenant_info["limit_memory"] = tenant[3]
                tenant_info["enterprise_id"] = tenant[4]
                list1.append(tenant_info)
            # 需要license控制，现在没有，默认为一百万
            allow_num = 1000000
            bean = {"tenants_num": tenants_num, "allow_num": allow_num}
            result = generate_result(
                "0000", "success", "查询成功", bean=bean, list=list1, total=tenants_num
            )
            return Response(result)
        except Exception as e:
            result = generate_result("1111", "4.faild", "{0}".format(e.message))
            return Response(result)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        添加团队
        ---
        parameters:
            - name: tenant_name
              description: 团队名
              required: true
              type: string
              paramType: form
            - name: enterprise_id
              description: 企业ID
              required: true
              type: string
              paramType: form
            - name: useable_regions
              description: 可用数据中心 ali-sh,ali-hz
              required: false
              type: string
              paramType: form
        """
        sid = None
        try:
            tenant_name = request.data.get("tenant_name", None)
            if not tenant_name:
                return Response(generate_result("1003", "team name is none", "团对名称不能为空"))
            enterprise_id = request.data.get("enterprise_id", None)
            if not enterprise_id:
                return Response(generate_result("1003", "enterprise id is none", "企业ID不能为空"))
            enter = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
            if not enter:
                return Response(generate_result("0404", "enterprise not found", "企业在云帮不存在"))

            team = console_team_service.get_team_by_team_alias_and_eid(tenant_name, enterprise_id)
            if team:
                return Response(generate_result("0409", "team alias is exist", "团队别名{0}在该企业已存在".format(tenant_name)))

            creater = request.data.get("creater", None)
            if not creater:
                return Response(generate_result("0412", "please specify owner", "请指定拥有者"))
            user = user_repo.get_user_by_username(creater)
            useable_regions = request.data.get("useable_regions", "")
            logger.debug("team name {0}, usable regions {1}".format(tenant_name, useable_regions))
            regions = []
            if useable_regions:
                regions = useable_regions.split(",")
            # 开启保存点
            sid = transaction.savepoint()
            code, msg, team = console_team_service.create_team(user, enter, regions, tenant_name)
            # 创建用户在团队的权限
            perm_info = {
                "user_id": user.user_id,
                "tenant_id": team.ID,
                "identity": "owner",
                "enterprise_id": enter.pk
            }
            console_perm_service.add_user_tenant_perm(perm_info)

            for r in regions:
                code, msg, tenant_region = console_region_service.create_tenant_on_region(team.tenant_name, r)
                if code != 200:
                    logger.error(msg)
                    if sid:
                        transaction.savepoint_rollback(sid)
                    return Response(generate_result("0500", "add team error", msg), status=code)

            transaction.savepoint_commit(sid)

            bean = {"tenant_name": team.tenant_name, "tenant_id": team.tenant_id, "tenant_alias": team.tenant_alias,
                    "user_num": 1}
            result = generate_result("0000", "success", "租户添加成功", bean=bean)
        except TenantOverFlowError as e:
            result = generate_result("7001", "tenant over flow", "{}".format(e.message))
        except TenantExistError as e:
            result = generate_result("7002", "tenant exist", "{}".format(e.message))
        except NoEnableRegionError as e:
            result = generate_result("7003", "no enable region", "{}".format(e.message))
        except UserNotExistError as e:
            result = generate_result("7004", "not user", "{}".format(e.message))
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            result = generate_error_result()
        return Response(result)

    def delete(self, request, *args, **kwargs):
        """
        删除团队
        ---
        parameters:
            - name: team_name
              description: 要删除的团队
              required: true
              type: string
              paramType: path
        """
        tenant_name = request.data.get("tenant_name", None)
        if not tenant_name:
            return Response(generate_result("1003", "team name is none", "参数缺失"))

        try:
            service_count = team_services.get_team_service_count_by_team_name(team_name=tenant_name)
            if service_count >= 1:
                result = generate_result("0404", "failed", "当前团队内有应用,不可以删除")
                return Response(result)
            status = team_services.delete_tenant(tenant_name=tenant_name)
            if not status:
                result = generate_result("0000", "success", "删除团队成功")
            else:
                result = generate_result("1002", "delete a tenant failed", "删除团队失败")
        except Tenants.DoesNotExist as e:
            logger.exception(e)
            result = generate_result("1004", "tenant not exist", "{}团队不存在".format(tenant_name))
        except Exception as e:
            result = generate_result("9999", "sys exception", "系统异常")
            logger.exception(e)
        return Response(result)


class TeamView(BaseAPIView):
    def get(self, request, tenant_name, *args, **kwargs):
        """
        获取某指定团队信息
        ---
        parameters:
            - name: tenant_name
              description: 团队名称
              required: true
              type: string
              paramType: path

        """
        try:
            tenant = tenant_service.get_tenant(tenant_name)
            if not tenant:
                result = generate_result("0000", "success", "查询成功", list=[])
                return Response(result)
            create_id = tenant.creater
            user = user_service.get_user_by_user_id(create_id)
            user_list = tenant_service.get_users_by_tenantID(tenant.ID)
            user_num = len(user_list)
            rt_list = [{"tenant_id": tenant.tenant_id, "tenant_name": tenant.tenant_name, "user_num": user_num,
                        "tenant_alias": tenant.tenant_alias, "creater": user.nick_name}]
            result = generate_result("0000", "success", "查询成功", list=rt_list)
        except Tenants.DoesNotExist as e:
            logger.exception(e)
            result = generate_result("1001", "tenant not exist", "租户{}不存在".format(tenant_name))
        except Exception as e:
            logger.exception(e)
            result = generate_result("9999", "system error", "系统异常")
        return Response(result)


class TeamUserView(BaseAPIView):
    def get(self, request, tenant_name, user_name, *args, **kwargs):
        """
        查询某团队下的某个用户
        ---
        parameters:
            - name: tenant_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: user_namebucen
              description: 用户名
              required: true
              type: string
              paramType: path
        """
        try:
            user = user_service.get_user_by_username(user_name)
            tenant = tenant_service.get_tenant(tenant_name)
            perm_tenants = PermRelTenant.objects.filter(tenant_id=tenant.ID, user_id=user.pk)
            if not perm_tenants:
                result = generate_result("1010", "tenant user not exist",
                                         "租户{0}下不存在用户{1}".format(tenant_name, user_name))
            else:
                code = "0000"
                msg = "success"
                list = []
                res = {"tenant_id": tenant.tenant_id, "tenant_name": tenant.tenant_name, "user_id": user.user_id,
                       "nick_name": user.nick_name, "email": user.email, "phone": user.phone}
                list.append(res)
                result = generate_result(code, msg, "查询成功", list=list)
        except UserNotExistError as e:
            result = generate_result("1008", "user not exist", e.message)
        except Tenants.DoesNotExist as e:
            logger.exception(e)
            result = generate_result("1001", "tenant not exist", "租户{}不存在".format(tenant_name))
        except Exception as e:
            logger.exception(e)
            result = generate_result("9999", "system error", "系统异常")
        return Response(result)


class AddTeamUserView(BaseAPIView):
    def post(self, request, tenant_name, *args, **kwargs):
        """
        为团队添加用户
        ---
        parameters:
            - name: tenant_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: user_name
              description: 用户名
              required: true
              type: string
              paramType: form
            - name: identity
              description: 权限
              required: true
              type: string
              paramType: form
        """
        try:
            user_name = request.data.get("user_name", None)
            if not user_name:
                return Response(generate_result("1003", "username is null", "用户名不能为空"))
            identity = request.data.get("identity", "viewer")
            if not identity:
                return Response(generate_result("1003", "identity is null", "用户权限不能为空"))

            user = user_service.get_user_by_username(user_name)
            tenant = tenant_service.get_tenant(tenant_name)
            if not tenant:
                result = generate_result("1001", "tenant not exist", "租户{}不存在".format(tenant_name))
                return Response(result)
            enterprise = enterprise_services.get_enterprise_by_id(tenant.enterprise_id)
            tenant_service.add_user_to_tenant(tenant, user, identity, enterprise)
            result = generate_result("0000", "success", "用户添加成功")
        except PermTenantsExistError as e:
            result = generate_result("1009", "permtenant exist", e.message)
        except UserNotExistError as e:
            result = generate_result("1008", "user not exist", e.message)
        except Tenants.DoesNotExist as e:
            logger.exception(e)
            result = generate_result("1001", "tenant not exist", "租户{}不存在".format(tenant_name))
        except Exception as e:
            logger.exception(e)
            result = generate_result("9999", "system error", "系统异常")
        return Response(result)


class TeamUsableRegionView(BaseAPIView):

    def get(self, request, tenant_name, *args, **kwargs):
        """
        获取团队可用的数据中心
        ---
        parameters:
            - name: tenant_name
              description: 团队名
              required: true
              type: string
              paramType: path
        """
        region_name = None
        try:
            team = console_team_service.get_tenant_by_tenant_name(tenant_name)
            if not team:
                return Response(generate_result("0404", "team not found", "团队{0}不存在".format(tenant_name)))

            region_list = console_region_service.get_region_list_by_team_name(request, tenant_name)
            if region_list:
                region_name = region_list[0]["team_region_name"]
            else:
                regions = region_service.get_all_regions()
                if regions:
                    region_name = regions[0].region_name
            result = generate_result("0000", "success", "查询成功", bean={"region_name": region_name})
        except Exception as e:
            logger.exception(e)
            result = generate_result("9999", "system error", "系统异常")
        return Response(result)


class TenantSortView(BaseAPIView):
    """企业下团队排行（根据人数+应用数）"""

    def get(self, request, *args, **kwargs):

        enterprise_id = request.GET.get("enterprise_id", None)
        if enterprise_id:
            enter = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)
            if not enter:
                return Response(
                    generate_result("0404", "enterprise is not found", "企业不存在"))
            try:
                tenant_list = tenant_service.get_all_tenant()
                if not tenant_list:
                    result = generate_result('0000', 'success', '查询成功', list=[])
                    return Response(result)
                bean = dict()
                bean["tenant_num"] = len(tenant_list)
                user_list = user_repo.get_all_users()
                bean["user_num"] = len(user_list)
                sort_list = []
                cursor = connection.cursor()
                cursor.execute(
                    "select t.tenant_alias,t.tenant_id, count(s.ID) as num from tenant_info as t left join tenant_service as s on t.tenant_id=s.tenant_id group by tenant_id order by num desc limit 0,5;")
                tenant_tuples = cursor.fetchall()
                for tenant_tuple in tenant_tuples:
                    tenant_alias_list = list()
                    tenant_alias_list.append(tenant_tuple[0])
                    sort_list.append(tenant_alias_list)
                result = generate_result('0000', 'success', '查询成功', list=sort_list, bean=bean)
            except Exception as e:
                logger.exception(e)
                result = generate_result('9999', 'system error', '系统异常')
            return Response(result)
        else:
            result = generate_result("1003", "the enterprise alias cannot be empty", "企业别名不能为空")
            return Response(result)


# 管理后台添加企业管理员
class AddEnterAdminView(BaseAPIView):
    def post(self, request, *args, **kwargs):
        """

        """
        try:
            username = request.data.get("username", None)
            enterprise_id = request.data.get("enterprise_id", None)
            enterprise_alias = request.data.get("enterprise_alias", None)
            # 校验参数
            if not username or not enterprise_id or not enterprise_alias:
                return Response(generate_result(
                    "1003", "params error", "参数错误"))
            user_obj = user_repo.get_user_by_user_name(username)
            if not user_obj:
                return Response(generate_result(
                    "1004", "user already exists", "用户在控制台不存在"))
            # 查询企业信息
            enterprise = enterprise_services.get_enterprise_by_enterprise_id(enterprise_id)

            # 判断用户是否为企业管理员
            if user_services.is_user_admin_in_current_enterprise(user_obj, enterprise.enterprise_id):
                bean_dict = {"user_info": user_obj.to_dict()}
                return Response(generate_result("0000", "success", "当前用户已经是企业管理员，已同步至管理后台", bean_dict))
            # 添加企业管理员
            enterprise_user_perm_repo.create_enterprise_user_perm(user_obj.user_id, enterprise.enterprise_id, "admin")
            bean = {"user_info": user_obj.to_dict()}

            result = generate_result("0000", "success", "添加成功", bean=bean)

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def delete(self, request, *args, **kwargs):
        """
        管理后台删除企业管理员
        """
        try:
            user_id = request.data.get("user_id", None)
            # 校验参数
            if not user_id:
                return Response(generate_result("1003", "params error", "参数错误"))
            user_perm = enterprise_user_perm_repo.get_backend_enterprise_admin_by_user_id(user_id)
            if not user_perm:
                return Response(generate_result("1006", "The current user is not an enterprise administrator",
                                                "当前用户不是企业管理员"))
            # 最后一个企业管理员无法删除
            admin_count = EnterpriseUserPerm.objects.count()
            logger.debug('-----------count------->{0}'.format(admin_count))
            if admin_count == 1:
                return Response(generate_result("1004", "The last admin", "当前用户为最后一个企业管理员，无法删除"))
            enterprise_user_perm_repo.delete_backend_enterprise_admin_by_user_id(user_id)

            result = generate_result("0000", "success", "删除成功")

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class EnterpriseAdminView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        管理后台查询控制台企业下的企业管理员
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            page = int(request.GET.get("page_num", 1))
            page_size = int(request.GET.get("page_size", 10))
            admins_num = EnterpriseUserPerm.objects.count()
            admin_list = []
            start = (page - 1) * 10
            remaining_num = admins_num - (page - 1) * 10
            end = 10
            if remaining_num < page_size:
                end = remaining_num

            cursor = connection.cursor()
            cursor.execute(
                "select * from enterprise_user_perm order by user_id desc LIMIT {0},{1};".format(start, end))
            admin_tuples = cursor.fetchall()
            logger.debug('---------admin-------------->{0}'.format(admin_tuples))
            for admin in admin_tuples:
                user = user_repo.get_by_user_id(user_id=admin[1])
                bean = dict()
                if user:
                    bean["nick_name"] = user.nick_name
                    bean["phone"] = user.phone
                    bean["email"] = user.email
                    bean["create_time"] = time_to_str(user.create_time, "%Y-%m-%d %H:%M:%S")
                    bean["user_id"] = user.user_id
                admin_list.append(bean)
            result = generate_result("0000", "success", "查询成功", list=admin_list, total=admins_num)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class SetUserPasswordView(BaseAPIView):
    def put(self, request, *args, **kwargs):
        """
        管理后台修改用户密码
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            new_password = request.data.get('new_password')
            re_password = request.data.get("re_password")
            username = request.data.get('username')
            if not username or not re_password or not new_password:
                logger.debug('===================')
                return Response(generate_result("1003", "params error", "参数错误"))
            if new_password != re_password:
                return Response(generate_result("1010", "two password disagree", "两个密码不一致"))

            user_obj = user_service.get_user_by_username(username)
            # 修改密码
            status, info = user_services.update_password(user_id=user_obj.user_id, new_password=new_password)
            if status:
                result = generate_result("0000", "change password success", "密码修改成功")
            else:
                result = generate_result("1004", "password change failed", "密码修改失败")

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)
