# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger("default")


def check_memory_quota(oauth_instance, eid, memory, node=1):
    logger.debug("required memory: {}, node: {}".format(memory, node))
    memory_required = int(memory) * int(node)
    if memory_required <= 0:
        return True
    body = {"memory_required": memory_required}
    if not oauth_instance:
        return True
    rst = oauth_instance.check_ent_memory(eid, body)
    return not rst.insufficient
