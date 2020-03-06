# -*- coding: utf-8 -*-
from console.exception.main import ServiceHandleException

err_cert_expired = ServiceHandleException("the certificate has been expired", u"证书已过期")

err_invalid_cert = ServiceHandleException("the certificate is invalid", u"无效证书")
