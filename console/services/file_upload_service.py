# -*- coding: utf8 -*-
"""
  Created on 18/3/13.
"""
import oss2
from goodrain_web.custom_config import custom_config as custom_settings
from django.conf import settings
import logging
from www.apiclient.baseclient import client_auth_service
from www.utils.crypt import make_uuid
import requests
from addict import Dict
import json
import os

logger = logging.getLogger("default")


class FileUploadService(object):

    def upload_file(self, upload_file, suffix):
        is_upload_to_oss = self.is_upload_to_oss()
        if is_upload_to_oss:
            file_url = self.upload_file_to_oss(upload_file, suffix)
        else:
            file_url = self.upload_file_to_local(upload_file, suffix)
        return file_url

    def app_market_upload(self, tenant_id, upload_file):

        url, market_client_id, market_client_token = client_auth_service.get_market_access_token_by_tenant(tenant_id)
        url += "/openapi/console/v1/files/upload"
        files = {'file': upload_file}
        headers = {"X_ENTERPRISE_ID": market_client_id,
                   "X_ENTERPRISE_TOKEN": market_client_token}
        resp = requests.post(url, files=files, headers=headers, verify=False)
        result = Dict(json.loads(resp.content))
        return result.data.bean.path

    def upload_file_to_oss(self, upload_file, suffix):
        filename = 'console/file/{0}.{1}'.format(make_uuid(), suffix)
        ret = None
        bucket = None
        try:
            bucket = self.get_bucket()
            ret = bucket.put_object(filename, upload_file.read())
        except Exception as e:
            logger.exception(e)
        if not ret or ret.status != 200:
            logger.error("Upload file error!")
            return None
        if bucket:
            return "{0}/{1}".format(bucket.endpoint, filename)

    def __get_oss_config(self):
        configs = custom_settings.configs()
        oss_conf = configs.get("OSS_CONFIG", None)
        if not oss_conf:
            return settings.OSS_CONFIG
        return oss_conf

    def get_bucket(self):
        oss_conf = self.__get_oss_config()

        auth = oss2.Auth(oss_conf["OSS_ACCESS_KEY"], oss_conf["OSS_ACCESS_KEY_SECRET"])
        bucket = oss2.Bucket(
            auth, oss_conf["OSS_ENDPOINT"], oss_conf["OSS_BUCKET"], is_cname=True)
        return bucket

    def is_upload_to_oss(self):
        return settings.MODULES.get('SSO_LOGIN')

    def upload_file_to_local(self, upload_file, suffix):
        try:
            prefix_file_path = '{0}/uploads'.format(settings.MEDIA_ROOT)

            if not os.path.exists(prefix_file_path):
                os.makedirs(prefix_file_path, 0777)
        except Exception as e:
            logger.exception(e)

        filename = '{0}/uploads/{1}.{2}'.format(settings.MEDIA_ROOT,
                                                make_uuid(), suffix)
        with open(filename, 'wb+') as destination:
            for chunk in upload_file.chunks():
                destination.write(chunk)
            return filename

upload_service = FileUploadService()