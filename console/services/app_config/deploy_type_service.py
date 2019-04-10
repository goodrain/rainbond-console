# -*- coding: utf8 -*-
"""
  Created on 19/4/10.
"""

import logging

from www.apiclient.regionapi import RegionInvokeApi
from console.exception import CallRegionAPIException

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class DeployTypeService(object):
    def get_service_deploy_type(self, service):
        return service.extend_method

    def put_service_deploy_type(self, service, deploy_type):
        label = {
            "label_key":
            "service-type",
            "label_value":
            "StatelessServiceType"
            if deploy_type == "stateless" else "StatefulServiceType",
        }
        label_dict = {
            "labels": [label],
        }
        res, body = region_api.update_service_state_label(
            self.service.service_region, self.tenant.tenant_name,
            self.service.service_alias, label_dict)
        if int(res.status) != 200:
            raise CallRegionAPIException(res.status,
                                         "update service deploy type failure")
        service.extend_method = deploy_type
        service.save()
