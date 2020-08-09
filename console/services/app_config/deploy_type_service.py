# -*- coding: utf8 -*-
"""
  Created on 19/4/10.
"""
import logging

from console.exception.main import ServiceHandleException
from console.exception.main import CallRegionAPIException
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class DeployTypeService(object):
    def get_service_deploy_type(self, service):
        return service.extend_method

    def put_service_deploy_type(self, tenant, service, deploy_type):
        label = {
            "label_key": "service-type",
            "label_value": "StatelessServiceType" if deploy_type == "stateless" else "StatefulServiceType",
        }
        label_dict = {
            "labels": [label],
        }
        try:
            res, body = region_api.update_service_state_label(service.service_region, tenant.tenant_name, service.service_alias,
                                                              label_dict)
            if int(res.status) != 200:
                raise CallRegionAPIException(res.status, "update service deploy type failure")
        except (region_api.CallApiError, ServiceHandleException) as e:
            logger.debug(e)
            raise ServiceHandleException(msg="region error", msg_show="访问数据中心失败")
        service.extend_method = deploy_type
        service.save()
