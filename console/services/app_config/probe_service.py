# -*- coding: utf8 -*-
"""
  Created on 18/1/26.
"""
import copy
import json
import logging

from console.exception.main import ServiceHandleException, AbortRequest
from console.repositories.probe_repo import probe_repo
from www.models.main import ServiceProbe
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class ProbeService(object):
    PROBE_MODE = ("readiness", "liveness", "ignore")

    def json_service_probe(self,
                           port,
                           scheme,
                           mode,
                           initial_delay_second,
                           period_second,
                           timeout_second,
                           success_threshold,
                           is_used=True,
                           http_header="",
                           path="",
                           **kwargs):
        service_probe_dict = dict()
        service_probe_dict["状态"] = "启用" if is_used else "禁用"
        service_probe_dict["检测端口"] = port
        service_probe_dict["探针协议"] = scheme
        service_probe_dict["不健康处理方式"] = "下线" if mode == "readiness" else "重启"
        if http_header:
            service_probe_dict["http请求头"] = http_header
        if path:
            service_probe_dict["路径"] = path
        service_probe_dict["初始化等候时间"] = "{}秒".format(initial_delay_second)
        service_probe_dict["检测间隔时间"] = "{}秒".format(period_second)
        service_probe_dict["检测超时时间"] = "{}秒".format(timeout_second)
        service_probe_dict["连续成功次数"] = success_threshold
        return json.dumps(service_probe_dict, ensure_ascii=False)

    def get_service_probe_by_mode(self, service, mode):
        if not mode:
            m_list = []
            for m in self.PROBE_MODE:
                probe = probe_repo.get_probe_by_mode(service.service_id, m)
                if not probe:
                    m_list.append({m: False})
                else:
                    m_list.append({m: bool(probe.is_used)})

            return 200, "success", m_list
        if mode not in self.PROBE_MODE:
            return 400, "参数错误,不健康处理方式只能为readiness或liveness或ignore", None
        probe = probe_repo.get_probe_by_mode(service.service_id, mode)
        if not probe:
            return 404, "探针不存在，您可能并未设置检测探针", None
        return 200, "success", probe

    def get_service_probe(self, service):
        probe = probe_repo.get_probe(service.service_id)
        if not probe:
            return 404, "探针不存在，您可能并未设置检测探针", None
        return 200, "success", probe

    def __check_probe_data(self, data):
        mode = data.get("mode", None)
        if mode:
            if mode not in self.PROBE_MODE:
                return 400, "参数错误,不健康处理方式只能为readiness或liveness或ignore"
        port = data.get("port", None)
        if port is not None:
            if port < 1:
                return 400, "端口号只能为1到65535的整数"
        else:
            return 400, "端口不能为空"

        initial_delay_second = data.get("initial_delay_second", 1)
        if initial_delay_second is not None:
            if initial_delay_second < 1:
                data["initial_delay_second"] = 1

        period_second = data.get("period_second", 1)
        if period_second is not None:
            if period_second < 1:
                data["period_second"] = 1

        timeout_second = data.get("timeout_second", 1)
        if timeout_second < 1:
            data["timeout_second"] = 1

        failure_threshold = data.get("failure_threshold", 3)
        if failure_threshold is not None:
            if failure_threshold < 1:
                data["failure_threshold"] = 3

        success_threshold = data.get("success_threshold", 3)
        if success_threshold is not None:
            if success_threshold < 1:
                data["success_threshold"] = 3

        return 200, "success"

    def create_probe(self, tenant, service, data):
        code, msg = self.__check_probe_data(data)
        if code != 200:
            raise AbortRequest("invalid probe", msg_show=msg)

        probe = probe_repo.get_probe_by_mode(service.service_id, data["mode"])
        if probe:
            raise AbortRequest("probe exists", msg_show="已设置过该类型探针", status_code=409, error_code=409)
        is_used = 1 if data.get("is_used", 1) else 0
        probe = {
            "service_id": service.service_id,
            "scheme": data.get("scheme", "tcp"),
            "path": data.get("path", ""),
            "port": data.get("port"),
            "cmd": data.get("cmd", ""),
            "http_header": data.get("http_header", ""),
            "initial_delay_second": data.get("initial_delay_second", 4),
            "period_second": data.get("period_second", 3),
            "timeout_second": data.get("timeout_second", 5),
            "failure_threshold": data.get("failure_threshold", 3),
            "success_threshold": data.get("success_threshold", 1),
            "is_used": is_used,
            "probe_id": make_uuid(),
            "mode": data["mode"],
        }
        return ServiceProbe(**probe)

    def add_service_probe(self, tenant, service, data):
        probe = self.create_probe(tenant, service, data)
        probe = probe.to_dict()
        # deep copy
        logger.debug("create status: {}".format(service.create_status))
        if service.create_status == "complete":
            new_probe = copy.deepcopy(probe)
            new_probe["enterprise_id"] = tenant.enterprise_id
            res, body = region_api.add_service_probe(service.service_region, tenant.tenant_name, service.service_alias,
                                                     new_probe)
            logger.debug("add probe action status {0}".format(res.status))
        new_probe = probe_repo.add_service_probe(**probe)
        return 200, "success", new_probe

    def update_service_probea(self, tenant, service, data, user_name=''):
        code, msg = self.__check_probe_data(data)
        if code != 200:
            raise ServiceHandleException(status_code=code, msg_show=msg, msg="error")
        probes = probe_repo.get_service_probe(service.service_id)
        if not probes:
            if service.service_source == "third_party":
                code, msg, new_probe = self.add_service_probe(tenant, service, data)
                return new_probe
            raise ServiceHandleException(status_code=404, msg="no found", msg_show="组件未设置探针，无法进行修改操作")
        probe = probes[0]
        # delete more probe without first, one service will have one probe
        if len(probes) > 1:
            for index in range(len(probes)):
                if index > 0:
                    self.delete_service_probe(tenant, service, probes[index].probe_id)
        if not probe:
            raise ServiceHandleException(status_code=404, msg="no found", msg_show="组件未设置探针，无法进行修改操作")
        is_used = data.get("is_used", None)
        if is_used is None:
            is_used = probe.is_used
        else:
            is_used = 1 if is_used else 0
        prob_data = {
            "service_id": service.service_id,
            "scheme": data.get("scheme", probe.scheme),
            "path": data.get("path", probe.path),
            "port": data.get("port", probe.port),
            "cmd": data.get("cmd", probe.cmd),
            "http_header": data.get("http_header", probe.http_header),
            "initial_delay_second": data.get("initial_delay_second", probe.initial_delay_second),
            "period_second": data.get("period_second", probe.period_second),
            "timeout_second": data.get("timeout_second", probe.timeout_second),
            "failure_threshold": data.get("failure_threshold", probe.failure_threshold),
            "success_threshold": data.get("success_threshold", probe.success_threshold),
            "is_used": is_used,
            "probe_id": probe.probe_id,
            "mode": data["mode"]
        }
        console_probe = copy.deepcopy(prob_data)
        prob_data["enterprise_id"] = tenant.enterprise_id
        prob_data["operator"] = user_name
        if service.create_status == "complete":
            try:
                res, body = region_api.update_service_probec(service.service_region, tenant.tenant_name, service.service_alias,
                                                             prob_data)
                logger.debug("update probe action status {0}".format(res.status))
            except region_api.CallApiError as e:
                logger.debug(e)
                if e.message.get("httpcode") == 404:
                    probe.delete()
        console_probe.pop("probe_id")
        console_probe.pop("service_id")
        probe_repo.update_service_probeb(service_id=service.service_id, probe_id=probe.probe_id, **console_probe)
        new_probe = probe_repo.get_probe_by_probe_id(service.service_id, probe.probe_id)
        return new_probe

    def delete_service_probe(self, tenant, service, probe_id):
        probe = probe_repo.get_probe_by_probe_id(service.service_id, probe_id)
        if not probe:
            return 404, "未找到探针"
        body = {"probe_id": probe_id}
        region_api.delete_service_probe(service.service_region, tenant.tenant_name, service.service_alias, body)
        probe.delete()
        return 200, "success"
