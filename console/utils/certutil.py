#_*_ encoding:utf8 _*_
from OpenSSL import crypto
import time,datetime
import os

def analyze_cert(content):
    data = {}
    # path表示证书路径，file_name表示证书文件名

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, content)
    subject = cert.get_subject()
    has_expired = cert.has_expired()#是否过期


    # 得到证书的域名
    issued_to = subject.CN

    end_data = cert.get_notAfter()#过期时间
    issuer = cert.get_issuer()#颁发者

    # 得到证书颁发机构
    issued_by = issuer.CN     #颁发机构
    data["issued_to"] = issued_to
    # data["issuer"] = issuer
    data["has_expired"] = has_expired

    if issued_by == "rainbond":
        cert_source = "Let's Encrypt签发"
    else:
        cert_source = "第三方签发"
    data["issued_by"] = cert_source
    data["end_data"] = utc2local(end_data)


    return data

def cert_is_effective(content):
    """分析证书是否有效"""
    try:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, content)
        has_expired = cert.has_expired()  # 是否过期
        if not has_expired:
            return True
    except Exception as e:
        return False


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
    print local_st
    return str(local_st)

