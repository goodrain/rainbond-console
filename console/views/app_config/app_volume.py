# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import re
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.repositories.app_config import volume_repo
from console.services.app_config import mnt_service
from console.services.app_config import volume_service
from console.services.operation_log import operation_log_service, Operation
from console.utils.reqparse import parse_argument
from console.views.app_config.base import AppBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message
from console.exception.main import AbortRequest

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


def ensure_volume_mode(mode):
    if type(mode) != int:
        raise AbortRequest("mode be a number between 0 and 777 (octal)", msg_show="权限必须是在0和777之间的八进制数")
    regex = re.compile(r"^[0-7]{1,3}$")
    if not regex.match(str(mode)):
        raise AbortRequest("mode be a number between 0 and 777 (octal)", msg_show="权限必须是在0和777之间的八进制数")
    return mode


class AppVolumeOptionsView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件可用的存储列表
        ---
        parameters:
        """
        volume_types = volume_service.get_service_support_volume_options(self.tenant, self.service)
        result = general_message(200, "success", "查询成功", list=volume_types)
        return Response(result, status=result["code"])


class AppVolumeView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件的持久化路径
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
        """
        is_config = parse_argument(request, 'is_config', value_type=bool, default=False)

        volumes = volume_service.get_service_volumes(self.tenant, self.service, is_config)
        volumes_list = []
        if is_config:
            for tenant_service_volume in volumes:
                volume = volume_repo.get_service_volume_by_pk(tenant_service_volume["ID"])
                cf_file = volume_repo.get_service_config_file(volume)
                if cf_file:
                    tenant_service_volume["file_content"] = cf_file.file_content
                volumes_list.append(tenant_service_volume)
        else:
            dependents = mnt_service.get_volume_dependent(self.tenant, self.service)
            name2deps = {}
            if dependents:
                for dep in dependents:
                    if name2deps.get(dep["volume_name"], None) is None:
                        name2deps[dep["volume_name"]] = []
                    name2deps[dep["volume_name"]].append(dep)
            for vo in volumes:
                vo["dep_services"] = name2deps.get(vo["volume_name"], None)
                volumes_list.append(vo)
        if volumes_list and len(volumes_list) > 0:
            volumes_list[0]["first"] = True
        result = general_message(200, "success", "查询成功", list=volumes_list)
        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, *args, **kwargs):
        """
        为组件添加持久化目录
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
            - name: volume_name
              description: 持久化名称
              required: true
              type: string
              paramType: form
            - name: volume_type
              description: 持久化类型
              required: true
              type: string
              paramType: form
            - name: volume_path
              description: 持久化路径
              required: true
              type: string
              paramType: form

        """
        volume_name = request.data.get("volume_name", None)
        r = re.compile('(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])$')
        if not r.match(volume_name):
            raise AbortRequest(msg="volume name illegal", msg_show="持久化名称只支持数字字母下划线")
        volume_type = request.data.get("volume_type", None)
        volume_path = request.data.get("volume_path", None)
        file_content = request.data.get("file_content", None)
        volume_capacity = request.data.get("volume_capacity", 0)
        provider_name = request.data.get("volume_provider_name", '')
        access_mode = request.data.get("access_mode", '')
        share_policy = request.data.get('share_policy', '')
        backup_policy = request.data.get('back_policy', '')
        reclaim_policy = request.data.get('reclaim_policy', '')  # TODO fanyangyang 使用serialer进行参数校验
        allow_expansion = request.data.get('allow_expansion', False)
        mode = request.data.get("mode")
        if mode is not None:
            mode = ensure_volume_mode(mode)

        settings = {}
        settings['volume_capacity'] = volume_capacity
        settings['provider_name'] = provider_name
        settings['access_mode'] = access_mode
        settings['share_policy'] = share_policy
        settings['backup_policy'] = backup_policy
        settings['reclaim_policy'] = reclaim_policy
        settings['allow_expansion'] = allow_expansion
        new_information = volume_service.json_service_volume(
            volume_type=volume_type,
            volume_name=volume_name,
            volume_path=volume_path,
            volume_cap=volume_capacity,
            mode=mode,
            file_content=file_content)
        data = volume_service.add_service_volume(
            self.tenant,
            self.service,
            volume_path,
            volume_type,
            volume_name,
            file_content,
            settings,
            self.user.nick_name,
            mode=mode)
        result = general_message(200, "success", "持久化路径添加成功", bean=data.to_dict())
        src_suffix = " 下的配置文件 {}".format(volume_name) if volume_type == "config-file" else " 下的存储 {}".format(volume_name)

        comment = operation_log_service.generate_component_comment(
            operation=Operation.ADD,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=src_suffix)
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            new_information=new_information)
        return Response(result, status=result["code"])


class AppVolumeManageView(AppBaseView):
    @never_cache
    def delete(self, request, *args, **kwargs):
        """
        删除组件的某个持久化路径
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
            - name: volume_id
              description: 需要删除的持久化ID
              required: true
              type: string
              paramType: path

        """
        force = request.GET.get("force", None)
        volume_id = kwargs.get("volume_id", None)
        if not volume_id:
            return Response(general_message(400, "attr_name not specify", "未指定需要删除的持久化路径"), status=400)
        volume = volume_repo.get_service_volume_by_pk(volume_id)
        file_content = ""
        if volume.volume_type == "config-file":
            file_content = volume_repo.get_service_config_file(volume).file_content
        old_information = volume_service.json_service_volume(
            volume_name=volume.volume_name,
            volume_path=volume.volume_path,
            mode=volume.mode,
            file_content=file_content,
            volume_cap=volume.volume_capacity,
            volume_type=volume.volume_type)
        code, msg, volume = volume_service.delete_service_volume_by_id(self.tenant, self.service, int(volume_id),
                                                                       self.user.nick_name, force)
        if code != 200:
            result = general_message(code=code, msg="delete volume error", msg_show=msg, list=volume)
            return Response(result, status=result["code"])
        result = general_message(200, "success", "删除成功")
        src_suffix = " 下的配置文件 {}".format(
            volume.volume_name) if volume.volume_type == "config-file" else " 下的存储 {}".format(
            volume.volume_name)
        comment = operation_log_service.generate_component_comment(
            operation=Operation.DELETE,
            module_name=self.service.service_cname,
            region=self.service.service_region,
            team_name=self.tenant.tenant_name,
            service_alias=self.service.service_alias,
            suffix=src_suffix)
        operation_log_service.create_component_log(
            user=self.user,
            comment=comment,
            enterprise_id=self.user.enterprise_id,
            team_name=self.tenant.tenant_name,
            app_id=self.app.ID,
            service_alias=self.service.service_alias,
            old_information=old_information)
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, *args, **kwargs):
        """
        修改存储设置
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        # try:
        volume_id = kwargs.get("volume_id", None)
        new_volume_path = request.data.get("new_volume_path", None)
        new_file_content = request.data.get("new_file_content", None)
        if not volume_id:
            return Response(general_message(400, "volume_id is null", "未指定需要编辑的配置文件存储"), status=400)
        volume = volume_repo.get_service_volume_by_pk(volume_id)
        if not volume:
            return Response(general_message(400, "volume is null", "存储不存在"), status=400)
        mode = request.data.get("mode")
        if mode is not None:
            mode = ensure_volume_mode(mode)
        service_config = volume_repo.get_service_config_file(volume)
        file_content = ""
        if volume.volume_type == 'config-file':
            if not service_config:
                return Response(general_message(400, "file_content is null", "配置文件内容不存在"), status=400)
            if new_volume_path == volume.volume_path and new_file_content == service_config.file_content and volume.mode == mode:
                return Response(general_message(400, "no change", "没有变化，不需要修改"), status=400)
            file_content = service_config.file_content
        else:
            if new_volume_path == volume.volume_path:
                return Response(general_message(400, "no change", "没有变化，不需要修改"), status=400)

        new_information = volume_service.json_service_volume(
            volume_name=volume.volume_name,
            volume_path=new_volume_path,
            mode=mode,
            file_content=new_file_content,
            volume_type=volume.volume_type,
            volume_cap=volume.volume_capacity)
        old_information = volume_service.json_service_volume(
            volume_name=volume.volume_name,
            volume_path=volume.volume_path,
            mode=volume.mode,
            file_content=file_content,
            volume_type=volume.volume_type,
            volume_cap=volume.volume_capacity)
        data = {
            "volume_name": volume.volume_name,
            "volume_path": new_volume_path,
            "volume_type": volume.volume_type,
            "file_content": new_file_content,
            "operator": self.user.nick_name,
            "mode": mode,
        }
        res, body = region_api.upgrade_service_volumes(self.service.service_region, self.tenant.tenant_name,
                                                       self.service.service_alias, data)
        if res.status == 200:
            volume.volume_path = new_volume_path
            if mode is not None:
                volume.mode = mode
            volume.save()
            if volume.volume_type == 'config-file':
                service_config.volume_name = volume.volume_name
                service_config.file_content = new_file_content
                service_config.save()
            result = general_message(200, "success", "修改成功")
            src_suffix = " 下的配置文件 {}".format(
                volume.volume_name) if volume.volume_type == "config-file" else " 下的存储 {}".format(
                volume.volume_name)
            comment = operation_log_service.generate_component_comment(
                operation=Operation.CHANGE,
                module_name=self.service.service_cname,
                region=self.service.service_region,
                team_name=self.tenant.tenant_name,
                service_alias=self.service.service_alias,
                suffix=src_suffix)
            operation_log_service.create_component_log(
                user=self.user,
                comment=comment,
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                app_id=self.app.ID,
                service_alias=self.service.service_alias,
                old_information=old_information,
                new_information=new_information)
            return Response(result, status=result["code"])
        return Response(general_message(405, "success", "修改失败"), status=405)
