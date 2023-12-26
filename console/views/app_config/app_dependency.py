# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from console.services.app_config import dependency_service, port_service
from console.services.group_service import group_service
from console.views.app_config.base import AppBaseView
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from www.utils.return_message import general_message
from console.exception.main import AbortRequest

logger = logging.getLogger("default")


class AppDependencyReverseView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件可以被依赖但未依赖的组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
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
            - name: search_key
              description: 搜索关键字
              required: false
              type: string
              paramType: query
            - name: condition
              description: 模糊搜索条件，按组名还是按组件名 group_name|service_name
              required: false
              type: string
              paramType: query
        """
        page_num = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 25))
        search_key = request.GET.get("search_key", None)
        condition = request.GET.get("condition", None)
        un_dependencies = dependency_service.get_reverse_undependencies(self.tenant, self.service)
        service_ids = [s.service_id for s in un_dependencies]
        service_group_map = group_service.get_services_group_name(service_ids)
        un_dep_list = []
        for un_dep in un_dependencies:
            dep_service_info = {
                "service_cname": un_dep.service_cname,
                "service_id": un_dep.service_id,
                "service_type": un_dep.service_type,
                "service_alias": un_dep.service_alias,
                "group_name": service_group_map[un_dep.service_id]["group_name"],
                "group_id": service_group_map[un_dep.service_id]["group_id"]
            }
            if search_key is not None and condition and condition != "group_name" and condition!="service_name":
                result = general_message(400, "error", "condition参数错误")
                return Response(result, status=400)

            if search_key is not None and condition:
                if condition == "group_name" and search_key.lower() in service_group_map[un_dep.service_id]["group_name"].lower():
                    un_dep_list.append(dep_service_info)
                if condition == "service_name" and search_key.lower() in un_dep.service_cname.lower():
                    un_dep_list.append(dep_service_info)

            elif search_key is not None and not condition:
                if search_key.lower() in service_group_map[
                        un_dep.service_id]["group_name"].lower() or search_key.lower() in un_dep.service_cname.lower():
                    un_dep_list.append(dep_service_info)
            elif search_key is None and not condition:
                un_dep_list.append(dep_service_info)

        rt_list = un_dep_list[(page_num - 1) * page_size:page_num * page_size]
        result = general_message(200, "success", "查询成功", list=rt_list, total=len(un_dep_list))
        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        反向依赖，让其他的组件来依赖自己
        ---
        parameters:
         - name: tenantName
           description: 租户名
           required: true
           type: string
           paramType: path
         - name: serviceAlias
           description: 组件别名
           required: true
           type: string
           paramType: path
         - name: be_dep_service_id
           description: 被依赖的组件的id
           required: true
           type: string
           paramType: form
        """
        be_dep_service_ids = request.data.get("be_dep_service_ids", None)
        # open_inner = request.data.get("open_inner", False)
        # container_port = request.data.get("container_port", None)
        if not be_dep_service_ids:
            return Response(general_message(400, "dependency service not specify", "请指明谁要依赖你"), status=400)
        if self.service.is_third_party():
            raise AbortRequest(msg="third-party components cannot add dependencies", msg_show="第三方组件不能添加依赖组件")
        if self.service.service_id in be_dep_service_ids:
            raise AbortRequest(msg="components cannot rely on themselves", msg_show="组件不能依赖自己")

        # 这一步真的去添加依赖
        try:
            data = dependency_service.patch_add_service_reverse_dependency(
                self.tenant, self.service, be_dep_service_ids=be_dep_service_ids, user_name=self.user.nick_name)
            result = general_message(200,"success", "依赖添加成功", list=data)
            return Response(result, status=result["code"])
        except Exception as e:
            logger.error("重复依赖添加失败",e)
        result = general_message(400, "error", "依赖添加失败")
        return Response(result, status=result["code"])



class AppDependencyView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件依赖的组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
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
        page_num = int(request.GET.get("page", 1))
        if page_num < 1:
            page_num = 1
        page_size = int(request.GET.get("page_size", 25))
        dependencies = dependency_service.get_service_dependencies(self.tenant, self.service)
        service_ids = [s.service_id for s in dependencies]
        service_group_map = group_service.get_services_group_name(service_ids)
        dep_list = []
        for dep in dependencies:
            tenant_service_ports = port_service.get_service_ports(dep)
            ports_list = []
            if tenant_service_ports:
                for port in tenant_service_ports:
                    ports_list.append(port.container_port)
            dep_service_info = {
                "service_cname": dep.service_cname,
                "service_id": dep.service_id,
                "service_type": dep.service_type,
                "service_alias": dep.service_alias,
                "group_name": service_group_map[dep.service_id]["group_name"],
                "group_id": service_group_map[dep.service_id]["group_id"],
                "ports_list": ports_list
            }
            dep_list.append(dep_service_info)
        start = (page_num - 1) * page_size
        end = page_num * page_size
        if start >= len(dep_list):
            start = len(dep_list) - 1
            end = len(dep_list) - 1
        rt_list = dep_list[start:end]

        service_ports = port_service.get_service_ports(self.service)
        port_list = []
        if service_ports:
            for port in service_ports:
                port_list.append(port.container_port)
        bean = {"port_list": port_list, 'total': len(dep_list)}
        result = general_message(200, "success", "查询成功", list=rt_list, total=len(dep_list), bean=bean)
        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        为组件添加依赖组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: dep_service_id
              description: 依赖的组件的id
              required: true
              type: string
              paramType: form


        """
        dep_service_id = request.data.get("dep_service_id", None)
        open_inner = request.data.get("open_inner", False)
        container_port = request.data.get("container_port", None)
        if not dep_service_id:
            return Response(general_message(400, "dependency service not specify", "请指明需要依赖的组件"), status=400)
        if self.service.is_third_party():
            raise AbortRequest(msg="third-party components cannot add dependencies", msg_show="第三方组件不能添加依赖组件")
        if dep_service_id == self.service.service_id:
            raise AbortRequest(msg="components cannot rely on themselves", msg_show="组件不能依赖自己")
        code, msg, data = dependency_service.add_service_dependency(self.tenant, self.service, dep_service_id, open_inner,
                                                                    container_port, self.user.nick_name)
        if code == 201:
            result = general_message(code, "add dependency success", msg, list=data, bean={"is_inner": False})
            return Response(result, status=code)
        if code != 200:
            result = general_message(code, "add dependency error", msg, list=data)
            return Response(result, status=code)
        result = general_message(code, msg, "依赖添加成功", bean=data.to_dict())
        return Response(result, status=result["code"])

    @never_cache
    def patch(self, request, *args, **kwargs):
        """
        为组件添加依赖组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: dep_service_ids
              description: 依赖的组件的id,多个依赖的组件id，以英文逗号分隔
              required: true
              type: string
              paramType: form

        """
        dep_service_ids = request.data.get("dep_service_ids", None)
        if not dep_service_ids:
            return Response(general_message(400, "dependency service not specify", "请指明需要依赖的组件"), status=400)
        if self.service.is_third_party():
            raise AbortRequest(msg="third-party components cannot add dependencies", msg_show="第三方组件不能添加依赖组件")
        dep_service_list = dep_service_ids.split(",")
        code, msg = dependency_service.patch_add_dependency(
            self.tenant, self.service, dep_service_list, user_name=self.user.nick_name)
        if code != 200:
            result = general_message(code, "add dependency error", msg)
            return Response(result, status=code)
        result = general_message(code, msg, "依赖添加成功")
        return Response(result, status=result["code"])


class AppNotDependencyView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件可以依赖但未依赖的组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
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
            - name: search_key
              description: 搜索关键字
              required: false
              type: string
              paramType: query
            - name: condition
              description: 模糊搜索条件，按组名还是按组件名 group_name|service_name
              required: false
              type: string
              paramType: query
        """
        page_num = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 25))
        search_key = request.GET.get("search_key", None)
        condition = request.GET.get("condition", None)
        un_dependencies = dependency_service.get_undependencies(self.tenant, self.service)
        service_ids = [s.service_id for s in un_dependencies]
        service_group_map = group_service.get_services_group_name(service_ids)
        un_dep_list = []
        for un_dep in un_dependencies:
            dep_service_info = {
                "service_cname": un_dep.service_cname,
                "service_id": un_dep.service_id,
                "service_type": un_dep.service_type,
                "service_alias": un_dep.service_alias,
                "group_name": service_group_map[un_dep.service_id]["group_name"],
                "group_id": service_group_map[un_dep.service_id]["group_id"]
            }

            if search_key is not None and condition:
                if condition == "group_name":
                    if search_key.lower() in service_group_map[un_dep.service_id]["group_name"].lower():
                        un_dep_list.append(dep_service_info)
                elif condition == "service_name":
                    if search_key.lower() in un_dep.service_cname.lower():
                        un_dep_list.append(dep_service_info)
                else:
                    result = general_message(400, "error", "condition参数错误")
                    return Response(result, status=400)
            elif search_key is not None and not condition:
                if search_key.lower() in service_group_map[
                        un_dep.service_id]["group_name"].lower() or search_key.lower() in un_dep.service_cname.lower():
                    un_dep_list.append(dep_service_info)
            elif search_key is None and not condition:
                un_dep_list.append(dep_service_info)

        rt_list = un_dep_list[(page_num - 1) * page_size:page_num * page_size]
        result = general_message(200, "success", "查询成功", list=rt_list, total=len(un_dep_list))
        return Response(result, status=result["code"])


class AppDependencyManageView(AppBaseView):
    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        删除组件的某个依赖
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: dep_service_id
              description: 需要删除的组件ID
              required: true
              type: string
              paramType: path

        """
        dep_service_id = kwargs.get("dep_service_id", None)
        if not dep_service_id:
            return Response(general_message(400, "attr_name not specify", "未指定需要删除的依赖组件"))
        code, msg, dependency = dependency_service.delete_service_dependency(self.tenant, self.service, dep_service_id,
                                                                             self.user.nick_name)
        if code != 200:
            return Response(general_message(code, "delete dependency error", msg))

        result = general_message(200, "success", "删除成功", bean=dependency.to_dict())
        return Response(result, status=result["code"])
