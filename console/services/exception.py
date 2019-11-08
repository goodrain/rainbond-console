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
    msg_show="该备份正在进行中",
    status_code=409,
)


ErrNeedAllServiceCloesed = ServiceHandleException(
    msg="restore the backup, please make sure that all services are all closed.",
    msg_show="请先关闭所有的组件",
)
