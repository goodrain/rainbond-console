# -*- coding: utf8 -*-
"""
  Created on 18/3/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.response import Response

from console.exception.main import AbortRequest
from console.services.config_service import EnterpriseConfigService
from console.utils.reqparse import bool_argument
from console.utils.reqparse import parse_item
from console.views.base import JWTAuthApiView

logger = logging.getLogger("default")


class EnterpriseObjectStorageView(JWTAuthApiView):
    @never_cache
    def put(self, request, enterprise_id):
        enable = bool_argument(parse_item(request, "enable", required=True))
        provider = parse_item(request, "provider", required=True)
        endpoint = parse_item(request, "endpoint", required=True)
        bucket_name = parse_item(request, "bucket_name", required=True)
        access_key = parse_item(request, "access_key", required=True)
        secret_key = parse_item(request, "secret_key", required=True)

        if provider not in ("alioss", "s3"):
            raise AbortRequest("provider {} not in (\"alioss\", \"s3\")".format(provider))

        ent_cfg_svc = EnterpriseConfigService(enterprise_id)
        ent_cfg_svc.update_config_enable_status(key="OBJECT_STORAGE", enable=enable)
        ent_cfg_svc.update_config_value(key="OBJECT_STORAGE", value={
            "provider": provider,
            "endpoint": endpoint,
            "bucket_name": bucket_name,
            "access_key": access_key,
            "secret_key": secret_key,
        })
        return Response(status=status.HTTP_200_OK)
