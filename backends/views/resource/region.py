# -*- coding: utf8 -*-

import logging

from rest_framework.response import Response

from backends.services.exceptions import *
from backends.services.regionservice import region_service
from backends.services.resultservice import *
from backends.views.base import BaseAPIView

logger = logging.getLogger("default")


class RegionView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取数据中心
        ---

        """
        try:
            region_list = region_service.get_all_regions(False)
            list = []
            for region in region_list:
                region_info = {}
                region_info['region_name'] = region.region_name
                region_info['region_alias'] = region.region_alias
                region_info['region_id'] = region.region_id
                list.append(region_info)
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, list=list)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def post(self, request, *args, **kwargs):
        """
        添加数据中心
        ---
        parameters:
            - name: region_name
              description: 数据中心英文名称
              required: true
              type: string
              paramType: form
            - name: region_alias
              description: 数据中心中文名
              required: true
              type: string
              paramType: form
            - name: url
              description: url
              required: true
              type: string
              paramType: form
            - name: token
              description: token
              required: true
              type: string
              paramType: form

        """
        try:
            region_name = request.data.get("region_name", None)
            region_alias = request.data.get("region_alias", None)
            url = request.data.get("url", None)
            token = request.data.get("token", None)
            region_service.add_region(region_name, region_alias, url, token)
            code = "0000"
            msg = "success"
            msg_show = "添加成功"
            result = generate_result(code, msg, msg_show)
        except RegionUnreachableError as e:
            result = generate_result("2003","region unreachable","数据中心无法访问,请确认数据中心配置正确")
        except RegionExistError as e:
            result = generate_result("2001", "region exist", e.message)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class RegionDetailView(BaseAPIView):
    def get(self, request, region_id, *args, **kwargs):
        """
        获取某数据中心信息
        ---
        parameters:
            - name: region_id
              description: 租户id
              required: true
              type: string
              paramType: path

        """
        result = {}
        try:
            bean = {}
            region_config = region_service.get_region(region_id)
            bean["region_alias"] = region_config.region_alias
            bean["region_id"] = region_config.region_id
            bean["region_name"] = region_config.region_name
            bean["url"] = region_config.url
            bean["token"] = region_config.token
            result = generate_result(
                "0000", "success", "查询成功", bean=bean
            )
        except Exception as e:
            logger.exception(e)
            result = generate_result("9999", "system error", "系统异常")
        return Response(result)

    def put(self, request, region_id, *args, **kwargs):
        """
        修改数据中心
        ---
        parameters:
        -   name: body
            description: 修改内容 字段有 region_name,region_alias,url,token,status(上下线)
            required: true
            type: string
            paramType: body
        """
        try:
            data = request.data
            params = {}
            for k, v in data.iteritems():
                params[k] = v
            region_service.update_region(region_id, **params)
            code = "0000"
            msg = "success"
            msg_show = "数据中心修改成功"
            result = generate_result(code, msg, msg_show)
        except RegionNotExistError as e:
            result = generate_result("2002", "region not exist", e.message)
        except RegionExistError as e:
            result = generate_result("2001", "region exist", e.message)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class RegionResourceView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取每个数据中心的资源使用
        ---

        """
        try:
            region_list = region_service.get_all_regions()
            statics = region_service.get_all_region_resource(list(region_list))
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, list=statics)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class RegionStatusView(BaseAPIView):
    def put(self, request, region_id, *args, **kwargs):
        """
        数据中心上下线
        ---
        parameters:
            - name: region_id
              description: 租户id
              required: true
              type: string
              paramType: path
            - name: action
              description: 操作类型online:上线 offline下线
              required: true
              type: string
              paramType: form
        """
        try:
            action = request.data.get("action", None)
            if not action:
                raise ParamsError("参数错误")
            if action not in ("online","offline"):
                raise ParamsError("参数错误")
            msg_show = "操作成功"
            if action == "online":
                msg_show = "上线成功"
            elif action == "offline":
                msg_show = "下线成功"
            region_service.region_status_mange(region_id,action)
            code = "0000"
            msg = "success"
            result = generate_result(code, msg, msg_show)
        except RegionNotExistError as e:
            result = generate_result("2002", "region not exist", e.message)
        except RegionUnreachableError as e:
            msg_show = "数据中心无法上线,请查看相关配置是否正确"
            result = generate_result("2003", "region unreachable", msg_show)
        except ParamsError as e:
            result = generate_result("1003", "params error", "参数错误")
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)
