# -*- coding: utf-8 -*-
import logging
import os
import requests
from django.conf import settings

from console.exception.main import ServiceHandleException

logger = logging.getLogger("default")


def check_account_quota(user_id, region_name, operation_type):
    """
    检查用户账户配额
    Args:
        user_id: 用户ID
        region_name: 数据中心名称
        operation_type: 操作类型,如 deploy

    Returns:
        bool: 是否允许操作
    """
    if os.getenv("BILL_SERVICE_URL", "") == "":  # 如果未配置计费服务地址
        logger.info("BILL_SERVICE_URL is not configured, skip quota check")
        return True  # 不需要计量计费,直接返回True

    try:
        api_url = "{}/api/v1/verify/operation".format(os.getenv("BILL_SERVICE_URL", ''))

        payload = {
            "user_id": user_id,
            "operation_type": operation_type,
            "region_name": region_name
        }

        # 设置超时时间
        timeout = getattr(settings, "REQUESTS_TIMEOUT", 3)

        # 发送请求到计费系统
        resp = requests.post(api_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("allowed", True):
            logger.warning("Account quota check failed - user_id: %s, message: %s", 
                         user_id, data.get("message"))
            raise ServiceHandleException(msg_show=data.get("message", "账户配额不足"), msg="Account quota not enough", error_code=20002, status_code=409)
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Failed to check account quota - error: %s", e)
        # 请求失败时默认放行
        return True
