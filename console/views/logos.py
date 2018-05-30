# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from backends.services.configservice import config_service
from backends.services.exceptions import *
from backends.services.resultservice import *
from console.repositories.announce_repo import announcement_repo
from console.views.base import BaseApiView, AlowAnyApiView
from www.utils.return_message import general_message, error_message
from django.conf import settings

logger = logging.getLogger("default")


class ConfigInfoView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        """
        登录页面获取云帮Logo、标题、github、gitlab配置信息(不要Authorization头)
        ---
        """
        try:
            code = 200
            data = dict()
            logo = config_service.get_image()
            host_name = request.get_host()
            data["logo"] = str(host_name) + str(logo)
            # 判断是否为公有云
            if settings.MODULES.get('SSO_LOGIN'):
                data["url"] = "https://sso.goodrain.com/#/login/"
                data["is_public"] = True
            else:
                data["url"] = "{0}://{1}/index#/user/login".format(request.scheme, request.get_host())
                data["is_public"] = False

            title = config_service.get_config_by_key("TITLE")
            if not title:
                config = config_service.add_config("TITLE", "好雨云帮", "string", "云帮title")
                title = config.value
            data["title"] = title

            github_config = config_service.get_github_config()
            data["github_config"] = github_config

            gitlab_config = config_service.get_gitlab_config()
            data["gitlab_config"] = gitlab_config

            result = general_message(code, "query success", "Logo获取成功", bean=data)
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)


class LogoView(BaseApiView):
    def get(self, request, *args, **kwargs):
        """
        获取云帮Logo
        ---
        """
        try:
            code = 200
            data = dict()
            logo = config_service.get_image()
            host_name = request.get_host()
            data["logo"] = str(host_name) + str(logo)
            result = general_message(code, "query success", "Logo获取成功", bean=data)
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result)

    # def post(self, request, *args, **kwargs):
    #     """
    #     添加logo
    #     ---
    #     parameters:
    #         - name: logo
    #           description: 图片
    #           required: true
    #           type: file
    #           paramType: form
    #
    #     """
    #     try:
    #         code = 200
    #         logo_url = config_service.upload_image(request)
    #         data = dict()
    #         data["logo"] = str(request.get_host()) + str(logo_url)
    #         result = general_message(code, "success", "图片上传成功", bean=data)
    #     except ParamsError as e:
    #         code = 400
    #         result = general_message(code, "params error", e.message)
    #     except Exception as e:
    #         code = 500
    #         logger.exception(e)
    #         result = error_message(e.message)
    #     return Response(result, status=code)


class TitleView(BaseApiView):
    def get(self, request, *args, **kwargs):
        """
        获取当前云帮Title
        ---

        """
        data = dict()
        try:
            code = 200
            title = config_service.get_config_by_key("TITLE")
            if not title:
                config = config_service.add_config("TITLE", "好雨云帮", "string", "云帮title")
                title = config.value
            data["title"] = title
            result = general_message(code, "success", "云帮标题获取成功", bean=data)
        except Exception as e:
            code = 500
            result = error_message(e.message)
            logger.exception(e)
        return Response(result, status=code)

    # def put(self, request, *args, **kwargs):
    #     """
    #     修改当前云帮Title
    #     ---
    #     parameters:
    #         - name: title
    #           description: 云帮标题
    #           required: true
    #           type: string
    #           paramType: form
    #
    #     """
    #     try:
    #         code = 200
    #         title = request.data.get("title", None)
    #         if title:
    #             config_service.update_config("TITLE", title)
    #         result = general_message(code, "success", "title修改成功")
    #     except Exception as e:
    #         logger.exception(e)
    #         code = 500
    #         result = error_message(e.message)
    #     return Response(result, status=code)


class AnnouncementView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        """
        获取站内消息
        ---

        """
        try:
            code = 200
            context = announcement_repo.get_announcement()
            result = general_message(code, "query success", "站内消息获取成功", bean=context)
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class GuideView(BaseApiView):
    def get(self, request, *args, **kwargs):
        """
        获取当前新手指南
        ---
        parameters:
            - name: title
              description: 云帮标题
              required: true
              type: string
              paramType: form

        """
        pass

    def post(self, request, *args, **kwargs):
        """
        修改当前新手指南
        ---
        parameters:
            - name: guide
              description: 新手指南
              required: true
              type: string
              paramType: form
        """
        pass


class SafetyView(BaseApiView):
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


class SafetyRegistView(BaseApiView):
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


class SafetyTenantView(BaseApiView):
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


class AuthorizationAView(BaseApiView):
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


class ConfigGithubView(BaseApiView):
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


class ConfigGitlabView(BaseApiView):
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


class ConfigCodeView(BaseApiView):
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


class PhpConfigView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        """获取php的环境配置"""

        versions = ["5.6.11", "5.6.30", "5.6.35", "7.0.16", "7.0.29", "7.1.2", "7.1.16"]
        default_version = "5.6.11"

        extends = [
            {"name": "BCMath", "value": "bcmath", "url": "http://docs.php.net/bcmath", "version": None},
            {"name": "Calendar", "value": "calendar", "url": "http/docs.php.net/calendar", "version": None},
            {"name": "Exif", "value": "exif", "url": "http://docs.php.net/exif", "version": "1.4"},
            {"name": "FTP", "value": "ftp", "url": "http://docs.php.net/ftp", "version": None},
            {"name": "GD(支持PNG, JPEG 和 FreeType)", "value": "gd", "url": "http://docs.php.net/gd", "version": "2.1.0"},
            {"name": "gettext", "value": "gettext", "url": "http://docs.php.net/gettext", "version": None},
            {"name": "intl", "value": "intl", "url": "http://docs.php.net/intl", "version": "1.1.0"},
            {"name": "mbstring", "value": "mbstring", "url": "http://docs.php.net/mbstring", "version": "1.3.2"},
            {"name": "MySQL(PHP 5.5 版本已经停止支持，请使用 MySQLi 或 PDO)", "value": "mysql",
             "url": "http://docs.php.net/book.mysql", "version": "mysqlnd 5.0.11-dev"},
            {"name": "PCNTL", "value": "pcntl", "url": "http://docs.php.net/pcntl", "version": None},
            {"name": "Shmop", "value": "shmop", "url": "http://docs.php.net/shmop", "version": None},
            {"name": "SOAP", "value": "soap", "url": "http://docs.php.net/soap", "version": None},
            {"name": "SQLite3", "value": "sqlite3", "url": "http://docs.php.net/sqlite3", "version": "0.7-dev"},
            {"name": "SQLite(PDO)", "value": "pdo_sqlite", "url": "http://docs.php.net/pdo_sqlite", "version": "3.8.2"},
            {"name": "XMLRPC", "value": "xmlrpc", "url": "http://docs.php.net/xmlrpc", "version": "0.51"},
            {"name": "XSL", "value": "xsl", "url": "http://docs.php.net/xsl", "version": "1.1.28"},
            {"name": "APCu", "value": "apcu", "url": "http://pecl.php.net/package/apcu", "version": "4.0.6"},
            {"name": "Blackfire", "value": "blackfire", "url": "http://blackfire.io/", "version": "0.20.6"},
            {"name": "memcached", "value": "memcached", "url": "http://docs.php.net/memcached", "version": "2.2.0"},
            {"name": "MongoDB", "value": "mongodb", "url": "http://docs.php.net/mongo", "version": "1.6.6"},
            {"name": "NewRelic", "value": "newrelic", "url": "http://newrelic.com/php", "version": "4.19.0.90"},
            {"name": "OAuth", "value": "oauth", "url": "http://docs.php.net/oauth", "version": "1.2.3"},
            {"name": "PHPRedis", "value": "redis", "url": "http://pecl.php.net/package/redis", "version": "2.2.7"}
        ]
        bean = {"versions": versions, "default_version": default_version, "extends": extends}
        return Response(general_message(200, "success", "查询成功", bean))
