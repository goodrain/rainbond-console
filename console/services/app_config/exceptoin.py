# -*- coding: utf-8 -*-
from console.exception.main import ServiceHandleException

err_cert_name_exists = ServiceHandleException("certificate name already exists", "证书别名已存在", 412, 412)

err_cert_not_found = ServiceHandleException("certificate not found", "证书不存在", 404, 404)

err_still_has_http_rules = ServiceHandleException("the certificate still has http rules", "仍有网关策略在使用该证书", 400, 400)
