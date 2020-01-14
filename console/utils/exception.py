# -*- coding: utf-8 -*-
from console.exception.main import ServiceHandleException

err_cert_expired = ServiceHandleException("the certificate has been expired", "证书已过期")

err_invalid_cert = ServiceHandleException("the certificate is invalid", "无效证书")
