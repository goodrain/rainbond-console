# -*- coding: utf-8 -*-
import logging
from console.utils.oauth.oauth_types import get_oauth_instance
from console.models.main import OAuthServices
from console.models.main import UserOAuthServices
from console.models.main import EnterpriseUserPerm

logger = logging.getLogger("default")


def order_payload(order):
    return {
        "eid": order.eid,
        "create_time": order.create_time,
        "expired_time": order.expired_time,
        "final_price": order.final_price,
        "memory": order.memory,
        "months": order.months,
        "order_id": order.order_id,
        "origin_price": order.origin_price,
        "status": order.status,
        "unit_price": order.unit_price,
        "user_id": order.user_id,
    }


def check_memory_quota(oauth_instance, eid,  memory):
    body = {
        "memory_required": memory
    }
    if oauth_instance is None:
        try:
            user_perm = EnterpriseUserPerm.objects.filter(enterprise_id=eid, identity="admin").order_by("ID").first()
            oauth_service = OAuthServices.objects.get(oauth_type="enterprisecenter", ID=1)
            oauth_user = UserOAuthServices.objects.get(service_id=oauth_service.ID, user_id=user_perm.user_id)
            oauth_instance = get_oauth_instance("enterprisecenter", oauth_service, oauth_user)
        except Exception as e:
            logger.debug(e)
            return False
    rst = oauth_instance.check_ent_memory(eid, body)
    return rst.insufficient
