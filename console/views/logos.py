# -*- coding: utf8 -*-
import logging
import os

from rest_framework.response import Response

from console.repositories.enterprise_repo import enterprise_repo
from console.repositories.perm_repo import role_perm_repo
from console.services.config_service import config_service
from console.views.base import AlowAnyApiView
from console.views.base import BaseApiView
from www.utils.return_message import error_message
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class ConfigInfoView(AlowAnyApiView):
    """
    获取配置信息
    ---
    """
    def get(self, request, *args, **kwargs):
        try:
            code = 200
            status = role_perm_repo.initialize_permission_settings()
            data = config_service.initialization_or_get_config()
            logo = config_service.get_image()
            data["logo"] = "{0}".format(str(logo))
            title = config_service.get_config_by_key("TITLE").value
            if not title:
                config = config_service.add_config("TITLE", "Rainbond-企业云应用操作系统，开发、交付云解决方案", "string", "云帮title")
                title = config.value
            data["title"] = title
            data["version"] = os.getenv("RELEASE_DESC", "public-cloud")
            result = general_message(code, "query success", u"Logo获取成功", bean=data, initialize_info=status)
            data["eid"] = None
            enterprise = enterprise_repo.get_enterprise_first()
            if enterprise:
                data["eid"] = enterprise.enterprise_id
                data["enterprise_name"] = enterprise.enterprise_alias
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


class PhpConfigView(AlowAnyApiView):
    def get(self, request, *args, **kwargs):
        """获取php的环境配置"""

        versions = ["5.6.11", "5.6.30", "5.6.35", "7.0.16", "7.0.29", "7.1.2", "7.1.16"]
        default_version = "5.6.11"

        extends = [{
            "name": "BCMath",
            "value": "bcmath",
            "url": "http://docs.php.net/bcmath",
            "version": None
        }, {
            "name": "Calendar",
            "value": "calendar",
            "url": "http/docs.php.net/calendar",
            "version": None
        }, {
            "name": "Exif",
            "value": "exif",
            "url": "http://docs.php.net/exif",
            "version": "1.4"
        }, {
            "name": "FTP",
            "value": "ftp",
            "url": "http://docs.php.net/ftp",
            "version": None
        }, {
            "name": "GD(支持PNG, JPEG 和 FreeType)",
            "value": "gd",
            "url": "http://docs.php.net/gd",
            "version": "2.1.0"
        }, {
            "name": "gettext",
            "value": "gettext",
            "url": "http://docs.php.net/gettext",
            "version": None
        }, {
            "name": "intl",
            "value": "intl",
            "url": "http://docs.php.net/intl",
            "version": "1.1.0"
        }, {
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
        }, {
            "name": "PCNTL",
            "value": "pcntl",
            "url": "http://docs.php.net/pcntl",
            "version": None
        }, {
            "name": "Shmop",
            "value": "shmop",
            "url": "http://docs.php.net/shmop",
            "version": None
        }, {
            "name": "SOAP",
            "value": "soap",
            "url": "http://docs.php.net/soap",
            "version": None
        }, {
            "name": "SQLite3",
            "value": "sqlite3",
            "url": "http://docs.php.net/sqlite3",
            "version": "0.7-dev"
        }, {
            "name": "SQLite(PDO)",
            "value": "pdo_sqlite",
            "url": "http://docs.php.net/pdo_sqlite",
            "version": "3.8.2"
        }, {
            "name": "XMLRPC",
            "value": "xmlrpc",
            "url": "http://docs.php.net/xmlrpc",
            "version": "0.51"
        }, {
            "name": "XSL",
            "value": "xsl",
            "url": "http://docs.php.net/xsl",
            "version": "1.1.28"
        }, {
            "name": "APCu",
            "value": "apcu",
            "url": "http://pecl.php.net/package/apcu",
            "version": "4.0.6"
        }, {
            "name": "Blackfire",
            "value": "blackfire",
            "url": "http://blackfire.io/",
            "version": "0.20.6"
        }, {
            "name": "memcached",
            "value": "memcached",
            "url": "http://docs.php.net/memcached",
            "version": "2.2.0"
        }, {
            "name": "MongoDB",
            "value": "mongodb",
            "url": "http://docs.php.net/mongo",
            "version": "1.6.6"
        }, {
            "name": "NewRelic",
            "value": "newrelic",
            "url": "http://newrelic.com/php",
            "version": "4.19.0.90"
        }, {
            "name": "OAuth",
            "value": "oauth",
            "url": "http://docs.php.net/oauth",
            "version": "1.2.3"
        }, {
            "name": "PHPRedis",
            "value": "redis",
            "url": "http://pecl.php.net/package/redis",
            "version": "2.2.7"
        }]
        bean = {"versions": versions, "default_version": default_version, "extends": extends}
        return Response(general_message(200, "success", "查询成功", bean))
