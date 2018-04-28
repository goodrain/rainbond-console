# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from backends.services.configservice import config_service
from backends.services.exceptions import *
from backends.services.resultservice import *
from backends.views.base import BaseAPIView

logger = logging.getLogger("default")


class LogoView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        查询logo
        ---
        """
        try:
            logo = config_service.get_image()
            bean = {}
            host_name = request.get_host()
            bean["logo"] = str(host_name) + str(logo)
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, bean)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def post(self, request, *args, **kwargs):
        """
        添加logo
        ---
        parameters:
            - name: logo
              description: 图片
              required: true
              type: file
              paramType: form

        """
        try:
            logo_url = config_service.upload_image(request)
            code = "0000"
            msg = "success"
            msg_show = "图片上传成功"
            bean = {}
            bean["logo"] = str(request.get_host()) + str(logo_url)
            result = generate_result(code, msg, msg_show, bean)
        except ParamsError as e:
            result = generate_result("1003", "params error", e.message)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class TitleView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取当前云帮Title
        ---

        """
        bean = {}
        try:
            title = config_service.get_config_by_key("TITLE")
            if not title:
                config = config_service.add_config("TITLE", "好雨云帮", "string", "云帮title")
                title = config.value
            bean["title"] = title
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, bean)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)

        return Response(result)

    def put(self, request, *args, **kwargs):
        """
        修改当前云帮Title
        ---
        parameters:
            - name: title
              description: 云帮标题
              required: true
              type: string
              paramType: form

        """
        try:
            title = request.data.get("title", None)
            if title:
                config_service.update_config("TITLE", title)

            code = "0000"
            msg = "success"
            msg_show = "title修改成功"
            result = generate_result(code, msg, msg_show)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class SafetyView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取当前安全策略
        ---

        """
        try:
            res = config_service.get_safety_config()
            bean = res
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, bean)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class SafetyRegistView(BaseAPIView):
    def put(self, request, *args, **kwargs):
        """
        修改注册
        ---
        parameters:
            - name: action
              description: 操作 open or close
              required: true
              type: string
              paramType: form

        """
        try:
            action = request.data.get("action", None)
            if not action:
                result = generate_result("1003", "params error", "参数错误")
            else:
                config_service.update_registerable_config(action)
                if action == "open":
                    msg_show = "修改成功,开放云帮注册"
                else:
                    msg_show = "修改成功,关闭云帮注册"
                code = "0000"
                msg = "success"
                result = generate_result(code, msg, msg_show)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class SafetyTenantView(BaseAPIView):
    def put(self, request, *args, **kwargs):
        """
        修改团队配置
        ---
        parameters:
            - name: action
              description: 操作 open , close ,set-num
              required: true
              type: string
              paramType: form
            - name: tenant_num
              description: 创建团队个数,action为set-num时必填
              required: false
              type: string
              paramType: form

        """

        action = request.data.get("action", None)
        tenant_num = request.data.get("tenant_num", None)
        try:
            config_service.update_tenant_config(action, tenant_num)
            if action == "open":
                msg_show = "修改成功,允许创建团队"
            elif action == "close":
                msg_show = "修改成功,不允许创建团队"
            else:
                msg_show = "修改成功"
            code = "0000"
            msg = "success"
            result = generate_result(code, msg, msg_show)
        except TenantOverFlowError as e:
            result = generate_result("1003", "params error", "{}".format(e.message))
        except ParamsError as e:
            result = generate_result("1003", "params error", "{}".format(e.message))
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class AuthorizationAView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取当前license信息
        ---

        """
        try:
            res = config_service.get_license_info()
            bean = res
            code = "0000"
            msg = "success"
            msg_show = "查询成功"
            result = generate_result(code, msg, msg_show, bean)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def put(self, request, *args, **kwargs):
        """
        导入license
        ---
        parameters:
            - name: license
              description: 云帮license
              required: true
              type: string
              paramType: form

        """
        try:
            license = request.data.get("license", None)
            if license:
                config_service.update_license_info(license)
            code = "0000"
            msg = "success"
            msg_show = "license修改成功"
            result = generate_result(code, msg, msg_show)
        except ParamsError as e:
            result = generate_result("1003", "params error", e.message)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class ConfigGithubView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取当前github配置信息
        ---

        """
        try:
            config = config_service.get_github_config()
            code = "0000"
            msg = "success"
            msg_show = "查询成功"

            result = generate_result(code, msg, msg_show, config)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def post(self, request, *args, **kwargs):
        """
        添加GitHub配置
        ---
        parameters:
            - name: redirect_uri
              description: 重定向地址
              required: true
              type: string
              paramType: form
            - name: client_secret
              description: 客户端密钥
              required: true
              type: string
              paramType: form
            - name: client_id
              description: 客户端id
              required: true
              type: string
              paramType: form

        """
        try:
            redirect_uri = request.data.get("redirect_uri", None)
            client_secret = request.data.get("client_secret", None)
            client_id = request.data.get("client_id", None)
            config_service.add_github_config(redirect_uri, client_secret, client_id)
            code = "0000"
            msg = "success"
            msg_show = "github配置添加成功"
            result = generate_result(code, msg, msg_show)
        except ConfigExistError as e:
            result = generate_result("1101", "config exist", "{}".format(e.message))
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def put(self, request, *args, **kwargs):
        """
        修改GitHub配置
        ---
        parameters:
            - name: redirect_uri
              description: 重定向地址
              required: true
              type: string
              paramType: form
            - name: client_secret
              description: 客户端密钥
              required: true
              type: string
              paramType: form
            - name: client_id
              description: 客户端id
              required: true
              type: string
              paramType: form

        """
        try:
            redirect_uri = request.data.get("redirect_uri", None)
            client_secret = request.data.get("client_secret", None)
            client_id = request.data.get("client_id", None)
            config_service.update_github_config(redirect_uri, client_secret, client_id)
            code = "0000"
            msg = "success"
            msg_show = "github配置修改成功"
            result = generate_result(code, msg, msg_show)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class ConfigGitlabView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取当前gitlab配置信息
        ---

        """
        try:
            config = config_service.get_gitlab_config()
            code = "0000"
            msg = "success"
            msg_show = "查询成功"

            result = generate_result(code, msg, msg_show, config)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def post(self, request, *args, **kwargs):
        """
        添加GitLab配置
        ---
        parameters:
            - name: url
              description: gitlab地址
              required: true
              type: string
              paramType: form
            - name: admin_user
              description: 管理员账户
              required: true
              type: string
              paramType: form
            - name: admin_password
              description: 管理员密码
              required: true
              type: string
              paramType: form
            - name: hook_url
              description: hook地址
              required: true
              type: string
              paramType: form
            - name: admin_email
              description: 管理员邮箱
              required: true
              type: string
              paramType: form

        """
        try:
            url = request.data.get("url", None)
            admin_user = request.data.get("admin_user", None)
            admin_password = request.data.get("admin_password", None)
            hook_url = request.data.get("hook_url", None)
            admin_email = request.data.get("admin_email", None)
            config_service.add_gitlab_config(url, admin_user, admin_password, admin_email, hook_url)
            code = "0000"
            msg = "success"
            msg_show = "gitlab配置添加成功"
            result = generate_result(code, msg, msg_show)
        except ConfigExistError as e:
            result = generate_result("1101", "config exist", "{}".format(e.message))
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def put(self, request, *args, **kwargs):
        """
        修改GitLab配置
        ---
        parameters:
            - name: url
              description: gitlab地址
              required: true
              type: string
              paramType: form
            - name: admin_user
              description: 管理员账户
              required: true
              type: string
              paramType: form
            - name: admin_password
              description: 管理员密码
              required: true
              type: string
              paramType: form
            - name: hook_url
              description: hook地址
              required: true
              type: string
              paramType: form
            - name: admin_email
              description: 管理员邮箱
              required: true
              type: string
              paramType: form

        """
        try:
            url = request.data.get("url", None)
            admin_user = request.data.get("admin_user", None)
            admin_password = request.data.get("admin_password", None)
            hook_url = request.data.get("hook_url", None)
            admin_email = request.data.get("admin_email", None)
            config_service.update_gitlab_config(url, admin_user, admin_password, admin_email, hook_url)
            code = "0000"
            msg = "success"
            msg_show = "gitlab配置修改成功"
            result = generate_result(code, msg, msg_show)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class ConfigCodeView(BaseAPIView):
    def post(self, request, *args, **kwargs):
        """
        git仓库对接
        ---
        parameters:
            - name: action
              description: 打开或关闭 open 或 close
              required: true
              type: string
              paramType: form
            - name: type
              description: 类型 github 或 gitlab
              required: true
              type: string
              paramType: form

        """
        try:

            action = request.data.get("action", "open")
            type = request.data.get("type", "github")
            config_service.manage_code_conf(action, type)
            code = "0000"
            msg = "success"
            if action == "open":
                msg_show = "{}开启对接".format(type)
            else:
                msg_show = "{}关闭对接".format(type)
            result = generate_result(code, msg, msg_show)
        except ParamsError as e:
            result = generate_result("1003", "params error", e.message)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class ConfigManageView(BaseAPIView):
    def post(self, request, *args, **kwargs):
        """
        环境对接起停
        ---
        parameters:
            - name: action
              description: 打开或关闭 open 或 close
              required: true
              type: string
              paramType: form
            - name: type
              description: github,gitlab,hubconf,ftpconf
              required: true
              type: string
              paramType: form

        """
        try:

            action = request.data.get("action", "open")
            type = request.data.get("type", "github")
            config_service.manage_code_conf(action, type)
            code = "0000"
            msg = "success"
            if action == "open":
                msg_show = "配置开启对接"
            else:
                msg_show = "配置关闭对接"
            result = generate_result(code, msg, msg_show)
        except ParamsError as e:
            result = generate_result("1003", "params error", e.message)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class HubConfigView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取当前配置信息配置信息
        ---

        """
        try:
            config = config_service.get_image_hub_config()
            code = "0000"
            msg = "success"
            msg_show = "查询成功"

            result = generate_result(code, msg, msg_show, config)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def post(self, request, *args, **kwargs):
        """
        添加hub配置
        ---
        parameters:
            - name: hub_url
              description: hub地址
              required: true
              type: string
              paramType: form
            - name: namespace
              description: 命名空间
              required: true
              type: string
              paramType: form
            - name: hub_user
              description: hub用户
              required: true
              type: string
              paramType: form
            - name: hub_password
              description: hub用户密码
              required: true
              type: string
              paramType: form

        """
        try:
            hub_url = request.data.get("hub_url", None)
            namespace = request.data.get("namespace", None)
            hub_user = request.data.get("hub_user", None)
            hub_password = request.data.get("hub_password", None)
            if not hub_url or not namespace or not hub_user or not hub_password:
                return Response(generate_result("0400", "params error", "请填写必要参数"))
            config_service.add_image_hub_config(hub_url, namespace, hub_user, hub_password)
            code = "0000"
            msg = "success"
            msg_show = "hub配置添加成功"
            result = generate_result(code, msg, msg_show)
        except ConfigExistError as e:
            result = generate_result("1101", "config exist", "{}".format(e.message))
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def put(self, request, *args, **kwargs):
        """
        修改hub配置
        ---
        parameters:
            - name: hub_url
              description: hub地址
              required: true
              type: string
              paramType: form
            - name: namespace
              description: 命名空间
              required: true
              type: string
              paramType: form
            - name: hub_user
              description: hub用户
              required: true
              type: string
              paramType: form
            - name: hub_password
              description: hub用户密码
              required: true
              type: string
              paramType: form

        """
        try:
            hub_url = request.data.get("hub_url", None)
            namespace = request.data.get("namespace", None)
            hub_user = request.data.get("hub_user", None)
            hub_password = request.data.get("hub_password", None)
            config_service.update_image_hub_config(hub_url, namespace, hub_user, hub_password)
            code = "0000"
            msg = "success"
            msg_show = "hub配置修改成功"
            result = generate_result(code, msg, msg_show)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)


class FtpConfigView(BaseAPIView):
    def get(self, request, *args, **kwargs):
        """
        获取当前ftp配置信息
        ---

        """
        try:
            config = config_service.get_ftp_config()
            code = "0000"
            msg = "success"
            msg_show = "查询成功"

            result = generate_result(code, msg, msg_show, config)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def post(self, request, *args, **kwargs):
        """
        添加ftp配置
        ---
        parameters:
            - name: ftp_host
              description: ftp地址
              required: true
              type: string
              paramType: form
            - name: ftp_port
              description: ftp端口
              required: true
              type: string
              paramType: form
            - name: namespace
              description: 命名空间
              required: true
              type: string
              paramType: form
            - name: ftp_username
              description: ftp用户名
              required: true
              type: string
              paramType: form
            - name: ftp_password
              description: ftp用户密码
              required: true
              type: string
              paramType: form

        """
        try:
            ftp_host = request.data.get("ftp_host", None)
            ftp_port = request.data.get("ftp_port", None)
            namespace = request.data.get("namespace", None)
            ftp_username = request.data.get("ftp_username", None)
            ftp_password = request.data.get("ftp_password", None)
            config_service.add_ftp_config(ftp_host, ftp_port, namespace, ftp_username, ftp_password)
            code = "0000"
            msg = "success"
            msg_show = "ftp配置添加成功"
            result = generate_result(code, msg, msg_show)
        except ConfigExistError as e:
            result = generate_result("1101", "config exist", "{}".format(e.message))
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)

    def put(self, request, *args, **kwargs):
        """
        修改ftp配置
        ---
        parameters:
            - name: ftp_host
              description: ftp地址
              required: true
              type: string
              paramType: form
            - name: ftp_port
              description: ftp端口
              required: true
              type: string
              paramType: form
            - name: namespace
              description: 命名空间
              required: true
              type: string
              paramType: form
            - name: ftp_username
              description: ftp用户名
              required: true
              type: string
              paramType: form
            - name: ftp_password
              description: ftp用户密码
              required: true
              type: string
              paramType: form

        """
        try:
            ftp_host = request.data.get("ftp_host", None)
            ftp_port = request.data.get("ftp_port", None)
            namespace = request.data.get("namespace", None)
            ftp_username = request.data.get("ftp_username", None)
            ftp_password = request.data.get("ftp_password", None)
            config_service.update_ftp_config(ftp_host, ftp_port, namespace,ftp_username, ftp_password)
            code = "0000"
            msg = "success"
            msg_show = "ftp配置修改成功"
            result = generate_result(code, msg, msg_show)
        except Exception as e:
            result = generate_error_result()
            logger.exception(e)
        return Response(result)