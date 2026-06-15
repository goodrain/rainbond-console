# -*- coding: utf-8 -*-
import json
from typing import Any

from console.exception.main import RbdAppNotFound
from console.exception.main import RecordNotFound
from console.repositories.market_app_repo import rainbond_app_repo


class RbdCenterAppService(object):
    def get_version_apps(self, eid: str, version: str, service_source: Any) -> Any:
        """
        get rainbond center(market) application
        raise: RecordNotFound
        raise: RbdAppNotFound
        """
        rain_app = rainbond_app_repo.get_enterpirse_app_by_key_and_version(eid, service_source.group_key, version)
        if rain_app is None:
            raise RecordNotFound("Enterprice id: {0}; Group key: {1}; version: {2}; \
                RainbondCenterApp not found.".format(eid, service_source.group_key, version))

        apps_template = json.loads(rain_app.app_template)
        return apps_template.get("apps")

    def get_version_app(self, eid: str, version: str, service_source: Any) -> Any:
        """
        Get the specified version of the rainbond center(market) application
        raise: RecordNotFound
        raise: RbdAppNotFound
        """
        rain_app = rainbond_app_repo.get_enterpirse_app_by_key_and_version(eid, service_source.group_key, version)
        if rain_app is None:
            raise RecordNotFound("Enterprice id: {0}; Group key: {1}; version: {2}; \
                RainbondCenterApp not found.".format(eid, service_source.group_key, version))

        apps_template = json.loads(rain_app.app_template)
        apps = apps_template.get("apps")

        def func(x: Any) -> bool:
            result = x.get("service_share_uuid", None) == service_source.service_share_uuid\
                or x.get("service_key", None) == service_source.service_share_uuid
            return result

        app = next(iter([x for x in apps if func(x)]), None)
        if app is None:
            fmt = "Group key: {0}; version: {1}; service_share_uuid: {2}; Rainbond app not found."
            raise RbdAppNotFound(fmt.format(service_source.group_key, version, service_source.service_share_uuid))

        return app

    def get_plugins(self, eid: str, version: str, service_source: Any) -> Any:
        rain_app = rainbond_app_repo.get_enterpirse_app_by_key_and_version(eid, service_source.group_key, version)
        if rain_app is None:
            raise RecordNotFound("Enterprice id: {0}; Group key: {1}; version: {2}; \
                RainbondCenterApp not found.".format(eid, service_source.group_key, version))
        apps_template = json.loads(rain_app.app_template)
        return apps_template.get("plugins", [])


rbd_center_app_service = RbdCenterAppService()
