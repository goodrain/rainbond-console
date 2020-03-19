# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.repositories.app_config import volume_repo
from console.services.app_config import volume_service
from console.utils.reqparse import parse_argument
from console.views.app_config.base import AppBaseView
from www.apiclient.regionapi import RegionInvokeApi
from www.decorator import perm_required
from www.utils.return_message import error_message
from www.utils.return_message import general_message

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class AppVolumeOptionsView(AppBaseView):
    @never_cache
    @perm_required('view_service')
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
    @perm_required('view_service')
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
        tenant_service_volumes = volume_service.get_service_volumes(self.tenant, self.service, is_config)
        volumes_list = []
        if is_config:
            for tenant_service_volume in tenant_service_volumes:
                cf_file = volume_repo.get_service_config_file(tenant_service_volume["ID"])
                if cf_file:
                    tenant_service_volume["file_content"] = cf_file.file_content
                volumes_list.append(tenant_service_volume)
        else:
            for vo in tenant_service_volumes:
                volumes_list.append(vo)
        result = general_message(200, "success", "查询成功", list=volumes_list)
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
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
        settings = {}
        settings['volume_capacity'] = volume_capacity
        settings['provider_name'] = provider_name
        settings['access_mode'] = access_mode
        settings['share_policy'] = share_policy
        settings['backup_policy'] = backup_policy
        settings['reclaim_policy'] = reclaim_policy
        settings['allow_expansion'] = allow_expansion

        data = volume_service.add_service_volume(
            self.tenant, self.service, volume_path, volume_type, volume_name, file_content, settings)
        result = general_message(200, "success", u"持久化路径添加成功", bean=data.to_dict())

        return Response(result, status=result["code"])


class AppVolumeManageView(AppBaseView):
    @never_cache
    @perm_required('manage_service_config')
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
        volume_id = kwargs.get("volume_id", None)
        if not volume_id:
            return Response(general_message(400, "attr_name not specify", u"未指定需要删除的持久化路径"), status=400)
        code, msg, volume = volume_service.delete_service_volume_by_id(self.tenant, self.service, int(volume_id))
        if code != 200:
            result = general_message(code=code, msg="delete volume error", msg_show=msg)
        result = general_message(200, "success", u"删除成功", bean=volume.to_dict())
        return Response(result, status=result["code"])

    @never_cache
    @perm_required('manage_service_config')
    def put(self, request, *args, **kwargs):
        """
        修改存储设置
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        try:
            volume_id = kwargs.get("volume_id", None)
            new_volume_path = request.data.get("new_volume_path", None)
            new_file_content = request.data.get("new_file_content", None)
            if not volume_id:
                return Response(general_message(400, "volume_id is null", u"未指定需要编辑的配置文件存储"), status=400)
            volume = volume_repo.get_service_volume_by_pk(volume_id)
            if not volume:
                return Response(general_message(400, "volume is null", u"存储不存在"), status=400)
            service_config = volume_repo.get_service_config_file(volume_id)
            if volume.volume_type == 'config-file':
                if not service_config:
                    return Response(general_message(400, "file_content is null", u"配置文件内容不存在"), status=400)
                if new_volume_path == volume.volume_path and new_file_content == service_config.file_content:
                    return Response(general_message(400, "no change", u"没有变化，不需要修改"), status=400)
            else:
                if new_volume_path == volume.volume_path:
                    return Response(general_message(400, "no change", u"没有变化，不需要修改"), status=400)
            try:
                data = {
                    "volume_name": volume.volume_name,
                    "volume_path": new_volume_path,
                    "volume_type": volume.volume_type,
                    "file_content": new_file_content
                }
                res, body = region_api.upgrade_service_volumes(self.service.service_region, self.tenant.tenant_name,
                                                               self.service.service_alias, data)
                if res.status == 200:
                    volume.volume_path = new_volume_path
                    volume.save()
                    if volume.volume_type == 'config-file':
                        service_config.file_content = new_file_content
                        service_config.save()
                    result = general_message(200, "success", u"修改成功")
                    return Response(result, status=result["code"])
                return Response(general_message(405, "success", u"修改失败"), status=405)
            except Exception as e:
                logger.exception(e)
                result = error_message(e.message)
                return Response(result, status=500)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)
