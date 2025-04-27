# -*- coding: utf8 -*-
import logging
from rest_framework import status
from rest_framework.response import Response
from console.views.base import EnterpriseAdminView
from console.services.config_service import EnterpriseConfigService
from www.utils.return_message import general_message

logger = logging.getLogger("default")

class SMSConfigView(EnterpriseAdminView):
    def get(self, request, enterprise_id, *args, **kwargs):
        """
        获取短信配置
        ---
        parameters:
            - name: enterprise_id
              description: 企业ID
              required: true
              type: string
              paramType: path
        """
        try:
            config_service = EnterpriseConfigService(enterprise_id, self.user.user_id)
            sms_config = config_service.get_config_by_key("SMS_CONFIG")
            
            if not sms_config:
                # 如果配置不存在，初始化一个默认配置
                config_service.add_config(
                    key="SMS_CONFIG",
                    default_value={"access_key": "", "access_secret": "", "sign_name": "", "template_code": "", "provider": "aliyun", "sms_account": ""},
                    type="json",
                    desc="短信认证配置",
                    enable=True
                )
                sms_config = config_service.get_config_by_key("SMS_CONFIG")

            result = general_message(
                200,
                "success",
                "获取成功",
                bean={
                    "sms_config": {
                        "enable": sms_config.enable,
                        "value": eval(sms_config.value) if sms_config.type == "json" else sms_config.value
                    }
                }
            )
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(e)
            result = general_message(500, "获取短信配置失败", "{}".format(e))
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, enterprise_id, *args, **kwargs):
        """
        更新短信配置
        ---
        parameters:
            - name: enterprise_id
              description: 企业ID
              required: true
              type: string
              paramType: path
            - name: sms_config
              description: 短信配置
              required: true
              type: object
              paramType: body
        """
        try:
            sms_config = request.data.get("sms_config", None)
            if not sms_config:
                result = general_message(400, "参数错误", "缺少sms_config参数")
                return Response(result, status=status.HTTP_400_BAD_REQUEST)

            # 验证必要的配置字段, sms_account 只在火山云短信服务商下使用，暂不做校验
            required_fields = ["access_key", "access_secret", "sign_name", "template_code", "provider"]
            for field in required_fields:
                if field not in sms_config.get("value", {}):
                    result = general_message(400, "参数错误", "缺少必要的配置字段: {}".format(field))
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)

            config_service = EnterpriseConfigService(enterprise_id, self.user.user_id)
            # 更新配置
            config = config_service.update_config_by_key("SMS_CONFIG", sms_config)

            result = general_message(200, "success", "更新成功", bean=config)
            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(e)
            result = general_message(500, "更新短信配置失败", "{}".format(e))
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 