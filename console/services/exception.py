# -*- coding: utf8 -*-
from console.exception.main import ServiceHandleException


class ErrDepServiceNotFound(Exception):
    def __init__(self, sid=None):
        msg = "dep service not found"
        if sid:
            msg = "dep service not found(service_id={})".format(sid)
        super(ErrDepServiceNotFound, self).__init__(msg)


class ErrAdminUserDoesNotExist(Exception):
    def __init__(self, msg=""):
        super(ErrAdminUserDoesNotExist, self).__init__(msg)


class ErrCannotDelLastAdminUser(Exception):
    def __init__(self, msg=""):
        super(ErrCannotDelLastAdminUser, self).__init__(msg)


class ErrTenantRegionNotFound(Exception):
    def __init__(self):
        msg = "tenant region not found"
        super(ErrTenantRegionNotFound, self).__init__(msg)


ErrObjectStorageInfoNotFound = ServiceHandleException(
    msg="object storage info not found",
    msg_show="云端存储信息不存在",
    status_code=404,
)

ErrBackupRecordNotFound = ServiceHandleException(
    msg="backup not found",
    msg_show="备份不存在",
    status_code=404,
)

ErrBackupInProgress = ServiceHandleException(
    msg="backup in progress",
    msg_show="备份正在进行中",
    status_code=409,
)

ErrNeedAllServiceCloesed = ServiceHandleException(
    msg="restore the backup, please make sure that all services are all closed.",
    msg_show="请先关闭所有的组件",
)

ErrDuplicateMetrics = ServiceHandleException(
    msg="depulicate metrics",
    msg_show="重复的指标",
)

ErrAutoscalerRuleNotFound = ServiceHandleException(msg="autoscaler rule not found", msg_show="自动伸缩规程不存在", status_code=404)

ErrStillHasServices = ServiceHandleException(
    msg="the team still has service", msg_show="团队仍有组件, 无法删除", status_code=409, error_code=2001)

ErrAllTenantDeletionFailed = ServiceHandleException(
    msg="delete of all tenants failed", msg_show="所有租户的删除都失败了", status_code=400, error_code=400)

ErrVolumeTypeNotFound = ServiceHandleException(
    msg="volume type do not found", msg_show="存储类型不可用", status_code=400, error_code=400)

ErrVolumeTypeDoNotAllowMultiNode = ServiceHandleException(msg="volume type do not allow multi node", msg_show="存储类型不支持多个实例读写")
ErrChangeServiceType = ServiceHandleException(error_code=500, msg="change service type failed", msg_show="更新组件类型失败")
