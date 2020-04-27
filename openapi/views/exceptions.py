# -*- coding: utf-8 -*-
from console.exception.main import ServiceHandleException
from rest_framework import serializers

# 业务码
# 企业: 1xxx 团队2xxx 组件3xxx

ErrTeamNotFound = ServiceHandleException(
    msg="the team is not found",
    msg_show="团队不存在",
    status_code=404,
    error_code=2000
)

ErrEnterpriseNotFound = ServiceHandleException(
    msg="the enterprise is not found",
    msg_show="用户所在企业不存在",
    status_code=404,
    error_code=1000
)

ErrRegionNotFound = serializers.ValidationError("指定数据中心不存在")
