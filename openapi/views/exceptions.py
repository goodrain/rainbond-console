# -*- coding: utf-8 -*-
from console.exception.main import ServiceHandleException

# 业务码
# 企业: 1xxx 团队2xxx 组件3xxx

ErrTeamNotFound = ServiceHandleException(msg="the team is not found", msg_show="团队不存在", status_code=404, error_code=2000)

ErrEnterpriseNotFound = ServiceHandleException(
    msg="the enterprise is not found", msg_show="用户所在企业不存在", status_code=404, error_code=1000)

ErrRegionNotFound = ServiceHandleException(msg="the region is not found", msg_show="集群不存在", status_code=404, error_code=3000)

ErrAppNotFound = ServiceHandleException(msg="the app is not found", msg_show="应用不存在", status_code=404, error_code=4000)
