# -*- coding: utf8 -*-
import json
import logging

from console.services.config_service import config_service
from console.services.task_guidance.base_task_status_service import BaseTaskStatusContext

logger = logging.getLogger("default")


class BaseTaskGuidance:
    def __init__(self):
        pass

    def list_base_tasks(self, eid):
        cfg = config_service.get_config_by_key(eid).value
        if not cfg:
            # init base tasks
            logger.info("Enterprise id: {}; initialize basic tasks information".format(eid))
            data = self.init_base_task()
            # TODO: handle error
            config_service.add_config_without_reload(key=eid, default_value=json.dumps(data), type="json")
        else:
            data = json.loads(cfg)
        need_update = False
        for index in range(len(data)):
            if data[index] is not None and data[index]["key"] == "install_mysql_from_market":
                del data[index]
                config_service.update_config(eid, json.dumps(data))
                break

        for item in data:
            if not item["status"]:
                ctx = BaseTaskStatusContext(eid, item["key"])
                status = ctx.confirm_status()
                if status:
                    logger.info("Enterprise id: {0}; Task: {1}; Original status: False; "
                                "update status.".format(eid, item["key"]))
                    item["status"] = status
                    need_update = True

        if need_update:
            # TODO: handle error
            config_service.update_config(eid, json.dumps(data))

        return data

    def init_base_task(self):
        data = [{
            "key": "app_create",
            "status": False
        }, {
            "key": "source_code_service_create",
            "status": False
        }, {
            "key": "service_connect_db",
            "status": False
        }, {
            "key": "share_app",
            "status": False
        }, {
            "key": "custom_gw_rule",
            "status": False
        }, {
            "key": "install_plugin",
            "status": False
        }, {
            "key": "image_service_create",
            "status": False
        }]
        return data
