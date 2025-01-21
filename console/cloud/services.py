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
    # 如果是公有云环境才进行检查
    if os.getenv("IS_PUBLIC") != "true" and os.getenv("IS_PUBLIC") != "True":
        return True

    try:
        # 从环境变量获取计费系统地址,默认为 localhost:8081
        bill_domain = os.getenv("BILL_SERVICE_URL", "http://14.103.232.255:32222")
        api_url = "{}/api/v1/verify/operation".format(bill_domain)

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
            raise ServiceHandleException(msg_show=data.get("message", "账户配额不足"), msg="Account quota not enough", error_code=20002)
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Failed to check account quota - error: %s", e)
        # 请求失败时默认放行
        return True
    except Exception as e:
        logger.exception("Unexpected error when checking account quota")
        # 发生未知异常时默认放行
        return True
