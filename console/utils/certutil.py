#_*_ encoding:utf8 _*_
from OpenSSL import crypto

def analyze_cert(content):
    data = {}
    # path表示证书路径，file_name表示证书文件名

    cert = crypto.load_certificate(crypto.FILETYPE_PEM, content)
    subject = cert.get_subject()
    has_expired = cert.has_expired()#是否过期


    # 得到证书的域名
    issued_to = subject.CN

    end_data = cert.get_notAfter()#过期时间
    issuer = cert.get_issuer()#颁发者analyze_cert
    commonname = issuer.commonName#域名
    # 得到证书颁发机构
    issued_by = issuer.CN     #颁发机构
    data["issued_to"] = issued_to
    data["issuer"] = issuer
    data["has_expired"] = has_expired

    if issued_by == "rainbond":
        cert_source = "Let's Encrypt签发"
    else:
        cert_source = "第三方签发"
    data["issued_by"] = cert_source
    data["end_data"] = end_data


    return data




