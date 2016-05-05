# -*- coding:utf-8 -*-
import requests
from django.conf import settings
import json

from www.models import AppServiceRelation, AppServicePort, \
    AppServiceEnv, ServiceExtendMethod
from www.app_http import AppServiceApi
appClient = AppServiceApi()

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
            req_data.update({'cloud_assistant': settings.CLOUD_ASSISTANT})
            all_data = {
                'pre_list': map(lambda x: x.to_dict(), pre_list),
                'suf_list': map(lambda x: x.to_dict(), suf_list),
                'env_list': map(lambda x: x.to_dict(), env_list),
                'port_list': map(lambda x: x.to_dict(), port_list),
                'extend_list': map(lambda x: x.to_dict(), extend_list),
                'service': req_data,
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
            logger.debug(all_data)
            data = json.dumps(all_data)
            logger.debug('post service json data={}'.format(data))
            res, resp = appClient.publishServiceData(data)
            logger.debug(res)
            return 0
        except requests.exceptions.RequestException as ce:
            logger.exception('send service to app error!', ce)
            return 2

    def send_image(self, file_key, file_path):
        """发送服务信息, 不包括图片文本"""
        if file_path:
            retry = 3
            while retry > 0:
                num = self._send_image(file_key, file_path)
                if num == 0:
                    retry = 0
                else:
                    retry -= 1

    def _send_image(self, file_key, file_path):
        try:
            data = {'service_key': self.service_key,
                    'app_version': self.app_version}
            files = {file_key: open(file_path, 'rb')}
            res, resp = appClient.uploadFiles(body=data, files=files)
            logger.debug(res)
            return 0
        except requests.exceptions.RequestException as ce:
            logger.error('send service to app error!', ce)
            return 2

    def query_service(self, service_key, app_version):
        try:
            all_data = {
                'service_key': service_key,
                'app_version': app_version,
                'cloud_assistant': settings.CLOUD_ASSISTANT,
            }
            data = json.dumps(all_data)
            logger.debug('post service json data={}'.format(data))
            res, resp = appClient.getServiceData(body=data)
            logger.info(res)
            logger.info(resp)
            if res.status == 200:
                logger.debug(resp.data)
                return json.loads(resp.data)
            else:
                return json.dumps({"code": 500})
        except requests.exceptions.RequestException as ce:
            logger.error('send service to app error!', ce)
            return json.dumps({"code": 500})
