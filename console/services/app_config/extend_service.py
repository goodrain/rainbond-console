# -*- coding: utf8 -*-
"""
  Created on 18/1/30.
"""

from console.repositories.app_config import extend_repo


class AppExtendService(object):
    def get_app_extend_method(self, service):
        sem = extend_repo.get_extend_method_by_service(service)

        min_node = sem.min_node if sem else 1
        step_node = sem.step_node if sem else 1
        max_node = sem.max_node if sem else 20
        min_memory = sem.min_memory if sem else 128
        max_memory = sem.max_memory if sem else 65536

        node_list = []
        memory_list = []

        node_list.append(min_node)
        next_node = min_node + step_node
        while next_node <= max_node:
            node_list.append(next_node)
            next_node += step_node

        num = 1
        memory_list.append(str(min_memory))
        next_memory = min_memory * pow(2, num)
        while next_memory <= max_memory:
            memory_list.append(str(next_memory))
            num += 1
            next_memory = min_memory * pow(2, num)
        return node_list, memory_list
