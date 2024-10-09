"""
该文件主要是对管理端构建语言版本的操作，包括创建、更新、删除、展示等操作。
"""
import re

from console.repositories.app_config import compile_env_repo

from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class RegionLongVersion(object):
    def show_long_version(self, eid, region_id, language):
        return region_api.get_lang_version(eid, region_id, language,"")

    def create_long_version(self, eid, region_id, lang, version, event_id, file_name):
        data = {
            "lang": lang,
            "version": version,
            "event_id": event_id,
            "file_name": file_name,
            "show": True,
        }
        return region_api.create_lang_version(eid, region_id, data)

    def update_long_version(self, eid, region_id, lang, version, show,first_choice):
        data = {
            "lang": lang,
            "version": version,
            "show": show,
            "first_choice":first_choice
        }
        region_api.update_lang_version(eid, region_id, data)

    def delete_long_version(self, eid, region_id, lang, version):
        data = {
            "lang": lang,
            "version": version,
        }
        use_components = compile_env_repo.get_lang_version_in_use(lang, version)
        if use_components:
            return use_components
        region_api.delete_lang_version(eid, region_id, data)
        return ""

    def is_valid_version(self, version_str):
        pattern = r'^[a-z0-9]+([-\.][0-9a-zA-Z]+)*$'
        if len(version_str) > 64:
            return False
        return bool(re.match(pattern, version_str))

    def is_valid_image(self, image_name):
        pattern = r'^[a-z0-9]+([._-][a-z0-9]+)*(\/[a-z0-9]+([._-][a-z0-9]+)*)*(\:[a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*)?$'
        return bool(re.match(pattern, image_name))


region_lang_version = RegionLongVersion()
