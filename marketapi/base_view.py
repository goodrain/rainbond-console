# -*- coding: utf8 -*-

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from marketapi.auth import MarketAPIAuthentication


class BaseMarketAPIView(APIView):
    authentication_classes = ()
    permission_classes = ()

    def __init__(self, *args, **kwargs):
        APIView.__init__(self, *args, **kwargs)

    def success_response(self, data=None, total=0, msg='success', msg_show='成功'):
        template = {
            'msg': msg,
            'msg_show': msg_show,
            'data': {
                'bean': {},
                'list': []
            }
        }

        if data:
            if isinstance(data, list):
                template['data']['total'] = total
                template['data']['list'] = data
            elif isinstance(data, tuple):
                template['data']['list'] = list(data)
            else:
                template['data']['bean'] = data
        return Response(status=status.HTTP_200_OK, data=template)

    def error_response(self, code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg='error', msg_show='失败'):
        result = {
            'msg': msg,
            'msg_show': msg_show,
        }
        return Response(status=code, data=result)


class EnterpriseMarketAPIView(BaseMarketAPIView):
    authentication_classes = (MarketAPIAuthentication,)

    def __init__(self, *args, **kwargs):
        super(EnterpriseMarketAPIView, self).__init__(*args, **kwargs)

