# -*- coding: utf8 -*-

import logging
from django.http import HttpResponse
from django.views.decorators.cache import never_cache

from www.views import BaseView
from www.models import PhoneCode

logger = logging.getLogger('default')


class PhoneCodeSuccessView(BaseView):
    # allowed_methods = ('POST',)
    @never_cache
    def post(self, request, *args, **kwargs):
        # Authorization 	此次推送请求的签名 	XML 和 SIMPLIFIED格式下均有
        # x-mns-signing-cert-url 	签名证书的地址（Base64编码过） 	XML 和 SIMPLIFIED格式下均有
        # x-mns-request-id 	此次推送消息的 Request 编号 	XML 和 SIMPLIFIED格式下均有
        # x-mns-message-id 	此次推送消息的 MessageId 	SIMPLIFIED格式下有
        # x-mns-message-tag 	此次推送消息的消息标签 	SIMPLIFIED格式下有
        # 这里使用simplified格式接收短信回调
        logger.debug('aliyunmns', self.request.META)
        # authorization = self.request.META.get("HTTP_Authorization")
        # signing_cert_url = self.request.META.get("x-mns-signing-cert-url")
        # request_id = self.request.META.get("x-mns-request-id")
        # message_id = self.request.META.get("x-mns-message-id")
        # message_tag = self.request.META.get("x-mns-message-tag")
        authorization = self.request.META.get("HTTP_AUTHORIZATION")
        signing_cert_url = self.request.META.get("HTTP_X_MNS_SIGNING_CERT_URL")
        request_id = self.request.META.get("HTTP_X_MNS_REQUEST_ID")
        message_id = self.request.META.get("HTTP_X_MNS_MESSAGE_ID")
        message_tag = self.request.META.get("HTTP_X_MNS_MESSAGE_TAG")

        logger.debug('aliyunmns', 'mns send success:authorization={0},signing_cert_url={1},request-id={2},message-id={3},message-tag={4}'.format(authorization, signing_cert_url, request_id, message_id, message_tag))

        try:
            PhoneCode.objects.filter(message_id=message_id).update(status=1)
        except Exception as e:
            logger.exception(e)

        return HttpResponse(status=204)


class PhoneCodeFailedView(BaseView):
    # allowed_methods = ('POST',)

    @never_cache
    def post(self, request, *args, **kwargs):
        # Authorization 	此次推送请求的签名 	XML 和 SIMPLIFIED格式下均有
        # x-mns-signing-cert-url 	签名证书的地址（Base64编码过） 	XML 和 SIMPLIFIED格式下均有
        # x-mns-request-id 	此次推送消息的 Request 编号 	XML 和 SIMPLIFIED格式下均有
        # x-mns-message-id 	此次推送消息的 MessageId 	SIMPLIFIED格式下有
        # x-mns-message-tag 	此次推送消息的消息标签 	SIMPLIFIED格式下有
        # 这里使用simplified格式接收短信回调
        logger.debug('aliyunmns', self.request.META)
        authorization = self.request.META.get("HTTP_AUTHORIZATION")
        signing_cert_url = self.request.META.get("HTTP_X_MNS_SIGNING_CERT_URL")
        request_id = self.request.META.get("HTTP_X_MNS_REQUEST_ID")
        message_id = self.request.META.get("HTTP_X_MNS_MESSAGE_ID")
        message_tag = self.request.META.get("HTTP_X_MNS_MESSAGE_TAG")

        logger.debug('aliyunmns', 'mns send failed:authorization={0},signing_cert_url={1},request-id={2},message-id={3},message-tag={4}'.format(authorization, signing_cert_url, request_id, message_id, message_tag))

        try:
            PhoneCode.objects.filter(message_id=message_id).update(status=2)
        except Exception as e:
            logger.exception(e)

        return HttpResponse(status=204)