# -*- coding: utf8 -*-
import datetime
import logging
import os

from rest_framework.response import Response

from backends.services.configservice import config_service
from cadmin.models import ConsoleSysConfig
from console.repositories.enterprise_repo import enterprise_repo
from console.views.base import BaseApiView, AlowAnyApiView
from www.utils.return_message import general_message, error_message
from django.conf import settings
from console.repositories.perm_repo import role_perm_repo
from console.repositories.user_repo import user_repo
logger = logging.getLogger("default")


class ConfigInfoView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        """
        登录页面获取云帮Logo、标题、github、gitlab配置信息(不要Authorization头)
        ---
        """
        try:
            # 判断是否已经初始化权限默认数据，没有则初始化
            status = role_perm_repo.initialize_permission_settings()
            code = 200
            data = dict()
            logo = config_service.get_image()
            host_name = request.get_host()
            build_absolute_uri = request.build_absolute_uri()
            scheme = "http"

            if build_absolute_uri.startswith("https"):
                scheme = "https"
            data["logo"] = "{0}".format(str(logo))
            # 判断是否为公有云
            if settings.MODULES.get('SSO_LOGIN'):
                data["url"] = os.getenv(
                    "SSO_BASE_URL", "https://sso.goodrain.com") + "/#/login/"
                data["is_public"] = True
            else:
                data["url"] = "{0}://{1}/index#/user/login".format(
                    scheme, request.get_host())
                data["is_public"] = False

            title = config_service.get_config_by_key("TITLE")
            if not title:
                config = config_service.add_config("TITLE", "好雨云帮", "string",
                                                   "云帮title")
                title = config.value
            data["title"] = title
            if settings.MODULES.get('SSO_LOGIN'):
                data["is_user_register"] = True
            else:
                users = user_repo.get_all_users()
                if users:
                    data["is_user_register"] = True
                else:
                    data["is_user_register"] = False

            is_regist = config_service.get_config_by_key("REGISTER_STATUS")
            if not is_regist:
                is_regist = config_service.add_config(
                    key="REGISTER_STATUS",
                    default_value="yes",
                    type="string",
                    desc="开启/关闭注册").value
            if is_regist == "yes":
                data["is_regist"] = True
            else:
                data["is_regist"] = False
            # if register_config[0].value != "yes":
            #     data["is_regist"] = False
            # else:
            #     data["is_regist"] = True

            github_config = config_service.get_github_config()
            data["github_config"] = github_config

            gitlab_config = config_service.get_gitlab_config()
            data["gitlab_config"] = gitlab_config

            data["eid"] = None
            enterprise = enterprise_repo.get_enterprise_first()
            if enterprise:
                data["eid"] = enterprise.enterprise_id
                data["enterprise_name"] = enterprise.enterprise_alias
            data["version"] = os.getenv("RELEASE_DESC", "public-cloud")
            result = general_message(
                code,
                "query success",
                "Logo获取成功",
                bean=data,
                initialize_info=status)
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
            result = general_message(
                code, "query success", "Logo获取成功", bean=data)
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


class PhpConfigView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        """获取php的环境配置"""

        versions = [
            "5.6.11", "5.6.30", "5.6.35", "7.0.16", "7.0.29", "7.1.2", "7.1.16"
        ]
        default_version = "5.6.11"

        extends = [{
            "name": "BCMath",
            "value": "bcmath",
            "url": "http://docs.php.net/bcmath",
            "version": None
        },
                   {
                       "name": "Calendar",
                       "value": "calendar",
                       "url": "http/docs.php.net/calendar",
                       "version": None
                   },
                   {
                       "name": "Exif",
                       "value": "exif",
                       "url": "http://docs.php.net/exif",
                       "version": "1.4"
                   },
                   {
                       "name": "FTP",
                       "value": "ftp",
                       "url": "http://docs.php.net/ftp",
                       "version": None
                   },
                   {
                       "name": "GD(支持PNG, JPEG 和 FreeType)",
                       "value": "gd",
                       "url": "http://docs.php.net/gd",
                       "version": "2.1.0"
                   },
                   {
                       "name": "gettext",
                       "value": "gettext",
                       "url": "http://docs.php.net/gettext",
                       "version": None
                   },
                   {
                       "name": "intl",
                       "value": "intl",
                       "url": "http://docs.php.net/intl",
                       "version": "1.1.0"
                   },
                   {
                       "name": "mbstring",
                       "value": "mbstring",
                       "url": "http://docs.php.net/mbstring",
                       "version": "1.3.2"
                   },
                   {
                       "name": "MySQL(PHP 5.5 版本已经停止支持，请使用 MySQLi 或 PDO)",
                       "value": "mysql",
                       "url": "http://docs.php.net/book.mysql",
                       "version": "mysqlnd 5.0.11-dev"
                   },
                   {
                       "name": "PCNTL",
                       "value": "pcntl",
                       "url": "http://docs.php.net/pcntl",
                       "version": None
                   },
                   {
                       "name": "Shmop",
                       "value": "shmop",
                       "url": "http://docs.php.net/shmop",
                       "version": None
                   },
                   {
                       "name": "SOAP",
                       "value": "soap",
                       "url": "http://docs.php.net/soap",
                       "version": None
                   },
                   {
                       "name": "SQLite3",
                       "value": "sqlite3",
                       "url": "http://docs.php.net/sqlite3",
                       "version": "0.7-dev"
                   },
                   {
                       "name": "SQLite(PDO)",
                       "value": "pdo_sqlite",
                       "url": "http://docs.php.net/pdo_sqlite",
                       "version": "3.8.2"
                   },
                   {
                       "name": "XMLRPC",
                       "value": "xmlrpc",
                       "url": "http://docs.php.net/xmlrpc",
                       "version": "0.51"
                   },
                   {
                       "name": "XSL",
                       "value": "xsl",
                       "url": "http://docs.php.net/xsl",
                       "version": "1.1.28"
                   },
                   {
                       "name": "APCu",
                       "value": "apcu",
                       "url": "http://pecl.php.net/package/apcu",
                       "version": "4.0.6"
                   },
                   {
                       "name": "Blackfire",
                       "value": "blackfire",
                       "url": "http://blackfire.io/",
                       "version": "0.20.6"
                   },
                   {
                       "name": "memcached",
                       "value": "memcached",
                       "url": "http://docs.php.net/memcached",
                       "version": "2.2.0"
                   },
                   {
                       "name": "MongoDB",
                       "value": "mongodb",
                       "url": "http://docs.php.net/mongo",
                       "version": "1.6.6"
                   },
                   {
                       "name": "NewRelic",
                       "value": "newrelic",
                       "url": "http://newrelic.com/php",
                       "version": "4.19.0.90"
                   },
                   {
                       "name": "OAuth",
                       "value": "oauth",
                       "url": "http://docs.php.net/oauth",
                       "version": "1.2.3"
                   },
                   {
                       "name": "PHPRedis",
                       "value": "redis",
                       "url": "http://pecl.php.net/package/redis",
                       "version": "2.2.7"
                   }]
        bean = {
            "versions": versions,
            "default_version": default_version,
            "extends": extends
        }
        return Response(general_message(200, "success", "查询成功", bean))
