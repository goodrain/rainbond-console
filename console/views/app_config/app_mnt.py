# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import json
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.repositories.app_config import volume_repo, mnt_repo
from console.services.app import app_service
from console.services.app_config import mnt_service
from console.services.operation_log import operation_log_service, Operation, OperationModule
from console.utils.reqparse import parse_argument
from console.views.app_config.base import AppBaseView
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class AppMntView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件挂载的组件
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
            - name: type
              description: 查询的类别 mnt（已挂载的,默认）| unmnt (未挂载的)
              required: false
              type: string
              paramType: query
            - name: page
              description: 页号（默认第一页）
              required: false
              type: integer
              paramType: query
            - name: page_size
              description: 每页大小(默认10)
              required: false
              type: integer
              paramType: query

        """
        dep_app_name = request.GET.get("dep_app_name", "")
        if dep_app_name == "undefined":
            dep_app_name = ""
        dep_app_group = request.GET.get("dep_app_group", "")
        if dep_app_group == "undefined":
            dep_app_group = ""
        config_name = request.GET.get("config_name", "")
        query_type = request.GET.get("type", "mnt")
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", 10)
        volume_types = parse_argument(request, 'volume_types', value_type=list)
        is_config = parse_argument(request, 'is_config', value_type=bool, default=False)

        if volume_types is not None and ('config-file' in volume_types):
            is_config = True

        if query_type == "mnt":
            mnt_list, total = mnt_service.get_service_mnt_details(self.tenant, self.service, volume_types)
        elif query_type == "unmnt":
            services = app_service.get_app_list(self.tenant.tenant_id, self.service.service_region, dep_app_name)
            services_ids = [s.service_id for s in services]
            mnt_list, total = mnt_service.get_service_unmount_volume_list(self.tenant, self.service, services_ids, page,
                                                                          page_size, is_config, dep_app_group, config_name)
        else:
            return Response(general_message(400, "param error", "参数错误"), status=400)
        result = general_message(200, "success", "查询成功", list=mnt_list, total=total)

        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        为组件添加挂载依赖
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
            - name: body
              description: 批量添加挂载[{"id":49,"path":"/add"},{"id":85,"path":"/dadd"}]
              required: true
              type: string
              paramType: body

        """
        dep_vol_data = request.data["body"]
        dep_vol_data = json.loads(dep_vol_data)
        mnt_service.batch_mnt_serivce_volume(self.tenant, self.service, dep_vol_data, self.user.nick_name)
        result = general_message(200, "success", "操作成功")
        volume_a, mnt_type = handle_mnt_info(dep_vol_data[0]["id"])
        suffix = " 挂载了{0} {1}".format(mnt_type, volume_a.volume_name)
        if len(dep_vol_data) > 1:
            volume_b, _ = handle_mnt_info(dep_vol_data[1]["id"])
            suffix = " 挂载了 {0}、{1} 等{2}".format(volume_a.volume_name, volume_b.volume_name, mnt_type)
        new_mnt_list = mnt_service.get_service_mnt_details_byid(dep_vol_data)
        new_information = json.dumps(new_mnt_list, ensure_ascii=False)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.FOR,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=suffix)
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            new_information=new_information)
        return Response(result, status=result["code"])


class AppMntManageView(AppBaseView):
    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        为组件取消挂载依赖
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
            - name: dep_vol_id
              description: 挂载的组件持久化ID
              required: true
              type: string
              paramType: path

        """
        dep_vol_id = kwargs.get("dep_vol_id", None)
        mnt = volume_repo.get_service_volume_by_id(id=dep_vol_id)
        path = mnt_repo.get_mnt_relation_by_id(
            service_id=self.service.service_id, dep_service_id=mnt.service_id, mnt_name=mnt.volume_name).mnt_dir

        old_mnt_list = mnt_service.get_service_mnt_details_byid([{"path": path, "id": dep_vol_id}])

        code, msg = mnt_service.delete_service_mnt_relation(self.tenant, self.service, dep_vol_id, self.user.nick_name)

        if code != 200:
            return Response(general_message(code, "add error", msg), status=code)

        old_information = json.dumps(old_mnt_list[0], ensure_ascii=False)
        if code != 200:
            return Response(general_message(code, "add error", msg), status=code)
        result = general_message(200, "success", "操作成功")
        volume, mnt_type = handle_mnt_info(dep_vol_id)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.CANCEL,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=" 挂载的{0} {1}".format(mnt_type, volume.volume_name))
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            old_information=old_information,
        )
        return Response(result, status=result["code"])


def handle_mnt_info(dependency_volume_id):
    volume = volume_repo.get_service_volume_by_pk(dependency_volume_id)
    if not volume:
        return
    if volume.volume_type == "config-file":
        mnt_type = OperationModule.SHARED_CONFIG_FILE.value
    else:
        mnt_type = OperationModule.SHARED_STORAGE.value
    return volume, mnt_type