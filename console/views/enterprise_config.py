# -*- coding: utf8 -*-
"""
  Created on 18/3/15.
"""
import logging

from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.response import Response

from console.enum.system_config import ConfigKeyEnum
from console.exception.main import AbortRequest, ServiceHandleException
from console.services.config_service import EnterpriseConfigService, ConfigService
from console.services.enterprise_services import enterprise_services
from console.services.operation_log import operation_log_service, OperationModule, Operation
from www.utils.return_message import general_message
from console.utils.reqparse import bool_argument
from console.utils.reqparse import parse_item
from console.views.base import EnterpriseAdminView, JWTAuthApiView

logger = logging.getLogger("default")


class EnterpriseConfigView(EnterpriseAdminView):
    @never_cache
    def put(self, request, enterprise_id, *args, **kwargs):
        title = parse_item(request, "title")
        logo = parse_item(request, "logo")
        favicon = parse_item(request, "favicon")
        enterprise_alias = parse_item(request, "enterprise_alias")
        doc_url = parse_item(request, "doc_url")
        enable_official_demo = parse_item(request, "enable_official_demo", default=True)
        login_image = parse_item(request, "login_image")
        header_color = request.data.get("header_color", "")
        header_writing_color = request.data.get("header_writing_color", "")
        sidebar_color = request.data.get("sidebar_color", "")
        sidebar_writing_color = request.data.get("sidebar_writing_color", "")
        footer = request.data.get("footer", "")
        shadow = parse_item(request, "shadow", default=True)
        # 是否显示k8s集群相关
        show_k8s = parse_item(request, "show_k8s")
        # 是否显示切换语言
        show_langue = parse_item(request, "show_langue")
        security_restrictions = parse_item(request, "security_restrictions", default=False)

        config_service = ConfigService()
        ent_config_service = EnterpriseConfigService(enterprise_id, self.user.user_id)

        if title:
            config_service.update_config_value(ConfigKeyEnum.TITLE.name, title)
            ent_config_service.update_config_value(ConfigKeyEnum.TITLE.name, title)
        if logo:
            config_service.update_config_value(ConfigKeyEnum.LOGO.name, logo)
            ent_config_service.update_config_value(ConfigKeyEnum.LOGO.name, logo)
        if enterprise_alias:
            enterprise_services.update_alias(enterprise_id, enterprise_alias)
        if favicon:
            config_service.update_config_value(ConfigKeyEnum.FAVICON.name, favicon)
            ent_config_service.update_config_value(ConfigKeyEnum.FAVICON.name, favicon)
        if login_image:
            config_service.update_config_value(ConfigKeyEnum.LOGIN_IMAGE.name, login_image)
            ent_config_service.update_config_value(ConfigKeyEnum.LOGIN_IMAGE.name, login_image)
        if type(show_k8s) == bool:
            ent_config_service.update_config_enable_status(ConfigKeyEnum.SHOW_K8S.name, show_k8s)
        if type(show_langue) == bool:
            ent_config_service.update_config_enable_status(ConfigKeyEnum.SHOW_LANGUE.name, show_langue)
        if security_restrictions is not None:
            ent_config_service.update_config_enable_status(ConfigKeyEnum.SECURITY_RESTRICTIONS.name, security_restrictions)

        config_service.update_config_value(ConfigKeyEnum.HEADER_COLOR.name, header_color)
        ent_config_service.update_config_value(ConfigKeyEnum.HEADER_COLOR.name, header_color)

        config_service.update_config_value(ConfigKeyEnum.HEADER_WRITING_COLOR.name, header_writing_color)
        ent_config_service.update_config_value(ConfigKeyEnum.HEADER_WRITING_COLOR.name, header_writing_color)

        config_service.update_config_value(ConfigKeyEnum.SIDEBAR_COLOR.name, sidebar_color)
        ent_config_service.update_config_value(ConfigKeyEnum.SIDEBAR_COLOR.name, sidebar_color)

        config_service.update_config_value(ConfigKeyEnum.SIDEBAR_WRITING_COLOR.name, sidebar_writing_color)
        ent_config_service.update_config_value(ConfigKeyEnum.SIDEBAR_WRITING_COLOR.name, sidebar_writing_color)

        config_service.update_config_value(ConfigKeyEnum.FOOTER.name, footer)
        ent_config_service.update_config_value(ConfigKeyEnum.FOOTER.name, footer)

        config_service.update_config_value(ConfigKeyEnum.SHADOW.name, shadow)
        ent_config_service.update_config_enable_status(ConfigKeyEnum.SHADOW.name, shadow)

        doc_url_value = dict()
        doc_url_value["platform_url"] = ""
        if doc_url:
            if not doc_url.startswith(('http://', 'https://')):
                doc_url = "http://{}".format(doc_url)
            if not doc_url.endswith('/'):
                doc_url = doc_url + '/'
            doc_url_value["platform_url"] = doc_url
        ent_config_service.update_config_value(ConfigKeyEnum.DOCUMENT.name, doc_url_value)
        ent_config_service.update_config_enable_status(ConfigKeyEnum.OFFICIAL_DEMO.name, enable_official_demo)
        config_service.update_config_value(ConfigKeyEnum.DOCUMENT.name, doc_url_value)
        config_service.update_config_enable_status(ConfigKeyEnum.OFFICIAL_DEMO.name, enable_official_demo)

        # 处理自定义字段
        custom_fields = request.data.get("custom_fields")
        if custom_fields:
            # 验证是否为列表
            if not isinstance(custom_fields, list):
                raise ServiceHandleException(
                    msg="custom_fields must be a list",
                    msg_show="custom_fields 必须是数组格式",
                    status_code=400
                )

            # 验证每个字段
            valid_types = ('int', 'string', 'bool')
            validated_fields = {}

            for idx, field_data in enumerate(custom_fields):
                if not isinstance(field_data, dict):
                    raise ServiceHandleException(
                        msg=f"custom_fields[{idx}] must be a dict",
                        msg_show=f"自定义字段第 {idx + 1} 项必须是对象",
                        status_code=400
                    )

                # 检查必填字段
                key = field_data.get('key')
                value = field_data.get('value')
                field_type = field_data.get('type')

                if not key:
                    raise ServiceHandleException(
                        msg=f"custom_fields[{idx}].key is required",
                        msg_show=f"自定义字段第 {idx + 1} 项缺少 key",
                        status_code=400
                    )

                if value is None:
                    raise ServiceHandleException(
                        msg=f"custom_fields[{idx}].value is required",
                        msg_show=f"自定义字段第 {idx + 1} 项缺少 value",
                        status_code=400
                    )

                if not field_type:
                    raise ServiceHandleException(
                        msg=f"custom_fields[{idx}].type is required",
                        msg_show=f"自定义字段第 {idx + 1} 项缺少 type",
                        status_code=400
                    )

                # 检查 type 是否合法
                if field_type not in valid_types:
                    raise ServiceHandleException(
                        msg=f"custom_fields[{idx}].type must be one of {valid_types}",
                        msg_show=f"自定义字段第 {idx + 1} 项的 type 必须是 int、string 或 bool",
                        status_code=400
                    )

                # 验证值的类型
                if field_type == 'int' and value != '':
                    try:
                        int(value)
                    except (ValueError, TypeError):
                        raise ServiceHandleException(
                            msg=f"custom_fields[{idx}].value must be a valid integer",
                            msg_show=f"自定义字段 {key} 的值必须是有效的整数",
                            status_code=400
                        )

                elif field_type == 'bool' and value != '':
                    if str(value).lower() not in ('true', 'false', '0', '1'):
                        raise ServiceHandleException(
                            msg=f"custom_fields[{idx}].value must be a valid boolean",
                            msg_show=f"自定义字段 {key} 的值必须是有效的布尔值 (true/false/0/1)",
                            status_code=400
                        )

                # 保存为字典，key 为字段名，value 包含值和类型
                validated_fields[key] = {
                    'value': str(value),
                    'type': field_type
                }

            # 保存每个自定义字段为单独的配置项（仅企业级）
            ent_config_service.save_custom_fields(validated_fields)

        return Response(status=status.HTTP_200_OK)


class EnterpriseObjectStorageView(EnterpriseAdminView):
    @never_cache
    def put(self, request, enterprise_id, *args, **kwargs):
        enable = bool_argument(parse_item(request, "enable", required=True))
        provider = parse_item(request, "provider", required=True)
        endpoint = parse_item(request, "endpoint", required=True)
        bucket_name = parse_item(request, "bucket_name", required=True)
        access_key = parse_item(request, "access_key", required=True)
        secret_key = parse_item(request, "secret_key", required=True)

        if provider not in ("alioss", "s3"):
            raise AbortRequest("provider {} not in (\"alioss\", \"s3\")".format(provider))

        ent_cfg_svc = EnterpriseConfigService(enterprise_id, self.user.user_id)
        ent_cfg_svc.update_config_enable_status(key="OBJECT_STORAGE", enable=enable)
        ent_cfg_svc.update_config_value(
            key="OBJECT_STORAGE",
            value={
                "provider": provider,
                "endpoint": endpoint,
                "bucket_name": bucket_name,
                "access_key": access_key,
                "secret_key": secret_key,
            })
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.Set, module=OperationModule.OBJECT_STORAGE, module_name="")
        operation_log_service.create_enterprise_log(user=self.user, comment=comment, enterprise_id=enterprise_id)
        return Response(status=status.HTTP_200_OK)


class EnterpriseAppStoreImageHubView(EnterpriseAdminView):
    @never_cache
    def put(self, request, enterprise_id, *args, **kwargs):
        enable = bool_argument(parse_item(request, "enable", required=True))
        hub_url = parse_item(request, "hub_url", required=True)
        namespace = parse_item(request, "namespace")
        hub_user = parse_item(request, "hub_user")
        hub_password = parse_item(request, "hub_password")

        ent_cfg_svc = EnterpriseConfigService(enterprise_id, self.user.user_id)
        ent_cfg_svc.update_config_enable_status(key="APPSTORE_IMAGE_HUB", enable=enable)
        ent_cfg_svc.update_config_value(
            key="APPSTORE_IMAGE_HUB",
            value={
                "hub_url": hub_url,
                "namespace": namespace,
                "hub_user": hub_user,
                "hub_password": hub_password,
            })
        comment = operation_log_service.generate_generic_comment(
            operation=Operation.Set, module=OperationModule.APP_STORE_IMAGE_HUB, module_name="")
        operation_log_service.create_enterprise_log(user=self.user, comment=comment, enterprise_id=enterprise_id)
        return Response(status=status.HTTP_200_OK)


class EnterpriseVisualMonitorView(EnterpriseAdminView):
    @never_cache
    def put(self, request, enterprise_id, *args, **kwargs):
        enable = bool_argument(parse_item(request, "enable", required=True))
        home_url = parse_item(request, "home_url", required=True)
        cluster_monitor_suffix = request.data.get("cluster_monitor_suffix", "/d/cluster/ji-qun-jian-kong-ke-shi-hua")
        node_monitor_suffix = request.data.get("node_monitor_suffix", "/d/node/jie-dian-jian-kong-ke-shi-hua")
        component_monitor_suffix = request.data.get("component_monitor_suffix", "/d/component/zu-jian-jian-kong-ke-shi-hua")
        slo_monitor_suffix = request.data.get("slo_monitor_suffix", "/d/service/fu-wu-jian-kong-ke-shi-hua")

        ent_cfg_svc = EnterpriseConfigService(enterprise_id, self.user.user_id)
        ent_cfg_svc.update_config_enable_status(key="VISUAL_MONITOR", enable=enable)
        ent_cfg_svc.update_config_value(
            key="VISUAL_MONITOR",
            value={
                "home_url": home_url.strip('/'),
                "cluster_monitor_suffix": cluster_monitor_suffix,
                "node_monitor_suffix": node_monitor_suffix,
                "component_monitor_suffix": component_monitor_suffix,
                "slo_monitor_suffix": slo_monitor_suffix,
            })
        return Response(status=status.HTTP_200_OK)


class EnterpriseAlertsView(JWTAuthApiView):
    @never_cache
    def get(self, request, enterprise_id, *args, **kwargs):
        alerts = enterprise_services.get_enterprise_alerts(enterprise_id)
        return Response(general_message(200, "success", "查询成功", list=alerts), status=status.HTTP_200_OK)
