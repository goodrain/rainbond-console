# -*- coding: utf-8 -*-
from console.exception.main import ServiceHandleException

err_region_not_found = ServiceHandleException("region not found", "数据中心不存在", 404, 404)
