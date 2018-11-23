# -*- coding: utf-8 -*-

from console.views.team import UserAllTeamView
from www.models import Tenants,TenantRegionInfo,ServiceDomainCertificate
from console.utils.test_ssl import analyze_cert


def get_cert_info_by(self, tenant_name):
    result = {}
    tentant_info = Tenants.objects.get(tenant_name=tenant_name)
    tentant_id = tentant_info.tenant_id
    team_id = TenantRegionInfo.objects.get(tentant_id=tentant_id)
    try:
        certifactes = ServiceDomainCertificate.objects.filter(tenant_id=team_id)
        data = []
        for sdc in certifactes:
            certifacte = {}
            certifacte["certificate"] = sdc.certificate
            cert_data = analyze_cert(sdc.certificate)
            data.append(cert_data)
        result["data"] = data

    except Exception as e:
        logger.exception(e)
    return JsonResponse(result, status=200)