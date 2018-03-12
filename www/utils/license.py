# -*- coding: utf8 -*-
from Crypto.Cipher import AES
from Crypto import Random
import base64
import json
from django.conf import settings
import types
from www.models import ConsoleConfig
import datetime
import logging
logger = logging.getLogger('default')


def decrypt(key, value, block_segments=False):
    # The base64 library fails if value is Unicode. Luckily, base64 is ASCII-safe.
    value = str(value)
    # We add back the padding ("=") here so that the decode won't fail.
    value = base64.b64decode(value + '=' * (4 - len(value) % 4), '-_')
    iv, value = value[:AES.block_size], value[AES.block_size:]
    if block_segments:
        # Python uses 8-bit segments by default for legacy reasons. In order to support
        # languages that encrypt using 128-bit segments, without having to use data with
        # a length divisible by 16, we need to pad and truncate the values.
        remainder = len(value) % 16
        padded_value = value + '\0' * (16 - remainder) if remainder else value
        cipher = AES.new(key, AES.MODE_CFB, iv, segment_size=128)
        # Return the decrypted string with the padding removed.
        return cipher.decrypt(padded_value)[:len(value)]
    return AES.new(key, AES.MODE_CFB, iv).decrypt(value)


class LicenseUtil(object):
    def __init__(self):
        if settings.LICENSE:
            self.license_data = settings.LICENSE
            self.key = "qa123zxswe3532crfvtg123bnhymjuki"
            self.__load_license()

    def __load_license(self):
        license_config = ConsoleConfig.objects.filter(key="license")
        if license_config:
            lic = license_config[0]
            self.license_data = lic.value
        else:
            ConsoleConfig(
                key="license",
                value=self.license_data,
                update_time=datetime.datetime.now()).save()
        info = decrypt(self.key, self.license_data, block_segments=True)
        self.license_info = json.loads(info)
        self.update_time = datetime.datetime.now()

    def __check_time(self):
        if (datetime.datetime.now() - self.update_time).seconds > 30:
            self.__load_license()

    def get_authorization_tenant_number(self):
        tenant = self.license_info["tenant"]
        if isinstance(tenant, int):
            tenant = int(tenant)
        return tenant

    def get_authorization_data_center_number(self):
        self.__check_time()
        data_center = self.license_info["data_center"]
        if isinstance(data_center, int):
            data_center = int(data_center)
        return data_center

    def is_expired(self):
        self.__check_time()
        end_time = self.license_info["end_time"]
        end_time_date = datetime.datetime.strptime(end_time,
                                                   "%Y-%m-%d %H:%M:%S")
        # 已过期
        if end_time_date < datetime.datetime.now():
            return True
        return False

    def set_license(self, license):
        license_data = ConsoleConfig.objects.filter(key="license")
        if license_data:
            license_data[0].value = license
            license_data[0].update_time = datetime.datetime.now()
            license_data[0].save()
        self.__load_license()

    def get_license(self):
        self.__load_license()
        return self.license_data

    def validation(self, license):
        try:
            decrypt(self.key, license, block_segments=True)
            return True
        except Exception as e:
            logger.exception(e)
            return False


LICENSE = LicenseUtil()
