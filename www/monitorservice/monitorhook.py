# -*- coding: utf8 -*-
import datetime
import json

import logging

logger = logging.getLogger('default')


class MonitorHook(object):
    def registerMonitor(self, user, action):
        data = dict()
        data["operator"] = user.nick_name
        data["origin"] = "goodrain_web"
        data["target_id"] = user.user_id
        data["target_name"] = user.nick_name
        data["category"] = "user"
        data["action"] = action
        data["info"] = ""
        data["result"] = "success"
        data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug('monitor.hook', json.dumps(data))

    def tenantMonitor(self, tenant, user, action, init_result):
        data = dict()
        data["operator"] = user.nick_name
        data["origin"] = "goodrain_web"
        data["target_id"] = tenant.tenant_id
        data["target_name"] = tenant.tenant_name
        data["category"] = "tenant"
        data["action"] = action
        data["info"] = ""
        if init_result:
            data["result"] = "success"
        else:
            data["result"] = "failure"
        data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug('monitor.hook', json.dumps(data))

    def gitUserMonitor(self, user, git_user_id):
        data = dict()
        data["operator"] = user.nick_name
        data["origin"] = "goodrain_web"
        data["target_id"] = user.user_id
        data["target_name"] = user.nick_name
        data["category"] = "user"
        data["action"] = "create_git_user"
        data["info"] = ""
        if git_user_id > 0:
            data["result"] = "success"
        else:
            data["result"] = "failure"
        data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug('monitor.hook', json.dumps(data))

    def phoneCodeMonitor(self, phone, phone_code, send_result):
        data = dict()
        data["operator"] = "system"
        data["origin"] = "goodrain_web"
        data["target_id"] = phone
        data["target_name"] = phone
        data["category"] = "user"
        data["action"] = "sms_code"
        data["info"] = phone_code
        if send_result:
            data["result"] = "success"
        else:
            data["result"] = "failure"
        data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug('monitor.hook', json.dumps(data))

    def loginMonitor(self, user):
        data = dict()
        data["operator"] = user.nick_name
        data["origin"] = "goodrain_web"
        data["target_id"] = user.user_id
        data["target_name"] = user.nick_name
        data["category"] = "user"
        data["action"] = "login"
        data["info"] = ""
        data["result"] = "success"
        data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug('monitor.hook', json.dumps(data))

    def logoutMonitor(self, user):
        data = dict()
        data["operator"] = user.nick_name
        data["origin"] = "goodrain_web"
        data["target_id"] = user.user_id
        data["target_name"] = user.nick_name
        data["category"] = "user"
        data["action"] = "logout"
        data["info"] = ""
        data["result"] = "success"
        data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug('monitor.hook', json.dumps(data))

    def passwdResetMonitor(self, user, flag):
        data = dict()
        data["operator"] = user.nick_name
        data["origin"] = "goodrain_web"
        data["target_id"] = user.user_id
        data["target_name"] = user.nick_name
        data["category"] = "user"
        data["action"] = "passwd"
        data["info"] = ""
        if flag:
            data["result"] = "success"
        else:
            data["result"] = "failure"
        data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug('monitor.hook', json.dumps(data))

    def serviceMonitor(self, nick_name, tenantService, action, result, origin=None, info=""):
        data = dict()
        data["operator"] = nick_name
        if origin is None:
            origin = "goodrain_web"
        data["origin"] = origin
        data["target_id"] = tenantService.service_id
        data["target_name"] = tenantService.service_alias
        data["category"] = "service"
        data["action"] = action
        data["info"] = info
        if result:
            data["result"] = "success"
        else:
            data["result"] = "failure"
        data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug('monitor.hook', json.dumps(data))

    def gitProjectMonitor(self, nick_name, tenantService, action, project_id):
        data = dict()
        data["operator"] = nick_name
        data["origin"] = "goodrain_web"
        data["target_id"] = tenantService.service_id
        data["target_name"] = tenantService.service_alias
        data["category"] = "service"
        data["action"] = action
        data["info"] = ""
        if project_id > 0:
            data["result"] = "success"
        else:
            data["result"] = "failure"
        data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.debug('monitor.hook', json.dumps(data))

    def rechargeMonitor(self, nick_name, user_id, action):
        try:
            data = dict()
            data["operator"] = nick_name
            data["origin"] = "goodrain_web"
            data["target_id"] = user_id
            data["target_name"] = nick_name
            data["category"] = "user"
            data["action"] = action
            data["info"] = ""
            data["result"] = "success"
            data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.debug('monitor.hook', json.dumps(data))
        except Exception as e:
            logger.exception(e.message)
            pass

    def buyPayModelMonitor(self, tenant, user, action):
        try:
            data = dict()
            data["operator"] = user.nick_name
            data["origin"] = "goodrain_web"
            data["target_id"] = tenant.tenant_id
            data["target_name"] = tenant.tenant_name
            data["category"] = "tenant"
            data["action"] = action
            data["info"] = ""
            data["result"] = "success"
            data["create_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.debug('monitor.hook', json.dumps(data))
        except Exception as e:
            logger.exception(e.message)
            pass
