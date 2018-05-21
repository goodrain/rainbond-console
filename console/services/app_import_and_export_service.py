# -*- coding: utf8 -*-
"""
  Created on 18/5/15.
"""
import datetime
import json
import logging
import urllib2

import requests

from console.repositories.group import group_repo
from console.repositories.market_app_repo import app_export_record_repo
from console.repositories.region_repo import region_repo
from console.services.app_config.app_relation_service import AppServiceRelationService
from www.apiclient.baseclient import client_auth_service
from www.apiclient.marketclient import MarketOpenAPI
from www.apiclient.regionapi import RegionInvokeApi
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")
baseService = BaseTenantService()
app_relation_service = AppServiceRelationService()
market_api = MarketOpenAPI()
region_api = RegionInvokeApi()


class AppExportService(object):
    def create_export_repo(self, event_id, export_format, group_key, version):
        export_record = app_export_record_repo.get_export_record_by_unique_key(group_key, version, export_format)
        if export_record:
            return 409, "已存在改导出类型的文件", None

        if event_id is None:
            event_id = make_uuid()
        params = {
            "event_id": event_id,
            "group_key": group_key,
            "version": version,
            "format": export_format,
            "status": "exporting"
        }
        new_export_record = app_export_record_repo.create_app_export_record(**params)
        return 200, "success", new_export_record

    def export_current_app(self, team, export_format, app):
        event_id = make_uuid()
        data = {"event_id": event_id, "group_key": app.group_key, "version": app.version, "format": export_format,
                "group_metadata": app.app_template}
        region = self.get_app_share_region(app)
        if region is None:
            return 404, '无法查找当前应用分享所在数据中心', None
        region_api.export_app(region, team.tenant_name, data)
        export_record = app_export_record_repo.get_export_record_by_unique_key(app.group_key, app.version,
                                                                               export_format)
        if export_record:
            logger.debug("update export record !")
            export_record.event_id = event_id
            export_record.status = "exporting"
            export_record.update_time = datetime.datetime.now()
            export_record.save()
            new_export_record = export_record
        else:
            logger.debug("create export record !")
            code, msg, new_export_record = self.create_export_repo(event_id, export_format, app.group_key, app.version)
            if code != 200:
                return code, msg, None
        return 200, "success", new_export_record

    def get_app_share_region(self, app):
        app_template = json.loads(app.app_template)
        apps = app_template["apps"]
        first_app = apps[0]
        if first_app:
            region = first_app.get("service_region", None)
        else:
            group = group_repo.get_group_by_id(app.tenant_service_group_id)
            if group:
                region = group.region_name
            else:
                return None
        
        if region:
            region_config = region_repo.get_region_by_region_name(region)
            if region_config:
                return region
            return None
        else:
            return None


    def get_export_status(self, team, app):
        app_export_records = app_export_record_repo.get_by_key_and_version(app.group_key, app.version)
        rainbond_app_init_data = {
            "is_export_before": False,
        }
        docker_compose_init_data = {
            "is_export_before": False,
        }

        region = self.get_app_share_region(app)
        if region is None:
            return 404, '无法查找当前应用分享所在数据中心', None
        if app_export_records:
            for export_record in app_export_records:
                if export_record.event_id and export_record.status == "exporting":
                    try:
                        res, body = region_api.get_app_export_status(region, team.tenant_name, export_record.event_id)
                        result_bean = body["bean"]
                        if result_bean["status"] in ("failed", "success"):
                            export_record.status = result_bean["status"]
                        export_record.file_path = result_bean["tar_file_href"]
                        export_record.save()
                    except Exception as e:
                        logger.exception(e)

                if export_record.format == "rainbond-app":
                    rainbond_app_init_data.update({
                        "is_export_before": True,
                        "status": export_record.status,
                        "file_path": self._wrapper_director_download_url(region, export_record.file_path.replace("/v2",""))
                    })
                if export_record.format == "docker-compose":
                    docker_compose_init_data.update({
                        "is_export_before": True,
                        "status": export_record.status,
                        "file_path": self._wrapper_director_download_url(region, export_record.file_path.replace("/v2",""))
                    })

        result = {"rainbond_app": rainbond_app_init_data, "docker_compose": docker_compose_init_data}
        return 200, "success", result

    def __get_down_url(self, region_name, raw_url):
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            return region.url + raw_url
        else:
            return raw_url

    def _wrapper_director_download_url(self, region_name, raw_url):
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            splits_texts = region.url.split(":")
            if len(splits_texts) > 2:
                index = region.url.index(":", 6)
                return region.url[:index] + ":6060" + raw_url
            else:
                return region.url + ":6060" + raw_url

    def get_export_record(self, export_format, app):
        return app_export_record_repo.get_export_record_by_unique_key(app.group_key, app.version,
                                                                      export_format)

    def get_export_record_status(self, app):
        records = app_export_record_repo.get_by_key_and_version(app.group_key, app.version)
        export_status = "other"
        # 有一个成功即成功，全部失败为失败，全部为导出中则显示导出中
        if not records:
            return "unexported"
        failed = True

        for record in records:
            if record.status == "success":
                return "success"
            if record.status != "failed":
                failed = False
        if failed:
            return "failed"
        else:
            return "exporting"

    def get_file_down_req(self, export_format, tenant_name, app):
        export_record = app_export_record_repo.get_export_record_by_unique_key(app.group_key, app.version,
                                                                               export_format)
        region = self.get_app_share_region(app)

        download_url = self.__get_down_url(region, export_record.file_path)
        file_name = export_record.file_path.split("/")[-1]
        url, token = client_auth_service.get_region_access_token_by_tenant(
            tenant_name, region)
        if not token:
            region_info = region_repo.get_region_by_region_name(region)
            if region_info:
                token = region_info.token

        req = urllib2.Request(download_url)
        if token:
            req.add_header("Authorization", "Token {}".format(token))

        return req, file_name


export_service = AppExportService()
