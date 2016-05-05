# -*- coding:utf-8 -*-
import requests
from django.conf import settings
import json

from www.models import AppServiceRelation, AppServicePort, \
    AppServiceEnv, ServiceExtendMethod

import logging
logger = logging.getLogger('default')


class AppSendUtil:
    def __init__(self, service_key, app_version):
        self.service_key = service_key
        self.app_version = app_version

    def send_services(self, req_data):
        """发送服务信息, 不包括图片文本"""
        if len(req_data) == 0:
            logger.warning('there is no data to send!')
        else:
            # 获取扩展数据
            pre_list = AppServiceRelation.objects.filter(service_key=self.service_key,
                                                         app_version=self.app_version)
            suf_list = AppServiceRelation.objects.filter(dep_service_key=self.service_key,
                                                         dep_app_version=self.app_version)
            env_list = AppServiceEnv.objects.filter(service_key=self.service_key,
                                                    app_version=self.app_version)
            port_list = AppServicePort.objects.filter(service_key=self.service_key,
                                                      app_version=self.app_version)
            extend_list = ServiceExtendMethod.objects.filter(service_key=self.service_key,
                                                             app_version=self.app_version)
            tmp_data = {'cloud_assistant': settings.CLOUD_ASSISTANT}
            all_data = {
                'pre_list': list(pre_list),
                'suf_list': list(suf_list),
                'env_list': list(env_list),
                'port_list': list(port_list),
                'extend_list': list(extend_list),
                'service': dict(req_data, **tmp_data),
            }
            retry = 3
            while retry > 0:
                num = self._send_services(all_data)
                if num == 0:
                    retry = 0
                else:
                    retry -= 1

    def _send_services(self, all_data):
        try:
            dest_url = settings.CLOUD_MARKET + 'api/v0/service'
            headers = {'content-type': 'application/json'}
            data = json.dumps(all_data)
            logger.debug('post service json data={}'.format(data))
            resp = requests.post(dest_url, headers=headers, data=data)
            logger.info(resp)
            result_data = resp.status_code
            if result_data == 200:
                return 0
            else:
                return 1
        except requests.exceptions.RequestException as ce:
            logger.error('send service to app error!', ce)
            return 2

    def send_image(self, file_key, file_path):
        """发送服务信息, 不包括图片文本"""
        retry = 3
        while retry > 0:
            num = self._send_image(file_key, file_path)
            if num == 0:
                retry = 0
            else:
                retry -= 1

    def _send_image(self, file_key, file_path):
        try:
            dest_url = settings.CLOUD_MARKET + 'api/v0/service/logo'
            data = {'service_key': self.service_key,
                    'app_version': self.app_version}
            files = {file_key: open(file_path, 'rb')}
            resp = requests.post(dest_url, data=data, files=files)
            logger.info(resp)
            result_data = resp.status_code
            if result_data == 200:
                return 0
            else:
                return 1
        except requests.exceptions.RequestException as ce:
            logger.error('send service to app error!', ce)
            return 2


    def query_service(self, service_key, app_version):
        try:
            dest_url = settings.CLOUD_MARKET + 'api/v0/service'
            headers = {'content-type': 'application/json'}
            all_data = {
                'service_key': service_key,
                'app_version': app_version,
                'cloud_assistant': settings.CLOUD_ASSISTANT,
            }
            data = json.dumps(all_data)
            logger.debug('post service json data={}'.format(data))
            resp = requests.get(dest_url, headers=headers, data=data)
            logger.info(resp)
            result_data = resp.status_code
            if result_data == 200:
                data = resp.json()
                if data.get('code') == 200:
                    return data.get('data')
                else:
                    return json.dumps({"code": 500})
            else:
                return json.dumps({"code": 500})
        except requests.exceptions.RequestException as ce:
            logger.error('send service to app error!', ce)
            return json.dumps({"code": 500})
