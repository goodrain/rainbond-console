# -*- coding: utf8 -*-
"""
  Created on 18/3/13.
"""
import logging
import os

import oss2
from django.conf import settings

from goodrain_web.custom_config import custom_config as custom_settings
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class FileUploadService(object):
    def upload_file(self, upload_file, suffix):
        is_upload_to_oss = self.is_upload_to_oss()
        if is_upload_to_oss:
            file_url = self.upload_file_to_oss(upload_file, suffix)
        else:
            file_url = self.upload_file_to_local(upload_file, suffix)
        return file_url

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
        bucket = oss2.Bucket(auth, oss_conf["OSS_ENDPOINT"], oss_conf["OSS_BUCKET"], is_cname=True)
        return bucket

    def is_upload_to_oss(self):
        return settings.MODULES.get('SSO_LOGIN')

    def upload_file_to_local(self, upload_file, suffix):
        try:
            prefix_file_path = '{0}/uploads'.format(settings.MEDIA_ROOT)

            if not os.path.exists(prefix_file_path):
                os.makedirs(prefix_file_path, 0o777)
        except Exception as e:
            logger.exception(e)
        filename = 'uploads/{0}.{1}'.format(make_uuid(), suffix)
        savefilename = os.path.join(settings.MEDIA_ROOT, filename)
        queryfilename = os.path.join(settings.MEDIA_URL, filename)
        with open(savefilename, 'wb+') as destination:
            for chunk in upload_file.chunks():
                destination.write(chunk)
            return queryfilename


upload_service = FileUploadService()
