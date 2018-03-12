# -*- coding: utf8 -*-
"""
  Created on 18/1/26.
"""
from console.repositories.probe_repo import probe_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid
import logging
import copy

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class ProbeService(object):
    PROBE_MODE = ("readiness", "liveness")

    def get_service_probe_by_mode(self, service, mode):
        if not mode:
            m_list = []
            for m in self.PROBE_MODE:
                probe = probe_repo.get_probe_by_mode(service.service_id, m)
                if not probe:
                    m_list.append({m: False})
                else:
                    m_list.append({m: bool(probe.is_used)})

            return 200, u"success", m_list
        if mode not in self.PROBE_MODE:
            return 400, u"参数错误,探针模式只能为readiness或liveness", None
        probe = probe_repo.get_probe_by_mode(service.service_id, mode)
        if not probe:
            return 404, u"探针不存在，您可能并未设置检测探针", None
        return 200, u"success", probe

    def __check_probe_data(self, data):
        mode = data.get("mode", None)
        if mode:
            if mode not in self.PROBE_MODE:
                return 400, u"参数错误,探针模式只能为readiness或liveness"
        port = data.get("port", None)
        if port is not None:
            if port < 1:
                return 400, u"端口号只能为1到65535的整数"
        else:
            return 400, u"端口不能为空"

        initial_delay_second = data.get("initial_delay_second", 1)
        if initial_delay_second is not None:
            if initial_delay_second < 1:
                return 400, u"初始等候时间不能小于1秒"

        period_second = data.get("period_second", 1)
        if period_second is not None:
            if period_second < 1:
                return 400, u"检测间隔不能小于1秒"

        timeout_second = data.get("timeout_second", 30)
        if timeout_second is not None:
            if timeout_second < 20:
                return 400, u"检测超时时间不能少于20秒"

        failure_threshold = data.get("failure_threshold", 3)
        if failure_threshold is not None:
            if failure_threshold < 1:
                return 400, u"标志为失败的检测次数不能少于1"

        success_threshold = data.get("success_threshold", 3)
        if success_threshold is not None:
            if success_threshold < 1:
                return 400, u"标志为成功的检测次数不能少于1"

        return 200, u"success"

    def add_service_probe(self, tenant, service, data):
        code, msg = self.__check_probe_data(data)
        if code != 200:
            return code, msg, None

        probe = probe_repo.get_probe_by_mode(service.service_id, data["mode"])
        if probe:
            return 409, u"已设置过改类型探针", None
        is_used = 1 if data.get("is_used", 1) else 0
        prob_data = {
            "service_id": service.service_id,
            "scheme": data.get("scheme", "tcp"),
            "path": data.get("path", ""),
            "port": data.get("port"),
            "cmd": data.get("cmd", ""),
            "http_header": data.get("http_header", ""),
            "initial_delay_second": data.get("initial_delay_second", 1),
            "period_second": data.get("period_second", 3),
            "timeout_second": data.get("timeout_second", 30),
            "failure_threshold": data.get("failure_threshold", 3),
            "success_threshold": data.get("success_threshold", 1),
            "is_used": is_used,
            "probe_id": make_uuid(),
            "mode": data["mode"],
        }
        # 真·深拷贝
        console_prob = copy.deepcopy(prob_data)
        prob_data["enterprise_id"] = tenant.enterprise_id

        if service.create_status == "complete":
            res, body = region_api.add_service_probe(service.service_region, tenant.tenant_name,
                                                     service.service_alias,
                                                     prob_data)
            logger.debug("add probe action status {0}".format(res.status))
        new_probe = probe_repo.add_service_probe(**console_prob)
        return 200, "success", new_probe

    def update_service_probe(self, tenant, service, data):
        code, msg = self.__check_probe_data(data)
        if code != 200:
            return code, msg, None
        probe = probe_repo.get_probe_by_mode(service.service_id, data["mode"])
        if not probe:
            return 404, u"应用未设置探针，无法进行修改操作", None
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
        if service.create_status == "complete":
            res, body = region_api.update_service_probe(service.service_region, tenant.tenant_name,
                                                        service.service_alias, prob_data)
            logger.debug("update probe action status {0}".format(res.status))
        console_probe.pop("probe_id")
        probe_repo.update_service_probe(probe.probe_id, **console_probe)
        new_probe = probe_repo.get_probe_by_mode(service.service_id, probe.mode)
        return 200, "success", new_probe

    def delete_service_probe(self, tenant, service, probe_id):
        probe = probe_repo.get_probe_by_probe_id(probe_id)
        if not probe:
            return 404, u"未找到探针"
        body = {"probe_id": probe_id}
        region_api.delete_service_probe(service.service_region, tenant.tenant_name, service.service_alias, body)
        probe.delete()
        return 200, u"success"
