# -*- coding: utf8 -*-
import logging
from typing import Any

from www.apiclient.regionapi import RegionInvokeApi

DEFAULT_ARCH = "amd64"

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


def resolve_plugin_build_arch(requested_arch: Any, region: str) -> str:
    arch = str(requested_arch or "").strip()
    if arch:
        return arch

    try:
        _, body = region_api.get_cluster_nodes_arch(region)
        arches = [item for item in set((body or {}).get("list", [])) if item]
        if len(arches) == 1:
            return arches[0]
    except Exception as e:
        logger.warning("get region {0} arch for plugin build failed: {1}".format(region, e))
    return DEFAULT_ARCH
