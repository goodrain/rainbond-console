# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from backends.services.exceptions import *
from backends.services.resultservice import *
from backends.services.tenantservice import tenant_service
from backends.services.userservice import user_service
from base import BaseAPIView
from goodrain_web.tools import JuncheePaginator
from www.models import Tenants, PermRelTenant

logger = logging.getLogger("default")


class AllTeamView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取所有租户信息
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

        """
        try:
            page = request.GET.get("page_num", 1)
            page_size = request.GET.get("page_size", 20)
            tenant_list = tenant_service.get_all_tenants()
            tenant_paginator = JuncheePaginator(tenant_list, int(page_size))
            tenants = tenant_paginator.page(int(page))
            tenants_num = Tenants.objects.count()
            allow_num = 9999999

            list = []

            for tenant in tenants:
                tenant_dict = {}
                user_list = tenant_service.get_tenant_users(tenant["tenant_name"])
                tenant_dict["user_num"] = len(user_list)
                tenant_dict.update(tenant)
                list.append(tenant_dict)
            bean = {"total_tenant_num": allow_num, "cur_tenant_num": tenants_num}

            result = generate_result(
                "0000", "success", "查询成功", bean=bean, list=list, total=tenant_paginator.count
            )
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

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
            - name: useable_regions
              description: 可用数据中心 ali-sh,ali-hz
              required: false
              type: string
              paramType: form
        """
        try:
            tenant_name = request.data.get("tenant_name", None)
            useable_regions = request.data.get("useable_regions", "")
            regions = []
            if useable_regions:
                regions = useable_regions.split(",")
            tenant = tenant_service.add_tenant(tenant_name, None, regions)
            bean = {"tenant_name": tenant.tenant_name, "tenant_id": tenant.tenant_id, "user_num": 0}
            result = generate_result("0000", "success", "租户添加成功", bean=bean)
        except TenantOverFlowError as e:
            result = generate_result("7001", "tenant over flow", "{}".format(e.message))
        except TenantExistError as e:
            result = generate_result("7002", "tenant exist", "{}".format(e.message))
        except NoEnableRegionError as e:
            result = generate_result("7003", "no enable region", "{}".format(e.message))
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
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
            user_list = tenant_service.get_users_by_tenantID(tenant.ID)
            user_num = len(user_list)
            list = [{"tenant_id": tenant.tenant_id, "tenant_name": tenant.tenant_name, "user_num": user_num}]
            result = generate_result("0000", "success", "查询成功", list=list)
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
            - name: user_name
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
        """
        try:
            user_name = request.data.get("user_name", None)
            if not user_name:
                raise ParamsError("用户名为空")
            user = user_service.get_user_by_username(user_name)
            tenant = tenant_service.get_tenant(tenant_name)
            tenant_service.add_user_to_tenant(tenant, user)
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
