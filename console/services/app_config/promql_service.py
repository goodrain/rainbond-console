# -*- coding: utf8 -*-
import subprocess
import platform
import os
import logging

from goodrain_web.settings import BASE_DIR
from console.exception.main import AbortRequest

logger = logging.getLogger("default")


class PromQLService(object):
    @staticmethod
    def add_or_update_label(component_id, promql):
        """
        Add service_id label, or replace illegal service_id label
        """
        promql_parser = BASE_DIR + "/bin/" + platform.system().lower() + "/promql-parser"
        c = subprocess.Popen([os.getenv("PROMQL_PARSER", promql_parser), "--promql", promql, "--component_id", component_id],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        new_promql, err = c.communicate()
        if err != "":
            logger.warning("ensure service id for promql({}): {}".format(promql, err))
            raise AbortRequest("invalid promql", "非法的 prometheus 查询语句")

        return new_promql


promql_service = PromQLService()
