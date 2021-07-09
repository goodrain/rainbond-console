# -*- coding: utf-8 -*-
import json

from console.exception.main import RbdAppNotFound
from console.exception.main import RecordNotFound
from console.repositories.market_app_repo import rainbond_app_repo


class RbdCenterAppService(object):
    def get_version_apps(self, eid, version, service_source):
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

    def get_version_app(self, eid, version, service_source):
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

        def func(x):
            result = x.get("service_share_uuid", None) == service_source.service_share_uuid\
                or x.get("service_key", None) == service_source.service_share_uuid
            return result

        app = next(iter([x for x in apps if func(x)]), None)
        if app is None:
            fmt = "Group key: {0}; version: {1}; service_share_uuid: {2}; Rainbond app not found."
            raise RbdAppNotFound(fmt.format(service_source.group_key, version, service_source.service_share_uuid))

        return app

    def get_plugins(self, eid, version, service_source):
        rain_app = rainbond_app_repo.get_enterpirse_app_by_key_and_version(eid, service_source.group_key, version)
        if rain_app is None:
            raise RecordNotFound("Enterprice id: {0}; Group key: {1}; version: {2}; \
                RainbondCenterApp not found.".format(eid, service_source.group_key, version))
        apps_template = json.loads(rain_app.app_template)
        return apps_template.get("plugins", [])


rbd_center_app_service = RbdCenterAppService()
