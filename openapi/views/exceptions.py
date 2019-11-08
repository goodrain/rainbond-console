# -*- coding: utf-8 -*-
from console.exception.main import ServiceHandleException

# 业务码
# 企业: 1xxx 团队2xxx 组件3xxx

ErrStillHasServices = ServiceHandleException(
    msg="the team still has service",
    msg_show="团队仍有组件, 无法删除",
    status_code=409,
    error_code=2001
)

ErrTeamNotFound = ServiceHandleException(
    msg="the team is not found",
    msg_show="团队不存在",
    status_code=404,
    error_code=2002
)
