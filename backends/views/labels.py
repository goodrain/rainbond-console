# -*- coding: utf8 -*-
import logging
from backends.services.exceptions import *

from rest_framework.response import Response
from backends.views.base import BaseAPIView
from backends.services.labelservice import label_service
from backends.services.resultservice import *
from www.models.label import Labels

logger = logging.getLogger("default")


class AllLabelsView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取标签
        ---
        parameters:
            - name: label_alias
              description: 标签中文名
              required: false
              type: string
              paramType: query

        """
        try:
            label_alias = request.GET.get("label_alias", None)
            labels = label_service.get_label_usage(label_alias)
            result = generate_result(
                "0000", "success", "查询成功", list=labels
            )
        except LabelNotExistError as e:
            result = generate_result("6001", "label not exist", e.message)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def post(self, request, *args, **kwargs):
        """
        添加标签
        ---
        parameters:
            - name: label_alias
              description: 标签中文名
              required: true
              type: string
              paramType: form
        """
        try:
            region_alias = request.data.get("label_alias", None)
            label_service.add_label(region_alias)
            result = generate_result("0000", "success", "标签添加成功")
        except ParamsError as e:
            result = generate_result("1001", "param error", e.message)
        except LabelExistError as e:
            result = generate_result("6002", "label exist", e.message)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class LabelView(BaseAPIView):
    def delete(self, request, label_id, *args, **kwargs):
        """
        删除标签
        ---
        parameters:
            - name: label_id
              description: 标签ID
              required: true
              type: string
              paramType: path
        """
        try:
            label = label_service.delete_label(label_id)
            result = generate_result("0000", "success", "标签{0}删除成功".format(label.label_alias))
        except Labels.DoesNotExist as e:
            result = generate_result("6001", "label not exist", "标签不存在")
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class QueryLabelView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        模糊查询标签
        ---
        parameters:
            - name: label_alias
              description: 模糊标签名称
              required: true
              type: string
              paramType: query

        """
        try:
            label_alias = request.GET.get("label_alias", None)
            label_list = []
            if label_alias:
                label_list = label_service.get_fuzzy_labels(label_alias)
            labels = []
            for label in label_list:
                labels.append(label.to_dict())
            result = generate_result("0000", "success", "查询成功", list=labels)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

