# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger("default")


def check_memory_quota(oauth_instance, eid, memory, node):
    body = {
        "memory_required": int(memory)*int(node)
    }
    if not oauth_instance:
        return False
    rst = oauth_instance.check_ent_memory(eid, body)
    return not rst.insufficient
