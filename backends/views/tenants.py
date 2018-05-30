# -*- coding: utf8 -*-
import logging
import json
from rest_framework.response import Response
from backends.services.exceptions import TenantNotExistError, ParamsError
from backends.services.regionservice import region_service
from backends.services.resultservice import *
from backends.services.tenantservice import tenant_service
from base import BaseAPIView

logger = logging.getLogger("default")


class TenantsView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        模糊查询团队
        ---
        parameters:
            - name: tenant_name
              description: 模糊团队名称
              required: false
              type: string
              paramType: query
            - name: tenant_alias
              description: 模糊团队别名
              required: false
              type: string
              paramType: query

        """
        try:
            tenant_name = request.GET.get("tenant_name", None)
            tenant_alias = request.GET.get("tenant_alias", None)
            tenant_list = []
            if tenant_name:
                tenant_list = tenant_service.get_fuzzy_tenants_by_tenant_name(tenant_name)
            if tenant_alias:
                tenant_list = tenant_service.get_fuzzy_tenants_by_tenant_alias(tenant_alias)
            tenants = []
            for tenant in tenant_list:
                id_name_pair = {}
                id_name_pair["tenant_name"] = tenant.tenant_name
                id_name_pair["tenant_id"] = tenant.tenant_id
                id_name_pair["tenant_alias"] = tenant.tenant_alias
                tenants.append(id_name_pair)
            result = generate_result("0000", "success", "查询成功", list=tenants)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class TenantRegionResourceView(BaseAPIView):

    def post(self, request, *args, **kwargs):
        """
        获取团队资源使用
        ---
        parameters:
            - name: tenant_name
              description: 租户名
              required: false
              type: string
              paramType: form
            - name: region_id
              description: 数据中心ID
              required: false
              type: string
              paramType: form
            - name: page_num
              description: 页码
              required: false
              type: string
              paramType: form
            - name: page_size
              description: 每页数量
              required: false
              type: string
              paramType: form

        """

        try:
            tenant_name = request.data.get("tenant_name", None)
            region_id = request.data.get("region_id", None)
            page_num = int(request.data.get("page_num", 1))
            page_size = int(request.data.get("page_size", 10))

            total, list = region_service.get_tenant_resources(tenant_name, region_id, page_num, page_size)
            # sorted_list = sorted(list, key=lambda service: service["allocate_memory"],reverse=True)
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, list=list, total=total, page_size=page_size)
        except ParamsError as e:
            result = generate_result("1001","param error",e.message)
        except TenantNotExistError as e:
            result = generate_result("5001","tenant not exist",e.message)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)


class TenantRegionRealResourceView(BaseAPIView):
    def post(self, request, *args, **kwargs):
        """
        获取团队数据中心资源的真实使用
        ---
        parameters:
            - name: body
              description: json内容
              required: true
              type: string
              paramType: body

        """
        try:
            data = request.data.get("body")
            data = json.loads(data)
            statics_list = []
            for region, tenant_id_list in dict(data).iteritems():
                res_list = region_service.get_real_region_tenant_resource(region, tenant_id_list)
                statics_list[0:0] = res_list
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, list=statics_list)
        except Exception as e:
            logger.exception(e)
            result = generate_error_result()
        return Response(result)
