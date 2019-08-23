# -*- coding: utf-8 -*-
# creater by: barnett
from region_client.api.base import Base


class Tenant(Base):
    def __init__(self, api):
        super(Tenant, self).__init__(api)
        self.api = api

    def list_tenants(self, page=1, pageSize=10, query=None, only_return_body=False):
        list_teanants_path = "/v2/tenants?page={0}&pageSize={1}&query={2}".format(page, pageSize, query)
        re, body = self.api.GET(list_teanants_path)
        if only_return_body:
            return body
        return re, body

    def get_tenant(self, tenant_name, only_return_body=False):
        re, body = self.api.GET("/v2/tenants/{}".format(tenant_name))
        if only_return_body:
            return body
        return re, body

    def update_tenant(self, tenant_name, limit_memory, only_return_body=False):
        update_body = {"limit_memory": limit_memory}
        re, body = self.api.PUT("/v2/tenants/{}".format(tenant_name), body=update_body)
        if only_return_body:
            return body
        return re, body

    def get_region_tenant_number(self, only_return_body=False):
        url = "/v2/resources/tenants/sum"
        res, body = self.api.GET(url)
        if only_return_body:
            return body
        return res, body

    def get_region_fuzzy_tenant_name(self, tenant_name, only_return_body=False):
        url = "/v2/resources/tenants/query/{0}".format(tenant_name)
        res, body = self.api.GET(url)
        if only_return_body:
            return body
        return res, body

    def get_region_tenants_by_page(self, page_num, page_size, only_return_body=False):
        url = "/v2/resources/tenants/res/page/{0}/size/{1}".format(page_num, page_size)
        res, body = self.api.GET(url)
        if only_return_body:
            return body
        return res, body

    def get_region_tenants_by_tenant_name(self, tenant_name, only_return_body=False):
        url = "/v2/resources/tenants/{0}/res".format(tenant_name)
        res, body = self.api.GET(url)
        if only_return_body:
            return body
        return res, body

    # 查询租户的内存资源剩余
    def get_tenant_limit_memory(self, tenant_name, only_return_body=False):
        url = "/v2/tenants/{0}/limit_memory".format(tenant_name)
        res, body = self.api.GET(url)
        if only_return_body:
            return body
        return res, body

    # 设置租户的内存资源
    def set_tenant_limit_memory(self, tenant_name, body, only_return_body=False):
        url = "/v2/tenants/{0}/limit_memory".format(tenant_name)
        res, body = self.api.POST(url, body=body)
        if only_return_body:
            return body
        return res, body
