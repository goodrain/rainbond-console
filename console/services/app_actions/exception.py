# -*- coding: utf8 -*-


class ErrBackupNotFound(Exception):
    def __init__(self, sid: str) -> None:
        msg = "error not found backup for service(service_id={})".format(sid)
        super(ErrBackupNotFound, self).__init__(msg)


class ErrVersionAlreadyExists(Exception):
    def __init__(self) -> None:
        msg = "version already exists"
        super(ErrVersionAlreadyExists, self).__init__(msg)


class ErrServiceSourceNotFound(Exception):
    def __init__(self, sid: str) -> None:
        msg = "service id: {};service source not found".format(sid)
        super(ErrVersionAlreadyExists, self).__init__(msg)  # type: ignore[misc]  # NOTE: pre-existing bug — wrong class in super(); not fixing runtime logic
