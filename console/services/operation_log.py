# -*- coding: utf8 -*-
import json
import logging
import time
from enum import Enum

from console.repositories.group import group_repo
from console.repositories.operation_log import operation_log_repo
from console.repositories.region_repo import region_repo
from console.services.group_service import service_repo
from console.repositories.user_repo import user_repo
from console.repositories.team_repo import team_repo
from console.views.app_config.base import AppBaseView
from deprecated import deprecated
from django.core.paginator import Paginator
from django.db.models import Q

logger = logging.getLogger("default")


class Operation(Enum):
    FOR = "为"
    IN = "在"
    ADD = "添加了"
    CREATE = "创建了"
    UPDATE = "编辑了"
    DELETE = "删除了"
    FINISH = "完成了"
    IMPORT = "导入了"
    EXPORT = "导出了"
    JOIN = "加入了"
    EXIT = "退出了"
    RESET = "重置了"
    OPEN = "打开了"
    CLOSE = "关闭了"
    DISABLE = "禁用了"
    ENABLE = "启用了"
    APPLYJOIN = "申请加入"
    CANCEL_JOIN = "撤销了加入"
    REGENERATED = "重新生成了"
    INSTALL = "安装了"
    UNINSTALL = "卸载了"
    BUILD = "构建了"
    THROUGH = "通过了"
    REJECT = "拒绝了"
    TRUN_OVER = "移交了"
    START = "启动了"
    UPGRADE = "更新了"
    STOP = "停止了"
    RESTART = "重启了"
    DEPLOY = "构建了"
    SHARE = "分享了"
    BACKUP = "备份了"
    UPDATE2 = "升级了"
    CHANGE = "修改了"
    BATCH_START = "批量启动了"
    BATCH_RESTART = "批量重启了"
    BATCH_STOP = "批量停止了"
    BATCH_DEPLOY = "批量构建了"
    BATCH_UPGRADE = "批量更新了"
    BATCH_DELETE = "批量删除了"
    BATCH_MOVE = "移动了"
    ROLL_BACK = "回滚了"
    RE_CHECK = "重新检测了"
    VERTICAL_SCALE = "垂直伸缩了"
    HORIZONTAL_SCALE = "水平伸缩了"
    TRANSFER = "转移了"
    CANCEL = "取消了"
    LIMIT = "限制了"
    REMOVE = "移除了"
    Set = "设置了"


class OperationModule(Enum):
    REGISTER = "注册"
    LOGIN = "登录"
    TEAM = "团队"
    FAVORITE = "收藏"
    APP = "应用"
    APPMODEL = "应用模版"
    APPSTORE = "应用商店"
    CLUSTER = "集群"
    RESOURCELIMIT = "资源限额"
    USER = "用户"
    USERINFO = "用户信息"
    CERTSIGN = "证书签发功能"
    OAUTHCONNECT = "OAUTH互联功能"
    OAUTHCONFIG = "OAUTH配置"
    ENTERPRISEADMIN = "企业管理员"
    ACCESSKEY = "访问令牌"
    HTTPGATEWAYPOLICY = "HTTP网关策略"
    TCPPOLICY = "TCP策略"
    GATEWAYCONFIG = "网关参数"
    PLUGIN = "插件"
    PLUGINCONFIG = "插件配置"
    COMPONENT = "组件"
    PASS_WORD = "密码"
    REGION = "数据中心"
    SHARED_STORAGE = "共享存储"
    SHARED_CONFIG_FILE = "共享配置文件"
    APP_STORE_IMAGE_HUB = "组件库镜像仓库"
    OBJECT_STORAGE = "对象存储"


class OperationType(Enum):
    ENTERPRISE_MANAGE = "enterprise_manage"
    CLUSTER_MANAGE = "cluster_manage"
    COMPONENT_LIBRARY_MANAGE = "component_library_manage"
    TEAM_MANAGE = "team_manage"
    APPLICATION_MANAGE = "application_manage"
    COMPONENT_MANAGE = "component_manage"


class InformationType(Enum):
    INFORMATION_ADD = "information_add"
    INFORMATION_DELETE = "information_delete"
    INFORMATION_EDIT = "information_edit"
    INFORMATION_ADDS = "information_adds"
    INFORMATION_DELETES = "information_deletes"
    NO_DETAILS = "no_details"


class OperationViewType(Enum):
    ENTERPRISE = "enterprise"
    TEAM = "team"
    APP = "app"
    COMPONENT = "component"
    PLUGIN = "plugin"
    TEAM_APPLICATION = "team_application"


class OperationLogService(object):
    def create_log(self,
                   user,
                   operation_type,
                   comment,
                   enterprise_id='',
                   team_name='',
                   app_id=0,
                   service_alias='',
                   is_openapi=False,
                   service_cname='',
                   app_name='',
                   old_information='',
                   new_information='',
                   information_type=''):
        try:
            if service_alias != '':
                service = service_repo.get_service_by_service_alias(service_alias)
                if service:
                    service_cname = service.service_cname
            operation_log = {
                "create_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                "username": user.nick_name if user else "匿名",
                "operation_type": operation_type.value,
                "enterprise_id": enterprise_id,
                "team_name": team_name,
                "app_id": app_id,
                "service_alias": service_alias,
                "comment": comment,
                "is_openapi": is_openapi,
                "service_cname": service_cname,
                "app_name": app_name,
                "new_information": new_information,
                "old_information": old_information,
                "information_type": information_type
            }
            operation_log_repo.create(**operation_log)
        except Exception as e:
            logger.error(e)

    def list(self, enterprise_id, query_params):
        q = Q(enterprise_id=enterprise_id) & self.handle_query_condition(query_params)
        logs = operation_log_repo.list().filter(q).order_by("-create_time")

        p = Paginator(logs, query_params["page_size"])
        total = p.count
        return p.page(query_params["page"]).object_list, total

    def list_team_logs(self, enterprise_id, tenant, query_params):
        q = Q(enterprise_id=enterprise_id) & Q(team_name=tenant.tenant_name)
        q &= self.handle_query_condition(query_params)
        logs = operation_log_repo.list().filter(q).order_by("-create_time")

        p = Paginator(logs, query_params["page_size"])
        total = p.count
        return p.page(query_params["page"]).object_list, total

    def list_app_logs(self, enterprise_id, tenant, app, query_params):
        q = Q(enterprise_id=enterprise_id, team_name=tenant.tenant_name, app_id=app.ID)
        q &= self.handle_query_condition(query_params)
        logs = operation_log_repo.list().filter(q).order_by("-create_time")

        p = Paginator(logs, query_params["page_size"])
        total = p.count
        return p.page(query_params["page"]).object_list, total

    def handle_query_condition(self, params):
        q = Q()
        if params.get("start_time", None):
            q &= Q(create_time__gte=params["start_time"])
        if params.get("end_time", None):
            q &= Q(create_time__lte=params["end_time"])
        if params.get("username", None):
            q &= Q(username=params["username"])
        if params.get("operation_type", None):
            q &= Q(operation_type=params["operation_type"])
        if params.get("service_alias", None):
            q &= Q(service_alias=params["service_alias"])
        if params.get("app_id", None):
            q &= Q(app_id=params["app_id"])
        if params.get("query", None):
            q &= Q(comment__icontains=params["query"])
        return q

    # Processing names as jump parameters
    def process_name(self, region, name, view_type, team_name='', app_id=0, service_alias='', plugin_id=''):
        body = None
        name = name.value if isinstance(name, Enum) else name
        name = name.replace("<<", "").replace(">>", "")

        view_type = view_type.value if isinstance(view_type, Enum) else view_type
        if view_type == OperationViewType.TEAM.value or view_type == OperationViewType.TEAM_APPLICATION.value:
            body = {"region": region, "name": name, "team_name": team_name, "view_type": view_type}
        if view_type == OperationViewType.APP.value:
            body = {"region": region, "name": name, "team_name": team_name, "app_id": app_id, "view_type": view_type}
        if view_type == OperationViewType.COMPONENT.value:
            body = {
                "region": region,
                "name": name,
                "team_name": team_name,
                "service_alias": service_alias,
                "view_type": view_type
            }
        if view_type == OperationViewType.PLUGIN.value:
            body = {"region": region, "name": name, "team_name": team_name, "plugin_id": plugin_id, "view_type": view_type}
        if not body:
            return ""
        data = json.dumps(body)
        return "<<" + data + ">>"

    # Generate some formatted text
    def generate_generic_comment(self, operation, module, module_name, suffix=''):
        operation = operation.value if isinstance(operation, Enum) else operation
        module = module.value if isinstance(module, Enum) else module
        return operation + module + ' ' + module_name + suffix

    def create_enterprise_log(self, user, comment, enterprise_id, is_openapi=False, old_information="", new_information=""):
        information_type = self.type_log(old_information=old_information, new_information=new_information)
        self.create_log(
            user,
            operation_type=OperationType.ENTERPRISE_MANAGE,
            comment=comment,
            enterprise_id=enterprise_id,
            is_openapi=is_openapi,
            old_information=old_information,
            new_information=new_information,
            information_type=information_type.value)

    def create_component_library_log(self,
                                     user,
                                     comment,
                                     enterprise_id,
                                     is_openapi=False,
                                     old_information="",
                                     new_information=""):
        information_type = self.type_log(old_information=old_information, new_information=new_information)
        self.create_log(
            user,
            operation_type=OperationType.COMPONENT_LIBRARY_MANAGE,
            comment=comment,
            enterprise_id=enterprise_id,
            is_openapi=is_openapi,
            new_information=new_information,
            old_information=old_information,
            information_type=information_type.value)

    def create_cluster_log(self, user, comment, enterprise_id, is_openapi=False, new_information="", old_information=""):
        information_type = self.type_log(old_information=old_information, new_information=new_information)
        self.create_log(
            user,
            operation_type=OperationType.CLUSTER_MANAGE,
            comment=comment,
            enterprise_id=enterprise_id,
            is_openapi=is_openapi,
            new_information=new_information,
            information_type=information_type.value)

    def create_team_log(self, user, comment, enterprise_id, team_name, is_openapi=False, old_information="",
                        new_information=""):
        information_type = self.type_log(old_information=old_information, new_information=new_information)
        self.create_log(
            user,
            operation_type=OperationType.TEAM_MANAGE,
            comment=comment,
            enterprise_id=enterprise_id,
            team_name=team_name,
            is_openapi=is_openapi,
            new_information=new_information,
            old_information=old_information,
            information_type=information_type.value)

    def create_app_log(self, ctx, comment, is_openapi=False, format_app=True, old_information="", new_information=""):
        information_type = self.type_log(old_information=old_information, new_information=new_information)
        try:
            ctx.app
        except AttributeError as e:
            # make sure ctx has attribute app
            logger.warning(e)
            return
        if format_app:
            app = self.process_app_name(ctx.app.group_name, ctx.region_name, ctx.tenant_name, ctx.app.app_id)
            comment = comment.format(app=app)
        self.create_log(
            ctx.user,
            operation_type=OperationType.APPLICATION_MANAGE,
            comment=comment,
            enterprise_id=ctx.user.enterprise_id,
            team_name=ctx.tenant_name,
            app_id=ctx.app.app_id,
            app_name=ctx.app.app_name,
            is_openapi=is_openapi,
            old_information=old_information,
            new_information=new_information,
            information_type=information_type.value)

    @deprecated
    def create_component_log(self,
                             user,
                             comment,
                             enterprise_id,
                             team_name,
                             app_id,
                             service_alias,
                             is_openapi=False,
                             service_cname='',
                             new_information='',
                             old_information=''):
        app = group_repo.get_app_by_pk(app_id)
        app_name = self.process_app_name(app.app_name, app.region_name, team_name, app_id)
        information_type = self.type_log(old_information=old_information, new_information=new_information)
        self.create_log(
            user,
            operation_type=OperationType.COMPONENT_MANAGE,
            comment="在应用 {} 中".format(app_name) + comment,
            enterprise_id=enterprise_id,
            team_name=team_name,
            app_id=app_id,
            service_alias=service_alias,
            is_openapi=is_openapi,
            service_cname=service_cname,
            app_name=app.app_name,
            new_information=new_information,
            old_information=old_information,
            information_type=information_type.value)

    def create_component_log_v2(self, ctx, comment, is_openapi=False, new_information="", old_information=""):
        if not isinstance(ctx, AppBaseView):
            logger.warning("ctx is not instance of AppBaseView: {}".format(ctx))
            return
        information_type = self.type_log(new_information=new_information, old_information=old_information)
        comment = comment.format(
            component=self.process_component_name(ctx.component.service_cname, ctx.region_name, ctx.team_name,
                                                  ctx.component.service_alias))
        self.create_log(
            ctx.user,
            operation_type=OperationType.COMPONENT_MANAGE,
            comment=comment,
            enterprise_id=ctx.user.enterprise_id,
            team_name=ctx.team_name,
            app_id=ctx.app.app_id,
            service_alias=ctx.component.service_alias,
            is_openapi=is_openapi,
            new_information=new_information,
            old_information=old_information,
            information_type=information_type.value)

    def type_log(self, new_information, old_information):
        information_type = InformationType.NO_DETAILS
        if new_information and old_information:
            information_type = InformationType.INFORMATION_EDIT
        elif new_information and isinstance(json.loads(new_information), list):
            information_type = InformationType.INFORMATION_ADDS
        elif new_information:
            information_type = InformationType.INFORMATION_ADD
        elif old_information and isinstance(json.loads(old_information), list):
            information_type = InformationType.INFORMATION_DELETES
        elif old_information:
            information_type = InformationType.INFORMATION_DELETE
        return information_type

    def process_team_name(self, name, region, team_name):
        return self.process_name(region=region, name=name, view_type=OperationViewType.TEAM, team_name=team_name)

    def process_app_name(self, name, region, team_name, app_id):
        return self.process_name(region=region, name=name, view_type=OperationViewType.APP, team_name=team_name, app_id=app_id)

    def process_component_name(self, name, region, team_name, service_alias):
        return self.process_name(
            region=region, name=name, view_type=OperationViewType.COMPONENT, team_name=team_name, service_alias=service_alias)

    def process_plugin_name(self, name, region, team_name, plugin_id):
        return self.process_name(
            region=region, name=name, view_type=OperationViewType.PLUGIN, team_name=team_name, plugin_id=plugin_id)

    def generate_team_comment(self, operation, module_name, suffix='', region='', team_name=''):
        if region == '' and team_name != '':
            tenant_regions = region_repo.get_region_by_tenant_name(team_name)
            region = tenant_regions[0].region_name if tenant_regions else ''
        if region != '' and team_name != '':
            module_name = self.process_team_name(module_name, region, team_name)
        return self.generate_generic_comment(operation, OperationModule.TEAM, module_name, suffix)

    def generate_component_comment(self, operation, module_name, suffix='', region='', team_name='', service_alias=''):
        if region != '' and team_name != '' and service_alias != '':
            module_name = self.process_component_name(module_name, region, team_name, service_alias)
        return self.generate_generic_comment(operation, OperationModule.COMPONENT, module_name, suffix)

    def port_action_to_zh(self, action):
        if action == "open_outer" or action == "close_outer":
            return "对外服务"
        if action == "open_inner" or action == "close_inner":
            return "对内服务"
        if action == "change_protocol":
            return "协议"
        if action == "change_port_alias":
            return "端口别名"

    def handle_logs(self, enterprise_id, logs):
        allusers = user_repo.get_all_users()
        users = {user.username: user for user in allusers}
        allteams = team_repo.get_team_by_enterprise_id(enterprise_id).all()
        teams = {team.tenant_name: team for team in allteams}
        result = []
        for log in logs:
            tenant = teams.get(log["team_name"])
            user = users.get(log["username"])
            data = {
                "create_time": log["create_time"],
                "team_alias": tenant.tenant_alias if tenant else log["team_name"],
                "comment": log["comment"],
                "real_name": user.get_name() if user else log["username"],
            }
            result.append(data)
        return result


operation_log_service = OperationLogService()
