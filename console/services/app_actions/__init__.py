# -*- coding: utf8 -*-
"""
  Created on 18/1/24.
"""
from console.services.app_actions.app_log import AppEventService
from console.services.app_actions.app_log import AppLogService
from console.services.app_actions.app_log import AppWebSocketService
from console.services.app_actions.app_manage import AppManageService

event_service = AppEventService()
app_manage_service = AppManageService()
log_service = AppLogService()
ws_service = AppWebSocketService()
