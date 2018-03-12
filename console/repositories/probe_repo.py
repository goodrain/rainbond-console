# -*- coding: utf8 -*-
"""
  Created on 18/1/26.
"""
from www.models.main import ServiceProbe
import logging

logger = logging.getLogger("default")


class ServiceProbeRepository(object):
    def get_probe_by_mode(self, service_id, mode):
        probe = ServiceProbe.objects.filter(
            mode=mode, service_id=service_id)
        if probe:
            return probe[0]
        return None

    def add_service_probe(self, **probe_data):
        return ServiceProbe.objects.create(**probe_data)

    def update_service_probe(self, probe_id, **update_params):
        ServiceProbe.objects.filter(probe_id=probe_id).update(**update_params)

    def delete_probe_by_probe_id(self, probe_id):
        ServiceProbe.objects.filter(probe_id=probe_id).delete()

    def get_probe_by_probe_id(self, probe_id):
        probes = ServiceProbe.objects.filter(probe_id=probe_id)
        if probes:
            return probes[0]
        return None

    def delete_service_probe(self, service_id):
        ServiceProbe.objects.filter(service_id=service_id).delete()

probe_repo = ServiceProbeRepository()
