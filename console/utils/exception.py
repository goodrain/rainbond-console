# -*- coding: utf-8 -*-
from console.exception.main import ServiceHandleException

err_cert_expired = ServiceHandleException("the certificate has been expired", u"证书已过期")

err_invalid_cert = ServiceHandleException("the certificate is invalid", u"无效证书")

err_cert_mismatch = ServiceHandleException("the certificate key pair mismatch", u"证书密钥对不匹配")

err_invalid_private_key = ServiceHandleException("the private key is invalid", u"无效私钥")