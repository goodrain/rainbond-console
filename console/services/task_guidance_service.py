# -*- coding: utf8 -*-
import logging

logger = logging.getLogger("default")


class BaseTaskStatusStrategy(object):
    """Abstract class: confirm the status of the base task"""

    def confirm_status(self):
        raise NotImplementedError("Doesn't provide a representation for BaseTaskStatus.")


class AppCreationStrategy(BaseTaskStatusStrategy):
    """Task: app creation"""

    def confirm_status(self):
        logger.debug("AppCreationStrategy")
        return True


class SourceCodeServiceCreationStrategy(BaseTaskStatusStrategy):
    """Task: create a service based on source code"""

    def confirm_status(self):
        logger.debug("SourceCodeServiceCreationStrategy")
        return False


class BaseTaskStatusContext(object):
    def __init__(self, task):
        self.has_error = False
        if task == 'app_create':
            self.strategy = AppCreationStrategy()
        elif task == 'source_code_service_create':
            self.strategy = SourceCodeServiceCreationStrategy()
        else:
            logger.warning("Task: {}; unsupported task", task)
            self.has_error = True

    def confirm_status(self):
        return self.strategy.confirm_status()

