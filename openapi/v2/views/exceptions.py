# -*- coding: utf-8 -*-
from console.exception.main import ServiceHandleException

# 业务码
# 企业: 1xxx 团队2xxx 组件3xxx

ErrTeamNotFound = ServiceHandleException(msg="the team is not found", msg_show="团队不存在", status_code=404, error_code=2002)
