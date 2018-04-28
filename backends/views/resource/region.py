# -*- coding: utf8 -*-

import logging

from rest_framework.response import Response

from backends.services.exceptions import *
from backends.services.regionservice import region_service
from backends.services.resultservice import *
from backends.services.clusterservice import cluster_service
from backends.views.base import BaseAPIView
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class RegionView(BaseAPIView):

    def get(self, request, *args, **kwargs):
        """
        同步数据中心信息
        ---
        """
        try:
            regions = region_service.get_all_regions()
            regions_info = []
            if regions:
                for r in regions:
                    clusters = cluster_service.get_cluster_by_region(r.region_id)
                    if not clusters:
                        cluster_id = make_uuid()
                        cluster_alias = r.region_alias + u"-集群A"
                        cluster_name = r.region_name + "-" + "c1"
                        cluster_info = cluster_service.add_cluster(r.region_id, cluster_id, cluster_name, cluster_alias,
                                                                   True)
                        clusters = [cluster_info]
                    bean = r.to_dict()
                    bean.update({"clusters": [c.to_dict() for c in clusters]})
                    regions_info.append(bean)
            result = generate_result("0000", "success", "查询成功", list=regions_info)

        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def post(self, request, *args, **kwargs):
        """
        添加数据中心
        ---
        parameters:
            - name: region_id
              description: 数据中心id
              required: true
              type: string
              paramType: form
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
            - name: wsurl
              description: 数据中心websocket访问地址
              required: true
              type: string
              paramType: form
            - name: httpdomain
              description: 数据中心http访问根域名
              required: true
              type: string
              paramType: form
            - name: tcpdomain
              description: 数据中心tpc访问根域名
              required: true
              type: string
              paramType: form
            - name: desc
              description: 数据中心描述
              required: false
              type: string
              paramType: form
            - name: scope
              description: 数据中心类型 公有|私有
              required: true
              type: string
              paramType: form

        """
        try:
            region_name = request.data.get("region_name", None)
            region_id = request.data.get("region_id", None)
            region_alias = request.data.get("region_alias", None)
            url = request.data.get("url", None)
            token = request.data.get("token", None)
            wsurl = request.data.get("wsurl", None)
            httpdomain = request.data.get("httpdomain", None)
            tcpdomain = request.data.get("tcpdomain", None)
            desc = request.data.get("desc", "")
            scope = request.data.get("scope", None)

            is_success, msg, region_info = region_service.add_region(region_id, region_name, region_alias, url, token,
                                                                     wsurl, httpdomain,
                                                                     tcpdomain, desc, scope)
            if not is_success:
                result = generate_result("2001", "add console region error", msg)
            else:
                result = generate_result("0000", "success", "添加成功", region_info.to_dict())
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class RegionDetailView(BaseAPIView):

    def put(self, request, region_id, *args, **kwargs):
        """
        修改数据中心
        ---
        parameters:
        -   name: body
            description: 修改内容 字段有 region_name,region_alias,url,token,wsurl,httpdomain,tcpdomain,scope,desc,status(上下线)
            required: true
            type: string
            paramType: body
        """
        try:
            data = request.data
            params = {}
            for k, v in data.iteritems():
                params[k] = v
            is_success, msg = region_service.update_region(region_id, **params)
            if not is_success:
                result = generate_result("2002", "update cloudband region info error", msg)
            else:
                result = generate_result("0000", "success", "修改成功")
        except RegionNotExistError as e:
            result = generate_result("2002", "region not exist", e.message)
        except RegionExistError as e:
            result = generate_result("2001", "region exist", e.message)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)

    def delete(self,request,region_id,*args,**kwargs):
        """
        删除数据中心
        ---
         parameters:
            - name: region_id
              description: 租户id
              required: true
              type: string
              paramType: path
        """
        try:
            region_service.delete_region_by_region_id(region_id)
            result = generate_result("0000", "success", "数据中心删除成功")
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
            if action not in ("online","offline","maintain", "cancel_maintain"):
                raise ParamsError("参数错误")
            msg_show = "操作成功"
            if action == "online":
                msg_show = "上线成功"
            elif action == "offline":
                msg_show = "下线成功"
            elif action == "maintain":
                msg_show = "已将数据中心设置为维护中"
            elif action == "cancel_maintain":
                msg_show = "已取消数据中心维护状态"
            region_service.region_status_mange(region_id, action)
            code = "0000"
            msg = "success"
            result = generate_result(code, msg, msg_show)
        except RegionNotExistError as e:
            result = generate_result("2002", "region not exist", e.message)
        except RegionUnreachableError as e:
            msg_show = "数据中心无法访问,请查看相关配置是否正确"
            result = generate_result("2003", "region unreachable", msg_show)
        except ParamsError as e:
            result = generate_result("1003", "params error", "参数错误")
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)
