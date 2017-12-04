# -*- coding: utf8 -*-
from api.views.base import APIView
import sys
import json
import logging
from rest_framework import status
from api.serializers import ServerProbeSerializer
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceProbe
from django.forms.models import model_to_dict
from www.views import AuthedView
from django.http import JsonResponse
from www.utils.crypt import make_uuid
region_api = RegionInvokeApi()
reload(sys)
sys.setdefaultencoding('UTF-8')

logger = logging.getLogger('default')


def errResponseJson(message, messagecn, code):
    result = {}
    result["code"] = code
    result["msg"] = message
    result["msgcn"] = messagecn
    return JsonResponse(result, status=200)


def successResponseJson(bean=None):
    result = {}
    result["code"] = 200
    result["body"] = {}
    result["body"]["bean"] = bean
    return JsonResponse(result, status=200)


class ServiceProbeManager(AuthedView):
    def post(self, request, *args, **kwargs):
        """
        探针信息添加
        ---
        serializer: ServerProbeSerializer
        """
        try:
            mode = request.POST.get("mode", None)
            if (not mode) or ((mode != "readiness") and (mode != "liveness")):
                return errResponseJson(
                    "mode can not be empty and only is readiness os liveness",
                    "参数错误,探针模式未指定", 412)

            port = request.POST.get("port", None)
            if not port:
                return errResponseJson("port can not be empty.", "参数错误,端口未指定",
                                       412)
            port = int(port)
            service_probe = ServiceProbe(
                service_id=self.service.service_id,
                scheme=request.POST.get("scheme", "tcp"),
                path=request.POST.get("path", ""),
                port=port,
                cmd=request.POST.get("cmd", ""),
                http_header=request.POST.get("http_header", ""),
                initial_delay_second=int(request.POST.get("initial_delay_second",
                                                      1)),
                period_second=int(request.POST.get("period_second", 3)),
                timeout_second=int(request.POST.get("timeout_second", 30)),
                failure_threshold=int(request.POST.get("failure_threshold", 3)),
                success_threshold=int(request.POST.get("success_threshold", 1)),
                is_used=bool(request.POST.get("is_used", True)),
                probe_id=make_uuid(),
                mode=mode)
            if not ServiceProbe.objects.filter(
                    service_id=service_probe.service_id,
                    mode=service_probe.mode):
                json_data = model_to_dict(service_probe)
                is_used = 1 if json_data["is_used"] else 0
                json_data.update({"is_used": is_used})
                json_data["enterprise_id"] = self.tenant.enterprise_id
                res, body = region_api.add_service_probe(self.service.service_region, self.tenantName,
                                                         self.service.service_alias,
                                                         json_data)


                if 400 <= res.status <= 600:
                    return errResponseJson("region error.", "数据中心操作失败", 500)
                service_probe.save()
            else:
                return errResponseJson(
                    "this {} probe can only have one in same service.".format(
                        service_probe.mode), "应用探测设置重复", 400)
            return successResponseJson(bean=model_to_dict(service_probe))
        except Exception as e:
            logger.debug("---------------- {}".format(json_data))
            logger.exception(e)
            return errResponseJson(e.message, "系统异常，处理错误", 500)

    def get(self, request, *args, **kwargs):
        """
        探针信息获取
        ---
        """
        try:
            mode = request.GET.get("mode", None)
            if not mode:
                return errResponseJson(
                    "mode can not be empty and only is readiness os liveness",
                    "参数错误,探针模式未指定", 412)
            probe = ServiceProbe.objects.filter(
                mode=mode, service_id=self.service.service_id)
            if probe:
                data = model_to_dict(probe[0])
                return successResponseJson(bean=data)
            else:
                return errResponseJson("the probe not exist.", "配置不存在", 404)

        except Exception as e:
            logger.exception(e)
            return errResponseJson(e.message, "系统异常，处理错误", 500)


class ServiceProbeUsedUpdateManager(AuthedView):
    def post(self, request, probe_id, *args, **kwargs):
        try:
            probe_list = ServiceProbe.objects.filter(probe_id=probe_id)
            if not probe_list:
                return errResponseJson("the probe not exist.", "配置不存在", 404)
            probe = probe_list[0]
            if probe.is_used:
                probe.is_used = 0
            else:
                probe.is_used = 1
            data = model_to_dict(probe)
            data["enterprise_id"] = self.tenant.enterprise_id
            res, body = region_api.update_service_probe(self.service.service_region, self.tenantName,
                                                        self.service.service_alias, data)

            if 400 <= res.status <= 600:
                return errResponseJson("region error.", "数据中心操作失败", 500)
            probe.save()
            return successResponseJson()
        except Exception as e:
            logger.exception(e)
            return errResponseJson(e.message, "系统异常，处理错误", 500)


class ServiceProbeInfoUpdateManager(AuthedView):
    def post(self, request, probe_id, *args, **kwargs):
        """
        探针信息更改
        ---
        serializer: ServerProbeSerializer
        parameters:
            - name: probe_id
              description: 探针id
              required: true
              type: string
              paramType: path
        """
        try:
            probe_list = ServiceProbe.objects.filter(probe_id=probe_id)
            if not probe_list:
                return errResponseJson("the probe not exist.", "配置不存在", 404)
            probe = probe_list[0]
            mode = request.POST.get("mode", None)
            if (not mode) or ((mode != "readiness") and (mode != "liveness")):
                return errResponseJson(
                    "mode can not be empty and only is readiness os liveness",
                    "参数错误,探针模式未指定", 412)
            port = int(request.POST.get("port", None))
            if not port:
                return errResponseJson("port can not be empty.", "参数错误,端口未指定",
                                       412)
            service_probe = ServiceProbe(
                probe_id=probe_id,
                service_id=self.service.service_id,
                scheme=request.POST.get("scheme", "tcp"),
                path=request.POST.get("path", ""),
                port=port,
                cmd=request.POST.get("cmd", ""),
                http_header=request.POST.get("http_header", ""),
                initial_delay_second=int(request.POST.get("initial_delay_second",
                                                      1)),
                period_second=int(request.POST.get("period_second", 3)),
                timeout_second=int(request.POST.get("timeout_second", 30)),
                failure_threshold=int(request.POST.get("failure_threshold", 3)),
                success_threshold=int(request.POST.get("success_threshold", 1)),
                is_used=bool(request.POST.get("is_used", 1)),
                mode=mode)
            json_data = model_to_dict(probe)
            is_used = 1 if json_data["is_used"] else 0
            json_data.update({"is_used": is_used})
            json_data["enterprise_id"] = self.tenant.enterprise_id
            res, body = region_api.update_service_probe(self.service.service_region, self.tenantName,
                                                        self.service.service_alias, json_data)
            if 400 <= res.status <= 600:
                return errResponseJson("region error.", "数据中心操作失败", 500)
            probe.delete()
            service_probe.save()
            return successResponseJson(bean=model_to_dict(service_probe))
        except Exception as e:
            logger.exception(e)
            return errResponseJson(e.message, "系统异常，处理错误", 500)

    def get(self, request, probe_id, format=None):
        """
        探针信息获取
        ---
        parameters:
            - name: probe_id
              description: 探针id
              required: true
              type: string
              paramType: path
        """
        try:
            if not probe_id:
                return errResponseJson("the probe id not exist.", "配置ID不存在",
                                       404)
            probe = ServiceProbe.objects.get(probe_id=probe_id)
            if probe:
                data = model_to_dict(probe)
                return successResponseJson(bean=data)
            else:
                return errResponseJson("the probe not exist.", "配置不存在", 404)
        except Exception as e:
            logger.exception(e)
            return errResponseJson(e.message, "系统异常，处理错误", 500)
