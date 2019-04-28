# -*- coding: utf-8 -*-
import json

from console.exception.main import RbdAppNotFound
from console.exception.main import RecordNotFound
from console.repositories.market_app_repo import rainbond_app_repo


class RbdCenterAppService(object):
    def get_version_app(self, eid, version, service_source):
        """
        Get the specified version of the rainbond center(market) application
        raise: RecordNotFound
        raise: RbdAppNotFound
        """
        rain_app = rainbond_app_repo.get_enterpirse_app_by_key_and_version(
            eid, service_source.group_key, version)
        if rain_app is None:
            raise RecordNotFound("Enterprice id: {0}; Group key: {1}; version: {2}; \
                RainbondCenterApp not found.".format(eid, service_source.group_key, version))

        apps_template = json.loads(rain_app.app_template)
        apps = apps_template.get("apps")

        def func(x):
            result = x.get("service_share_uuid", None) == service_source.service_share_uuid\
                or x.get("service_key", None) == service_source.service_share_uuid
            return result
        app = next(iter(filter(lambda x: func(x), apps)), None)
        if app is None:
            fmt = "Group key: {0}; version: {1}; service_share_uuid: {2}; Rainbond app not found."
            raise RbdAppNotFound(fmt.format(service_source.group_key,
                                            version,
                                            service_source.service_share_uuid))

        return app

    def get_service_key_by_service_id(self, tenant, service_source, version, service_id):
        """get service_key(service_share_uuid) according to service_id
        service_id: service_id corresponding to the app before sharing
        """
        app = self.get_version_app(tenant.enterprice_id, version, service_source)
        if not app:
            return ""
        service = next(iter(filter(lambda x: x["service_id"] == service_id, app)), None)
        if not service:
            return ""
        if service.get("service_share_uuid", None):
            return service["service_share_uuid"]
        if service.get("service_key", None):
            return service["service_key"]
        return ""


rbd_center_app_service = RbdCenterAppService()
