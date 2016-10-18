# -*- coding: utf8 -*-
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
import time
import datetime
import logging
import json
import math

from www.models import Tenants
from www.models.main import TenantConsumeDetail, TenantServiceInfo
from www.views.base import AuthedView

logger = logging.getLogger('default')

RULE = '''
{
"ucloud-bj-1":{
"free":{"disk":0.0831325301204819,"net":9.63855421686747,"memory_money":0.083,"disk_money":0.0069,"net_money":0.8},
"personal":{"disk":0.0831325301204819,"net":9.63855421686747,"memory_money":0.083,"disk_money":0.0069,"net_money":0.8},
"company":{"disk":0.0831325301204819,"net":2.409638554216867,"memory_money":0.332,"disk_money":0.0276,"net_money":0.8}
},
"aws-jp-1":{
"free":{"disk":0.0236994219653179,"net":5.144508670520231,"memory_money":0.173,"disk_money":0.0041,"net_money":0.89},
"personal":{"disk":0.0236994219653179,"net":5.144508670520231,"memory_money":0.173,"disk_money":0.0041,"net_money":0.89},
"company":{"disk":0.0236994219653179,"net":1.286127167630058,"memory_money":0.692,"disk_money":0.0164,"net_money":0.89}
},
"ali-sh":{
"free":{"disk":0.0594202898550725,"net":11.59420289855072,"memory_money":0.069,"disk_money":0.0041,"net_money":0.8},
"personal":{"disk":0.0594202898550725,"net":11.59420289855072,"memory_money":0.069,"disk_money":0.0041,"net_money":0.8},
"company":{"disk":0.0594202898550725,"net":2.898550724637681,"memory_money":0.276,"disk_money":0.0164,"net_money":0.8}
},
"xunda-bj":{
"free":{"disk":0.05967741935483871,"net":12.903225806451614,"memory_money":0.062,"disk_money":0.0037,"net_money":0.8},
"personal":{"disk":0.05967741935483871,"net":12.903225806451614,"memory_money":0.062,"disk_money":0.0037,"net_money":0.8},
"company":{"disk":0.05967741935483871,"net":3.2258064516129035,"memory_money":0.248,"disk_money":0.0148,"net_money":0.8}
}
}
'''


class ConsumeCostDetail(AuthedView):
    ruleJsonData = json.loads(RULE.replace('\n', ''))

    def get_media(self):
        media = super(ConsumeCostDetail, self).get_media() + self.vendor('www/css/owl.carousel.css',
                                                                         'www/css/goodrainstyle.css',
                                                                         'www/js/jquery.cookie.js',
                                                                         'www/js/common-scripts.js',
                                                                         'www/js/jquery.dcjqaccordion.2.7.js',
                                                                         'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context()
            create_time = request.GET.get("create_time")
            tenant = Tenants.objects.get(tenant_name=self.tenantName)
            consume_detail_list = TenantConsumeDetail.objects.filter(tenant_id=tenant.tenant_id, status=1, time=create_time)
            if len(consume_detail_list) == 0:
                return TemplateResponse(self.request, "www/consume_cost_detail.html", context)

            region_list = consume_detail_list.values("region").distinct()
            detail_result = {}

            for region in region_list:
                region_name = region['region']
                region_consume_detail = consume_detail_list.filter(region=region_name)

                region_total_memory = 0
                region_total_disk = 0
                region_total_net = 0
                detail_info = {}
                detail_info["region_services"] = list(region_consume_detail)

                for detail in region_consume_detail:
                    tenant_service = TenantServiceInfo.objects.get(service_id=detail.service_id)
                    detail.service_alias = tenant_service.service_cname
                    region_total_memory += detail.memory
                    region_total_disk += detail.disk
                    region_total_net += detail.net
                detail_info["region_total_memory"] = region_total_memory
                detail_info["region_total_disk"] = region_total_disk
                detail_info["region_total_net"] = region_total_net

                ruleJson = self.ruleJsonData[region_name]
                childJson = ruleJson["company"]

                region_memory_money = (region_total_memory / 1024.0) * float(childJson['memory_money'])
                region_disk_money = (region_total_disk / 1024.0) * float(childJson['disk']) * float(
                    childJson['memory_money'])
                region_net_money = (region_total_net / 1024.0) * float(childJson['net']) * float(
                    childJson['memory_money'])
                region_total_money = region_memory_money + region_disk_money + region_net_money

                detail_info["region_memory_money"] = round(region_memory_money,2)
                detail_info["region_disk_money"] = round(region_disk_money,2)
                detail_info["region_net_money"] = round(region_net_money,2)

                detail_info["region_total_money"] = round(region_total_money,2)

                detail_result[region_name] = detail_info
            context["details"] = detail_result

        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/consume_cost_detail.html", context)
