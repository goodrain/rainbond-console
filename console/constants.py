# -*- coding: utf8 -*-
"""
  Created on 18/1/24.
"""
from goodrain_web import settings


class AppConstants(object):
    DOCKER_RUN = "docker_run"
    SOURCE_CODE = "source_code"
    THIRD_PARTY = "third_party"
    MARKET = "market"
    DOCKER_COMPOSE = "docker_compose"
    DOCKER_IMAGE = "docker_image"
    PACKAGE_BUILD = "package_build"
    VM_RUN = "vm_run"


class LogConstants(object):
    """日志常量"""
    INFO = "info"
    DEBUG = "debug"
    ERROR = "error"
    """组件日志类型常量"""
    SERVICE = "service"
    COMPILE = "compile"
    OPERATE = "operate"


class ServiceEventConstants(object):
    TYPE_MAP = {
        "stop": "停止",
        "restart": "启动",
        "deploy": "构建",
        "upgrade": "更新",
        "delete": "删除",
        "HorizontalUpgrade": "水平升级",
        "VerticalUpgrade": "垂直升级",
        "create": "创建",
        "callback": "回滚",
        "share-yb": "云帮分享",
        "share-ys": "云市分享",
        "git-change": "代码仓库修改",
        "own_money": "欠费关闭",
        "add_label": "添加标签",
        "delete_label": "删除标签",
        "service_state": "组件状态修改",
        "reboot": "重启",
        "market_sync": "云市同步",
        "truncate": "删除"
    }


class ServicePortConstants(object):
    NO_PORT = "no_port"
    HTTP_PORT = "http_port"
    NOT_HTTP_OUTER = "not_http_outer"
    NOT_HTTP_INNER = "not_http_inner"
    HTTP_INNER = "http_inner"
    # 协议类型
    HTTP = "http"


class SourceCodeType(object):
    GITLAB_MANUAL = "gitlab_manual"
    GITLAB_SELF = "gitlab_self"
    GITLAB_NEW = "gitlab_new"
    GITLAB_EXIT = "gitlab_exit"
    GITHUB = "github"
    GITLAB_DEMO = "gitlab_demo"


class ServiceCreateConstants(object):
    FIRST_CREATE = "creating"
    CHECKING_SERVICE = 'checking'
    CHECKED = "checked"
    CREATE_COMPLETE = 'complete'


class PluginCategoryConstants(object):
    OUTPUT_NET = "net-plugin:down"
    INPUT_NET = "net-plugin:up"
    OUTPUT_INPUT_NET = "net-plugin:in-and-out"
    INIT_TYPE = "init-plugin"
    PERFORMANCE_ANALYSIS = "analyst-plugin:perf"
    COMMON_TYPE = "general-plugin"
    EXPORTER_TYPE = "exporter-plugin"


class DefaultPluginConstants(object):
    PERF_ANALYZE_PLUGIN = "perf_analyze_plugin"
    DOWNSTREAM_NET_PLUGIN = "downstream_net_plugin"
    INANDOUT_NET_PLUGIN = "inandout_net_plugin"
    FILEBEAT_LOG_PLUGIN = "filebeat_log_plugin"
    LOGTAIL_LOG_PLUGIN = "logtail_log_plugin"
    MYSQLD_EXPORTER_PLUGIN = "mysqld_exporter"


class PluginMetaType(object):
    UPSTREAM_PORT = "upstream_port"
    DOWNSTREAM_PORT = "downstream_port"
    UNDEFINE = "un_define"
    PLUGINSTORAGE = "plugin_storage"


class PluginInjection(object):
    AUTO = "auto"
    EVN = "env"


class MessageType(object):
    ANNOUNCEMENT = "announcement"
    NEWS = "news"
    WARN = "warn"


class AppMigrateType(object):
    CURRENT_REGION_CURRENT_TENANT = "cdct"
    OTHER_REGION = "od"
    CURRENT_REGION_OTHER_TENANT = "cdot"


class StorageUnit(object):
    ONE_MB = 1048576


class DomainType(object):
    SLD_DOMAIN = "goodrain-sld"
    WWW = "www"


class PluginImage(object):
    RUNNER = settings.IMAGE_REPO + "/runner"


class ServiceLanguageConstants(object):
    DOCKER_FILE = "dockerfile"
    STATIC = "static"
    JAVA_MAVEN = "Java-maven"
    JAVA_WAR = "Java-war"
    JAVA_JAR = "Java-jar"
    PHP = "PHP"
    PYTHON = "Python"
    NODE_JS = "Node.js"
    RUBY = "Ruby"
    CLOJURE = "Clojure"
    GO = "Go"
    GRADLE = "Gradle"
    PLAY = "Play"
    GRAILS = "Grails"
    SCALA = "Scala"
