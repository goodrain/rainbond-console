# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app_config import dependency_service
from console.views.app_config.base import AppBaseView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.services.group_service import group_service

logger = logging.getLogger("default")


class AppDependencyView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务依赖的应用
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
            - name: page
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
            page_num = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 25))
            dependencies = dependency_service.get_service_dependencies(self.tenant, self.service)
            service_ids = [s.service_id for s in dependencies]
            service_group_map = group_service.get_services_group_name(service_ids)
            dep_list = []
            for dep in dependencies:
                dep_service_info = {"service_cname": dep.service_cname, "service_id": dep.service_id,
                                    "service_type": dep.service_type, "service_alias": dep.service_alias,
                                    "group_name": service_group_map[dep.service_id]["group_name"],
                                    "group_id": service_group_map[dep.service_id]["group_id"]}
                dep_list.append(dep_service_info)
            rt_list = dep_list[(page_num - 1) * page_size:page_num * page_size]
            result = general_message(200, "success", "查询成功", list=rt_list, total=len(dep_list))
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def post(self, request, *args, **kwargs):
        """
        为应用添加依赖应用
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
            - name: dep_service_id
              description: 依赖的服务的id
              required: true
              type: string
              paramType: form


        """
        dep_service_id = request.data.get("dep_service_id", None)
        if not dep_service_id:
            return Response(general_message(400, "dependency service not specify", u"请指明需要依赖的服务"), status=400)
        try:
            code, msg, data = dependency_service.add_service_dependency(self.tenant, self.service, dep_service_id)
            if code != 200:
                result = general_message(code, "add dependency error", msg)
                return Response(result, status=code)
            result = general_message(code, msg, u"依赖添加成功", bean=data.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def patch(self, request, *args, **kwargs):
        """
        为应用添加依赖应用
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
            - name: dep_service_ids
              description: 依赖的服务的id,多个依赖的服务id，以英文逗号分隔
              required: true
              type: string
              paramType: form

        """
        dep_service_ids = request.data.get("dep_service_ids", None)
        if not dep_service_ids:
            return Response(general_message(400, "dependency service not specify", u"请指明需要依赖的服务"), status=400)
        try:
            dep_service_list = dep_service_ids.split(",")
            code, msg = dependency_service.patch_add_dependency(self.tenant, self.service, dep_service_list)
            if code != 200:
                result = general_message(code, "add dependency error", msg)
                return Response(result, status=code)
            result = general_message(code, msg, u"依赖添加成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppNotDependencyView(AppBaseView):
    @never_cache
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取服务可以依赖但未依赖的应用
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
            - name: page
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
            page_num = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 25))
            un_dependencies = dependency_service.get_undependencies(self.tenant, self.service)
            service_ids = [s.service_id for s in un_dependencies]
            service_group_map = group_service.get_services_group_name(service_ids)
            un_dep_list = []
            for un_dep in un_dependencies:
                dep_service_info = {"service_cname": un_dep.service_cname, "service_id": un_dep.service_id,
                                    "service_type": un_dep.service_type, "service_alias": un_dep.service_alias,
                                    "group_name": service_group_map[un_dep.service_id]["group_name"],
                                    "group_id": service_group_map[un_dep.service_id]["group_id"]}
                un_dep_list.append(dep_service_info)
            rt_list = un_dep_list[(page_num - 1) * page_size:page_num * page_size]
            result = general_message(200, "success", "查询成功", list=rt_list, total=len(un_dep_list))
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class AppDependencyManageView(AppBaseView):
    @never_cache
    @perm_required('manage_service_config')
    def delete(self, request, *args, **kwargs):
        """
        删除应用的某个依赖
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
            - name: dep_service_id
              description: 需要删除的服务ID
              required: true
              type: string
              paramType: path

        """
        dep_service_id = kwargs.get("dep_service_id", None)
        if not dep_service_id:
            return Response(general_message(400, "attr_name not specify", u"未指定需要删除的依赖服务"))
        try:
            code, msg, dependency = dependency_service.delete_service_dependency(self.tenant, self.service,
                                                                                 dep_service_id)
            if code != 200:
                return Response(general_message(code, "delete dependency error", msg))

            result = general_message(200, "success", u"删除成功", bean=dependency.to_dict())
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])
