# -*- coding: utf-8 -*-
from console.services.app_config import domain_service
from console.utils.certutil import analyze_cert

class Cert_Service(object):
    def get_cert_info(self,tenant):
        data=[]
        certificates = domain_service.get_certificate(tenant)
        for cert in certificates:
            cert_info = analyze_cert(cert)
            data.append(cert_info)
        return data



cert_service = Cert_Service()


