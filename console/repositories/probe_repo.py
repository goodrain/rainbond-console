# -*- coding: utf8 -*-
"""
  Created on 18/1/26.
"""
import logging

from www.models.main import ServiceProbe

logger = logging.getLogger("default")


class ServiceProbeRepository(object):
    def get_probe_by_mode(self, service_id, mode):
        probe = ServiceProbe.objects.filter(mode=mode, service_id=service_id)
        if probe:
            return probe[0]
        return None

    # 第三方组件获取探针信息
    def get_probe(self, service_id):
        return ServiceProbe.objects.filter(service_id=service_id).first()

    @staticmethod
    def list_probes(service_id):
        return ServiceProbe.objects.filter(service_id=service_id)

    def add_service_probe(self, **probe_data):
        return ServiceProbe.objects.create(**probe_data)

    def update_service_probeb(self, service_id, probe_id, **update_params):
        ServiceProbe.objects.filter(service_id=service_id, probe_id=probe_id).update(**update_params)

    def delete_probe_by_probe_id(self, service_id, probe_id):
        ServiceProbe.objects.filter(service_id=service_id, probe_id=probe_id).delete()

    def get_probe_by_probe_id(self, service_id, probe_id):
        probes = ServiceProbe.objects.filter(service_id=service_id, probe_id=probe_id)
        if probes:
            return probes[0]
        return None

    def delete_service_probe(self, service_id):
        ServiceProbe.objects.filter(service_id=service_id).delete()

    def get_service_probe(self, service_id):
        return ServiceProbe.objects.filter(service_id=service_id)

    def update_or_create(self, service_id, defaults):
        obj, _ = ServiceProbe.objects.update_or_create(service_id=service_id, defaults=defaults)
        return obj

    @staticmethod
    def bulk_create(probes):
        ServiceProbe.objects.bulk_create(probes)

    def overwrite_by_component_ids(self, component_ids, probes):
        ServiceProbe.objects.filter(service_id__in=component_ids).delete()
        self.bulk_create(probes)


probe_repo = ServiceProbeRepository()
