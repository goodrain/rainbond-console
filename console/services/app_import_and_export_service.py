# -*- coding: utf8 -*-
"""
  Created on 18/5/15.
"""
import base64
import json
import logging
import urllib2

from console.appstore.appstore import app_store
from console.models.main import RainbondCenterApp, RainbondCenterAppVersion
from console.repositories.market_app_repo import app_export_record_repo
from console.repositories.market_app_repo import app_import_record_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.region_repo import region_repo
from console.services.app_config.app_relation_service import AppServiceRelationService
from www.apiclient.baseclient import client_auth_service
from www.apiclient.regionapi import RegionInvokeApi
from www.tenantservice.baseservice import BaseTenantService
from www.utils.crypt import make_uuid
from console.exception.main import RegionNotFound, RecordNotFound
from console.exception.main import ExportAppError
from console.exception.main import RbdAppNotFound
from www.models.main import TenantRegionInfo

logger = logging.getLogger("default")
baseService = BaseTenantService()
app_relation_service = AppServiceRelationService()
region_api = RegionInvokeApi()


class AppExportService(object):
    def create_export_repo(self, event_id, export_format, group_key, version, enterprise_id):
        export_record = app_export_record_repo.get_enter_export_record_by_unique_key(enterprise_id, group_key, version,
                                                                                     export_format)
        if export_record:
            return 409, "已存在该导出类型的文件", None

        if event_id is None:
            event_id = make_uuid()
        params = {
            "event_id": event_id,
            "group_key": group_key,
            "version": version,
            "format": export_format,
            "status": "exporting",
            "enterprise_id": enterprise_id
        }
        new_export_record = app_export_record_repo.create_app_export_record(**params)
        return 200, "success", new_export_record

    def _export_app_region(self, eid):
        tenant_region_info = region_repo.get_region_by_enterprise_id(eid)
        if tenant_region_info:
            return tenant_region_info.region_name
        raise RecordNotFound("数据中心未找到")

    def export_app(self, eid, app_id, version, export_format):
        app, app_version = rainbond_app_repo.get_rainbond_app_and_version(eid, app_id, version)
        if not app or not app_version:
            raise RbdAppNotFound("未找到该应用")

        # get region
        region = self._export_app_region(eid)

        export_record = app_export_record_repo.get_export_record(eid, app_id, version, export_format)
        if export_record:
            if export_record.status == "success":
                raise ExportAppError(msg="exported", mes_show="已存在该导出记录", status_code=409)
            if export_record.status == "exporting":
                logger.debug("export record exists: event_id :{0}".format(export_record.event_id))
                return export_record
        # did not export, make a new export record
        # make export data
        event_id = make_uuid()
        data = {
            "event_id": event_id,
            "group_key": app.app_id,
            "version": app_version.version,
            "format": export_format,
            "group_metadata": self.__get_app_metata(app, app_version)
        }

        try:
            region_api.export_app(region, eid, data)
        except region_api.CallApiError as e:
            logger.exception(e)
            raise ExportAppError()

        params = {
            "event_id": event_id,
            "group_key": app_id,
            "version": version,
            "format": export_format,
            "status": "exporting",
            "enterprise_id": eid,
        }

        return app_export_record_repo.create_app_export_record(**params)

    def __get_app_metata(self, app, app_version):
        picture_path = app.pic
        suffix = picture_path.split('.')[-1]
        describe = app.describe
        try:
            image_base64_string = self.encode_image(picture_path)
        except IOError as e:
            logger.warning("path: {}; error encoding image: {}".format(picture_path, e))
            image_base64_string = ""

        app_template = json.loads(app_version.app_template)
        app_template["suffix"] = suffix
        app_template["describe"] = describe
        app_template["image_base64_string"] = image_base64_string
        return json.dumps(app_template)

    def encode_image(self, image_url):
        if not image_url:
            return None
        if image_url.startswith("http"):
            response = urllib2.urlopen(image_url)
        else:
            response = open(image_url)
        image_base64_string = base64.encodestring(response.read())
        response.close()
        return image_base64_string

    def get_app_share_region(self, app, app_version):
        import_record_id = app_version.record_id
        import_record = app_import_record_repo.get_import_record(import_record_id)
        if not import_record:
            return None
        return import_record.region

    def get_export_status(self, enterprise_id, app, app_version):
        app_export_records = app_export_record_repo.get_enter_export_record_by_key_and_version(
            enterprise_id, app.app_id, app_version.version)
        rainbond_app_init_data = {
            "is_export_before": False,
        }
        docker_compose_init_data = {
            "is_export_before": False,
        }

        # get region
        region = self._export_app_region(enterprise_id)

        if app_export_records:
            for export_record in app_export_records:
                if export_record.event_id and export_record.status == "exporting":
                    try:
                        res, body = region_api.get_app_export_status(region, enterprise_id, export_record.event_id)
                        result_bean = body["bean"]
                        if result_bean["status"] in ("failed", "success"):
                            export_record.status = result_bean["status"]
                        export_record.file_path = result_bean["tar_file_href"]
                        export_record.save()
                    except Exception as e:
                        logger.exception(e)

                if export_record.format == "rainbond-app":
                    rainbond_app_init_data.update({
                        "is_export_before":
                        True,
                        "status":
                        export_record.status,
                        "file_path":
                        self._wrapper_director_download_url(region, export_record.file_path.replace("/v2", ""))
                    })
                if export_record.format == "docker-compose":
                    docker_compose_init_data.update({
                        "is_export_before":
                        True,
                        "status":
                        export_record.status,
                        "file_path":
                        self._wrapper_director_download_url(region, export_record.file_path.replace("/v2", ""))
                    })

        result = {"rainbond_app": rainbond_app_init_data, "docker_compose": docker_compose_init_data}
        return result

    def __get_down_url(self, region_name, raw_url):
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            return region.url + raw_url
        else:
            return raw_url

    def _wrapper_director_download_url(self, region_name, raw_url):
        region = region_repo.get_region_by_region_name(region_name)
        if region:
            splits_texts = region.wsurl.split("://")
            if splits_texts[0] == "wss":
                return "https://" + splits_texts[1] + raw_url
            else:
                return "http://" + splits_texts[1] + raw_url

            # if len(splits_texts) > 2:
            #     temp_url = splits_texts[0] + "://" + region.tcpdomain
            #     return temp_url + ":6060" + raw_url
            # else:
            #     return "http://" + region.tcpdomain + ":6060" + raw_url

    def get_export_record(self, export_format, app):
        return app_export_record_repo.get_export_record_by_unique_key(app.group_key, app.version, export_format)

    def get_export_record_status(self, enterprise_id, group_key, version):
        records = app_export_record_repo.get_enter_export_record_by_key_and_version(enterprise_id, group_key, version)
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
        export_record = app_export_record_repo.get_export_record_by_unique_key(app.group_key, app.version, export_format)
        # TODO fix get region bugs, this func need app and version two parameters
        region = self.get_app_share_region(app)

        download_url = self.__get_down_url(region, export_record.file_path)
        file_name = export_record.file_path.split("/")[-1]
        url, token = client_auth_service.get_region_access_token_by_tenant(tenant_name, region)
        if not token:
            region_info = region_repo.get_region_by_region_name(region)
            if region_info:
                token = region_info.token

        req = urllib2.Request(download_url)
        if token:
            if token.startswith("Token"):
                req.add_header("Authorization", "{}".format(token))
            else:
                req.add_header("Authorization", "Token {}".format(token))

        return req, file_name


class AppImportService(object):
    def start_import_apps(self, scope, event_id, file_names, team_name=None, enterprise_id=None):
        import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
        if not import_record:
            raise RecordNotFound("import_record not found")
        import_record.scope = scope
        if team_name:
            import_record.team_name = team_name

        service_image = app_store.get_app_hub_info(enterprise_id=enterprise_id)
        data = {"service_image": service_image, "event_id": event_id, "apps": file_names}
        if scope == "enterprise":
            region_api.import_app_2_enterprise(import_record.region, import_record.enterprise_id, data)
        else:
            res, body = region_api.import_app(import_record.region, team_name, data)
        import_record.status = "importing"
        import_record.save()

    def get_and_update_import_by_event_id(self, event_id):
        import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
        if not import_record:
            raise RecordNotFound("import_record not found")
        # get import status from region
        res, body = region_api.get_enterprise_app_import_status(import_record.region, import_record.enterprise_id, event_id)
        status = body["bean"]["status"]
        if import_record.status != "success":
            if status == "success":
                logger.debug("app import success !")
                self.__save_enterprise_import_info(import_record, body["bean"]["metadata"])
                import_record.source_dir = body["bean"]["source_dir"]
                import_record.format = body["bean"]["format"]
                import_record.status = "success"
                import_record.save()
                # 成功以后删除数据中心目录数据
                try:
                    region_api.delete_enterprise_import_file_dir(import_record.region, import_record.enterprise_id, event_id)
                except Exception as e:
                    logger.exception(e)
            else:
                import_record.status = status
                import_record.save()
        apps_status = self.__wrapp_app_import_status(body["bean"]["apps"])

        failed_num = 0
        success_num = 0
        for i in apps_status:
            if i.get("status") == "success":
                success_num += 1
                import_record.status = "partial_success"
                import_record.save()
            elif i.get("status") == "failed":
                failed_num += 1
        if success_num == len(apps_status):
            import_record.status = "success"
            import_record.save()
        elif failed_num == len(apps_status):
            import_record.status = "failed"
            import_record.save()
        if status == "uploading":
            import_record.status = status
            import_record.save()

        return import_record, apps_status

    def get_and_update_import_status(self, tenant, region, event_id):
        """获取并更新导入状态"""
        import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
        if not import_record:
            raise RecordNotFound("import_record not found")
        # 去数据中心请求导入状态
        res, body = region_api.get_app_import_status(region, tenant.tenant_name, event_id)
        status = body["bean"]["status"]
        if import_record.status != "success":
            if status == "success":
                logger.debug("app import success !")
                self.__save_import_info(tenant, import_record.scope, body["bean"]["metadata"])
                import_record.source_dir = body["bean"]["source_dir"]
                import_record.format = body["bean"]["format"]
                import_record.status = "success"
                import_record.save()
                # 成功以后删除数据中心目录数据
                try:
                    region_api.delete_import_file_dir(region, tenant.tenant_name, event_id)
                except Exception as e:
                    logger.exception(e)
            else:
                import_record.status = status
                import_record.save()
        apps_status = self.__wrapp_app_import_status(body["bean"]["apps"])

        failed_num = 0
        success_num = 0
        for i in apps_status:
            if i.get("status") == "success":
                success_num += 1
                import_record.status = "partial_success"
                import_record.save()
            elif i.get("status") == "failed":
                failed_num += 1
        if success_num == len(apps_status):
            import_record.status = "success"
            import_record.save()
        elif failed_num == len(apps_status):
            import_record.status = "failed"
            import_record.save()
        if status == "uploading":
            import_record.status = status
            import_record.save()

        return import_record, apps_status

    def __wrapp_app_import_status(self, app_status):
        """
        wrapper struct "app1:success,app2:failed" to
        [{"file_name":"app1","status":"success"},{"file_name":"app2","status":"failed"} ]
        """
        status_list = []
        if not app_status:
            return status_list
        k_v_map_list = app_status.split(",")
        for value in k_v_map_list:
            kv_map_list = value.split(":")
            status_list.append({"file_name": kv_map_list[0], "status": kv_map_list[1]})
        return status_list

    def get_import_app_dir(self, event_id):
        """获取应用目录下的包"""
        import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
        if not import_record:
            raise RecordNotFound("import_record not found")
        res, body = region_api.get_enterprise_import_file_dir(import_record.region, import_record.enterprise_id, event_id)
        app_tars = body["bean"]["apps"]
        return app_tars

    def create_import_app_dir(self, tenant, user, region):
        """创建一个应用包"""
        event_id = make_uuid()
        res, body = region_api.create_import_file_dir(region, tenant.tenant_name, event_id)
        path = body["bean"]["path"]
        import_record_params = {
            "event_id": event_id,
            "status": "created_dir",
            "source_dir": path,
            "team_name": tenant.tenant_name,
            "region": region,
            "user_name": user.get_name()
        }
        import_record = app_import_record_repo.create_app_import_record(**import_record_params)
        return import_record

    def delete_import_app_dir_by_event_id(self, event_id):
        try:
            import_record = app_import_record_repo.get_import_record_by_event_id(event_id)
            region_api.delete_enterprise_import(import_record.region, import_record.enterprise_id, event_id)
        except Exception as e:
            logger.exception(e)

        app_import_record_repo.delete_by_event_id(event_id)

    def delete_import_app_dir(self, tenant, region, event_id):
        try:
            region_api.delete_import(region, tenant.tenant_name, event_id)
        except Exception as e:
            logger.exception(e)

        app_import_record_repo.delete_by_event_id(event_id)

    def __save_enterprise_import_info(self, import_record, metadata):
        rainbond_apps = []
        rainbond_app_versions = []
        metadata = json.loads(metadata)
        key_and_version_list = []
        for app_template in metadata:
            app = rainbond_app_repo.get_rainbond_app_by_app_id(import_record.enterprise_id, app_template["group_key"])
            # if app exists, update it
            if app:
                app.scope = import_record.scope
                app.describe = app_template.pop("describe", "")
                app.save()
                app_version = rainbond_app_repo.get_rainbond_app_version_by_app_id_and_version(
                    app.app_id, app_template["group_version"])
                if app_version:
                    app_version.scope = import_record.scope
                    app_version.app_template = json.dumps(app_template)
                    app_version.template_version = app_template["template_version"]
                    app_version.save()
                continue
            image_base64_string = app_template.pop("image_base64_string", "")
            pic_url = ""
            if image_base64_string:
                pic_url = self.decode_image(image_base64_string, app_template.pop("suffix", "jpg"))

            key_and_version = "{0}:{1}".format(app_template["group_key"], app_template['group_version'])
            if key_and_version in key_and_version_list:
                continue
            key_and_version_list.append(key_and_version)
            rainbond_app = RainbondCenterApp(
                enterprise_id=import_record.enterprise_id,
                app_id=app_template["group_key"],
                app_name=app_template["group_name"],
                source="import",
                create_team=import_record.team_name,
                scope=import_record.scope,
                describe=app_template.pop("describe", ""),
                pic=pic_url,
            )
            rainbond_apps.append(rainbond_app)
            rainbond_app_version = RainbondCenterAppVersion(
                scope=rainbond_app.scope,
                enterprise_id=rainbond_app.enterprise_id,
                app_id=rainbond_app.app_id,
                app_template=json.dumps(app_template),
                version=app_template["group_version"],
                template_version=app_template["template_version"],
                record_id=import_record.ID,
                share_user=0,
                is_complete=1,
            )
            rainbond_app_versions.append(rainbond_app_version)
        rainbond_app_repo.bulk_create_rainbond_app_versions(rainbond_app_versions)
        rainbond_app_repo.bulk_create_rainbond_apps(rainbond_apps)

    def __save_import_info(self, tenant, scope, metadata):
        rainbond_apps = []
        metadata = json.loads(metadata)
        key_and_version_list = []
        for app_template in metadata:
            app = rainbond_app_repo.get_rainbond_app_by_key_and_version_eid(tenant.enterprise_id, app_template["group_key"],
                                                                            app_template["group_version"])
            if app:
                # 覆盖原有应用数据
                app.share_team = tenant.tenant_name  # 分享团队名暂时为那个团队将应用导入进来的
                app.scope = scope
                app.describe = app_template.pop("describe", "")
                app.app_template = json.dumps(app_template)
                app.template_version = app_template.get("template_version", "")
                app.is_complete = True
                app.save()
                continue
            image_base64_string = app_template.pop("image_base64_string", "")
            pic_url = ""
            if image_base64_string:
                pic_url = self.decode_image(image_base64_string, app_template.pop("suffix", "jpg"))

            key_and_version = "{0}:{1}".format(app_template["group_key"], app_template['group_version'])
            if key_and_version in key_and_version_list:
                continue
            key_and_version_list.append(key_and_version)
            rainbond_app = RainbondCenterApp(
                enterprise_id=tenant.enterprise_id,
                group_key=app_template["group_key"],
                group_name=app_template["group_name"],
                version=app_template['group_version'],
                share_user=0,
                record_id=0,
                share_team=tenant.tenant_name,
                source="import",
                scope=scope,
                describe=app_template.pop("describe", ""),
                pic=pic_url,
                app_template=json.dumps(app_template),
                is_complete=True,
                template_version=app_template.get("template_version", ""))
            rainbond_apps.append(rainbond_app)
        rainbond_app_repo.bulk_create_rainbond_apps(rainbond_apps)

    def decode_image(self, image_base64_string, suffix):
        if not image_base64_string:
            return ""
        try:
            file_name = make_uuid() + "." + suffix
            file_path = "{0}/{1}".format("/data/media/uploads", file_name)
            with open(file_path, "wb") as f:
                f.write(image_base64_string.decode("base64"))
            return file_path
        except Exception as e:
            logger.exception(e)
        return ""

    def get_importing_apps(self, tenant, user, region):
        importing_records = app_import_record_repo.get_importing_record(tenant.tenant_name, user.nick_name)
        importing_list = []
        for importing_record in importing_records:
            import_record, apps_status = self.get_and_update_import_status(tenant, region, importing_record.event_id)
            if import_record.status not in ("success", "failed"):
                importing_list.append(apps_status)
        return importing_list

    def get_user_not_finish_import_record_in_enterprise(self, eid, user):
        return app_import_record_repo.get_user_not_finished_import_record_in_enterprise(eid, user.nick_name)

    def get_user_unfinished_import_record(self, tenant, user):
        return app_import_record_repo.get_user_unfinished_import_record(tenant.tenant_name, user.nick_name)

    def create_app_import_record(self, team_name, user_name, region):
        event_id = make_uuid()
        import_record_params = {
            "event_id": event_id,
            "status": "uploading",
            "team_name": team_name,
            "region": region,
            "user_name": user_name
        }
        return app_import_record_repo.create_app_import_record(**import_record_params)

    def create_app_import_record_2_enterprise(self, eid, user_name):
        event_id = make_uuid()
        try:
            region = region_repo.get_region_by_enterprise_id(eid)
        except TenantRegionInfo.DoesNotExist:
            raise RegionNotFound("region not found")
        if not region:
            raise RegionNotFound("region not found")
        import_record_params = {
            "event_id": event_id,
            "status": "uploading",
            "enterprise_id": eid,
            "region": region.region_name,
            "user_name": user_name
        }
        return app_import_record_repo.create_app_import_record(**import_record_params)

    def get_upload_url(self, region, event_id):
        region = region_repo.get_region_by_region_name(region)
        raw_url = "/app/upload"
        upload_url = ""
        if region:
            splits_texts = region.wsurl.split("://")
            if splits_texts[0] == "wss":
                upload_url = "https://" + splits_texts[1] + raw_url
            else:
                upload_url = "http://" + splits_texts[1] + raw_url
        return upload_url + "/" + event_id

        # if region:
        #     splits_texts = region.url.split(":")
        #     if len(splits_texts) > 2:
        #         temp_url = splits_texts[0] + "://" + region.tcpdomain
        #         upload_url = temp_url + ":6060" + raw_url
        #     else:
        #         upload_url = "http://" + region.tcpdomain + ":6060" + raw_url
        # return upload_url


export_service = AppExportService()
import_service = AppImportService()
