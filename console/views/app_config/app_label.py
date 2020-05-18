# -*- coding: utf8 -*-
"""
  Created on 18/1/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.services.app_config import label_service
from console.views.app_config.base import AppBaseView
from www.decorator import perm_required
from www.utils.return_message import general_message, error_message
from console.repositories.label_repo import label_repo, node_label_repo, service_label_repo

logger = logging.getLogger("default")


class AppLabelView(AppBaseView):
    @never_cache
    # @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取组件已使用和未使用的标签
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
        result = {}
        try:
            bean = label_service.get_service_labels(self.service)
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    # @perm_required('manage_service_config')
    def post(self, request, *args, **kwargs):
        """
        添加组件标签
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
              description: 组件标签 ["label_id1","label_id2"]
              required: true
              type: string
              paramType: body
        """
        result = {}
        try:
            label_ids = request.data.get("label_ids", None)
            if not label_ids:
                return Response(general_message(400, "param error", "标签ID未指定"), status=400)

            code, msg, event = label_service.add_service_labels(self.tenant, self.service, label_ids)
            if code != 200:
                return Response(general_message(code, "add labels error", msg), status=code)
            result = general_message(200, "success", "标签添加成功")
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])

    @never_cache
    # @perm_required('manage_service_config')
    def delete(self, request, *args, **kwargs):
        """
        删除组件标签
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
            - name: label_id
              description: 组件标签 id
              required: true
              type: string
              paramType: form
        """
        result = {}
        # try:
        label_id = request.data.get("label_id", None)
        if not label_id:
            return Response(general_message(400, "param error", "标签ID未指定"), status=400)
        service_label = service_label_repo.get_service_label(self.service.service_id, label_id)
        if not service_label:
            return Response(general_message(400, "tag does not exist", "标签不存在"), status=400)
        code, msg, event = label_service.delete_service_label(self.tenant, self.service, label_id)
        if code != 200:
            return Response(general_message(code, "add labels error", msg), status=code)
        result = general_message(200, "success", "标签删除成功")
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        return Response(result, status=result["code"])


# 添加特性获取可用标签
class AppLabelAvailableView(AppBaseView):
    @never_cache
    # @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        添加特性获取可用标签
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        # try:
        # 节点添加的标签和数据中心查询回来的标签才可被组件使用
        node_labels = node_label_repo.get_all_labels()
        labels_list = list()
        labels_name_list = list()
        if node_labels:
            node_labels_id_list = [label.label_id for label in node_labels]
            label_obj_list = label_repo.get_labels_by_label_ids(node_labels_id_list)
            for label_obj in label_obj_list:
                labels_name_list.append(label_obj.label_name)
        # 查询数据中心可使用的标签
        try:
            code, msg, data_list = label_service.get_region_labels(self.tenant, self.service)
            if code == 200:
                if data_list:
                    label_name_list = []
                    labels = label_repo.get_all_labels()
                    if labels:
                        for label in labels:
                            label_name_list.append(label.label_name)
                    for label_name in data_list:
                        if label_name not in label_name_list:
                            label_repo.create_label(label_name, label_name)
                        labels_name_list.append(label_name)

        except Exception as e:
            logger.exception(e)
            pass

        # 去除该组件已绑定的标签
        service_labels = service_label_repo.get_service_labels(self.service.service_id)
        if service_labels:
            service_labels_id_list = [l.label_id for l in service_labels]
            label_obj_list = label_repo.get_labels_by_label_ids(service_labels_id_list)
            service_labels_name_list = [l.label_name for l in label_obj_list]
            for service_labels_name in service_labels_name_list:
                if service_labels_name in labels_name_list:
                    labels_name_list.remove(service_labels_name)
        for labels_name in labels_name_list:
            label_dict = dict()
            label_oj = label_repo.get_labels_by_label_name(labels_name)
            label_dict["label_id"] = label_oj.label_id
            label_dict["label_alias"] = label_oj.label_alias
            labels_list.append(label_dict)

        result = general_message(200, "success", "查询成功", list=labels_list)
        # except Exception as e:
        #     logger.exception(e)
        #     result = error_message(e.message)
        return Response(result, status=result["code"])
