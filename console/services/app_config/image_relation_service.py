# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
from console.repositories.app_config import image_service_relation_repo


class AppImageRelationService(object):
    def create_image_service_relation(self, tenant, service_id, service_cname, image_url):
        if not image_service_relation_repo.get_image_service_relation(tenant.tenant_id, service_id):
            image_service_relation_repo.create_image_service_relation(tenant.tenant_id, service_id, image_url,
                                                                      service_cname)
