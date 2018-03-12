# -*- coding: utf8 -*-
"""
  Created on 18/1/24.
"""
from .app_log import AppEventService, AppLogService, AppWebSocketService
from .app_manage import AppManageService

event_service = AppEventService()
app_manage_service = AppManageService()
log_service = AppLogService()
ws_service = AppWebSocketService()