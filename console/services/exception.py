# -*- coding: utf8 -*-


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


class ErrNoObjectStorageInfo(Exception):
    def __init__(self):
        msg = "no object storage info"
        super(ErrNoObjectStorageInfo, self).__init__(msg)


class ErrBackupRecordNotFound(Exception):
    def __init__(self):
        msg = "backup record not found"
        super(ErrNoObjectStorageInfo, self).__init__(msg)


class ErrNeedAllServiceCloesed(Exception):
    def __init__(self):
        msg = "restore the backup, please make sure that all services are all closed."
        super(ErrNoObjectStorageInfo, self).__init__(msg)
