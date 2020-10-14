# -*- coding: utf-8 -*-
# creater by: barnett
import datetime
import logging
import time

from OpenSSL import crypto

from console.utils.exception import err_cert_expired
from console.utils.exception import err_invalid_cert, err_cert_mismatch, err_invalid_private_key
from console.utils.exception import ServiceHandleException

logger = logging.getLogger("default")


def analyze_cert(content):
    data = {}
    # path表示证书路径，file_name表示证书文件名

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, content)
    subject = cert.get_subject()
    has_expired = cert.has_expired()  # 是否过期

    # 得到证书的域名
    extension_count = cert.get_extension_count()
    index = 0
    sans = []
    while index < extension_count:
        extension = cert.get_extension(index)
        index = index + 1
        if extension.get_short_name() == "subjectAltName":
            subject_alt_names = parse_subject_alt_names(extension._subjectAltNameString())
            sans = subject_alt_names
    if subject.CN not in sans:
        sans.append(subject.CN)
    end_data = cert.get_notAfter()  # 过期时间
    issuer = cert.get_issuer()  # 颁发者

    # 得到证书颁发机构
    issued_by = issuer.CN  # 颁发机构
    data["issued_to"] = sans
    # data["issuer"] = issuer
    data["has_expired"] = has_expired

    if issued_by == "rainbond":
        cert_source = "Let's Encrypt签发"
    else:
        cert_source = "第三方签发"
    data["issued_by"] = cert_source
    data["end_data"] = utc2local(end_data)

    return data


def parse_subject_alt_names(content):
    subject_alt_names = []
    if ',' in content:
        kvs = content.split(',')
        for kv in kvs:
            if ':' in kv:
                k, v = kv.split(':')
                k = k.strip().replace('\'', '')
                if k == 'DNS' or k == 'IP Address':
                    if len(v.strip()) > 0 and v.strip() != '127.0.0.1':
                        subject_alt_names.append(v.strip())
    return subject_alt_names


def cert_is_effective(content):
    """分析证书是否有效"""
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, content)
        has_expired = cert.has_expired()  # 是否过期
        if has_expired:
            raise err_cert_expired
    except ServiceHandleException:
        raise err_cert_expired
    except Exception as e:
        logger.warning("loading certificate: {}".format(e))
        raise err_invalid_cert
    return True


def private_key_is_effective(content, private_key):
    """Determine whether the private key format is correct and whether the key pairs match"""
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, content)
    try:
        pri_key = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key)
    except Exception:
        raise err_invalid_private_key

    sign = crypto.sign(pri_key, "data", b"sha256")
    try:
        crypto.verify(cert, sign, "data", b"sha256")
    except Exception:
        raise err_cert_mismatch
    return True


def utc2local(utc_st):
    '''UTC时间转本地时间（+8:00）'''
    utc_format = "%Y%m%d%H%M%SZ"
    utc_st = datetime.datetime.strptime(utc_st, utc_format)
    now_stamp = time.time()
    local_time = datetime.datetime.fromtimestamp(now_stamp)
    utc_time = datetime.datetime.utcfromtimestamp(now_stamp)
    offset = local_time - utc_time
    local_st = utc_st + offset
    return str(local_st)
