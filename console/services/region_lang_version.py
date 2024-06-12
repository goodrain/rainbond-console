from console.repositories.app_config import compile_env_repo

from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()


class RegionLongVersion(object):
    def show_long_version(self, eid, region_id, language):
        return region_api.get_lang_version(eid, region_id, language)

    def create_long_version(self, eid, region_id, lang, version, event_id, file_name):
        data = {
            "lang": lang,
            "version": version,
            "event_id": event_id,
            "file_name": file_name,
        }
        region_api.create_lang_version(eid, region_id, data)

    def update_long_version(self, eid, region_id, lang, version):
        data = {
            "lang": lang,
            "version": version,
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


region_lang_version = RegionLongVersion()
