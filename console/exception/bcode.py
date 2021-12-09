# -*- coding: utf8 -*-
from console.exception.main import ServiceHandleException


# 20000 ~ 20099 => user
class ErrUserNotFound(ServiceHandleException):
    def __init__(self, message=""):
        msg = "user not found"
        super(ErrUserNotFound, self).__init__(msg)
        self.msg_show = "用户不存在"
        self.status_code = 404
        self.error_code = 20000


# 20100 ~ 20199 => app config group
class ErrAppConfigGroupExists(ServiceHandleException):
    def __init__(self):
        msg = "app config group exists"
        super(ErrAppConfigGroupExists, self).__init__(msg)
        self.msg_show = "应用配置组已存在"
        self.status_code = 409
        self.error_code = 20100


class ErrAppConfigGroupNotFound(ServiceHandleException):
    def __init__(self):
        msg = "app config group not found"
        super(ErrAppConfigGroupNotFound, self).__init__(msg)
        self.msg_show = "应用配置组不存在"
        self.status_code = 404
        self.error_code = 20101


# 20200 ~ 20299 => component monitor
class ErrComponentGraphNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrComponentGraphNotFound, self).__init__("component graph not found", "组件监控图表不存在", 404, 20200)


class ErrComponentGraphExists(ServiceHandleException):
    def __init__(self):
        super(ErrComponentGraphExists, self).__init__("component graph already exists", "组件监控图表已存在", 409, 20201)


class ErrInternalGraphsNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrInternalGraphsNotFound, self).__init__("internal graphs not found", "内置监控图表不存在", 404, 20202)


class ErrServiceMonitorExists(ServiceHandleException):
    def __init__(self):
        super(ErrServiceMonitorExists, self).__init__("service monitor already exists", "配置名称已存在", 409, 20203)


class ErrRepeatMonitoringTarget(ServiceHandleException):
    def __init__(self):
        super(ErrRepeatMonitoringTarget, self).__init__("repeat monitoring target", "监测指标已存在", 409, 20204)


# 20300 ~ 20399 => oauth
class ErrOauthServiceExists(ServiceHandleException):
    def __init__(self):
        super(ErrOauthServiceExists, self).__init__(
            "oauth service exists", msg_show="OAuth 名称已存在", status_code=409, error_code=20300)


class ErrUnSupportEnterpriseOauth(ServiceHandleException):
    def __init__(self):
        super(ErrUnSupportEnterpriseOauth, self).__init__(
            "Unsupported enterprise Oauth service", msg_show="不支持的企业Oauth服务", status_code=400, error_code=20301)


class ErrUnAuthnOauthService(ServiceHandleException):
    def __init__(self):
        super(ErrUnAuthnOauthService, self).__init__(
            "Unauthenticated oauth service", msg_show="该Oauth服务未认证，请认证后重试", status_code=400, error_code=20302)


class ErrExpiredAuthnOauthService(ServiceHandleException):
    def __init__(self):
        super(ErrExpiredAuthnOauthService, self).__init__(
            "oauth authentication information has expired", msg_show="该Oauth服务认证信息已过期，请重新认证", status_code=400, error_code=20303)


class ErrOauthUserNotLogout(ServiceHandleException):
    def __init__(self):
        super(ErrOauthUserNotLogout, self).__init__(
            "the oauth user is not logged out", msg_show="Oauth 用户尚未退出登录", status_code=409, error_code=20304)


class ErrOauthUserNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrOauthUserNotFound, self).__init__(
            "the oauth user is not found", msg_show="Oauth 用户不存在", status_code=404, error_code=20305)


class ErrOauthServiceNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrOauthServiceNotFound, self).__init__(
            "oauth service is not found", msg_show="OAuth 服务不存在", status_code=404, error_code=20306)


# 20400 ~ 20499 => enterprise
class ErrEnterpriseNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrEnterpriseNotFound, self).__init__("enterprise not found", msg_show="企业不存在", status_code=404, error_code=20400)


# 20500 ~ 20599 => service ports
class ErrK8sServiceNameExists(ServiceHandleException):
    def __init__(self):
        super(ErrK8sServiceNameExists, self).__init__("k8s service name already exists", "内部域名已存在", 409, 20500)


class ErrComponentPortExists(ServiceHandleException):
    def __init__(self):
        super(ErrComponentPortExists, self).__init__("component port already exists", "端口已存在", 409, 20501)


# 20600 ~ 20699 => service plugin
class ErrPluginIsUsed(ServiceHandleException):
    def __init__(self):
        super(ErrPluginIsUsed, self).__init__(
            msg="plugin is used by the service", msg_show="该插件被组件使用，无法删除", status_code=409, error_code=20600)


# 20700 ~ 20799 => tenant
class ErrTenantNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrTenantNotFound, self).__init__(msg="tenant not found", msg_show="团队不存在", status_code=404, error_code=20700)


class ErrNamespaceExists(ServiceHandleException):
    def __init__(self):
        super(ErrNamespaceExists, self).__init__(
            msg="namespace exists", msg_show="团队英文名(命名空间)已存在", status_code=400, error_code=20701)


# 20800 ~ 20899 => component
class ErrComponentBuildFailed(ServiceHandleException):
    def __init__(self):
        super(ErrComponentBuildFailed, self).__init__(
            msg="failed to build component", msg_show="组件构建失败", status_code=400, error_code=20800)


class ErrThirdComponentStartFailed(ServiceHandleException):
    def __init__(self):
        super(ErrThirdComponentStartFailed, self).__init__(
            msg="failed to start third component", msg_show="启动第三方组件失败, 请稍后重试", status_code=400, error_code=20801)


class ErrK8sComponentNameExists(ServiceHandleException):
    def __init__(self):
        super(ErrK8sComponentNameExists, self).__init__(
            msg="k8s component name exists", msg_show="组件英文名已存在", status_code=400, error_code=20802)


# 20900 ~ 20999 => app upgrade
class ErrAppUpgradeRecordNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrAppUpgradeRecordNotFound, self).__init__(
            msg="app upgrade record not found", msg_show="找不到升级记录", status_code=404, error_code=20900)


class ErrAppSnapshotNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrAppSnapshotNotFound, self).__init__(
            msg="app snapshot not found", msg_show="找不到应用升级快照", status_code=404, error_code=20901)


class ErrAppSnapshotExists(ServiceHandleException):
    def __init__(self):
        super(ErrAppSnapshotExists, self).__init__(
            msg="app snapshot exists", msg_show="应用升级快照已存在", status_code=409, error_code=20902)


class ErrAppUpgradeDeployFailed(ServiceHandleException):
    def __init__(self, msg=""):
        super(ErrAppUpgradeDeployFailed, self).__init__(
            msg if msg else "failed to deploy the app, please retry later",
            msg_show="组件部署失败, 请稍后重试",
            status_code=400,
            error_code=20903)


class ErrComponentGroupNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrComponentGroupNotFound, self).__init__(
            "component group not found", msg_show="无法找到组件与应用市场应用的从属关系", status_code=404, error_code=20904)


class ErrLastRecordUnfinished(ServiceHandleException):
    def __init__(self):
        super(ErrLastRecordUnfinished, self).__init__(
            "the last record is unfinished", msg_show="上一个任务未完成", status_code=400, error_code=20905)


class ErrAppUpgradeRecordCanNotDeploy(ServiceHandleException):
    def __init__(self):
        super(ErrAppUpgradeRecordCanNotDeploy, self).__init__(
            "can not deploy the record", msg_show="无法重新部署该记录", status_code=400, error_code=20906)


class ErrAppUpgradeRecordCanNotRollback(ServiceHandleException):
    def __init__(self):
        super(ErrAppUpgradeRecordCanNotRollback, self).__init__(
            "can not rollback the record", msg_show="无法回滚该记录", status_code=400, error_code=20907)


class ErrAppUpgradeWrongStatus(ServiceHandleException):
    def __init__(self):
        super(ErrAppUpgradeWrongStatus, self).__init__(
            "the status of the upgrade record is not not_upgraded", msg_show="只能升级未升级的升级记录", status_code=400, error_code=20908)


# 21000 ~ 21099 => application
class ErrApplicationNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrApplicationNotFound, self).__init__(
            msg="application not found", msg_show="应用不存在", status_code=404, error_code=21000)


class ErrApplicationServiceNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrApplicationServiceNotFound, self).__init__(
            msg="application service not found", msg_show="应用服务不存在", status_code=404, error_code=21001)


class ErrServiceAddressNotFound(ServiceHandleException):
    def __init__(self):
        super(ErrServiceAddressNotFound, self).__init__(
            msg="service address not found", msg_show="服务地址不存在", status_code=404, error_code=21002)


class ErrK8sAppExists(ServiceHandleException):
    def __init__(self):
        super(ErrK8sAppExists, self).__init__(msg="k8s app exists", msg_show="应用英文名已存在", status_code=400, error_code=21003)


# 21100 ~ 21199 => common
class ErrQualifiedName(ServiceHandleException):
    def __init__(self, msg="err qualified name", msg_show="名称只能由小写字母、数字或“-”组成，并且必须以字母数字开头和结尾"):
        super(ErrQualifiedName, self).__init__(msg=msg, msg_show=msg_show, status_code=400, error_code=21100)
