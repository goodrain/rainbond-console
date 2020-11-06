# -*- coding: utf8 -*-

from console.repositories.component_graph import component_graph_repo
from www.utils.crypt import make_uuid


class ComponentGraphService(object):
    def create_component_graph(self, component_id, title, promql):
        promql = self.add_or_update_label(component_id, promql)
        graph_id = make_uuid()
        sequence = self._next_sequence(component_id)
        component_graph_repo.create(component_id, graph_id, title, promql, sequence)
        return component_graph_repo.get(component_id, graph_id).to_dict()

    def add_or_update_label(self, component_id, promql):
        """
        Add service_id label, or replace illegal service_id label
        """
        return promql

    @staticmethod
    def _next_sequence(component_id):
        graphs = component_graph_repo.list(component_id=component_id)
        if not graphs:
            return 0
        sequences = [graph.sequence for graph in graphs]
        sequences.sort()
        return sequences[len(sequences)-1]+1



component_graph_service = ComponentGraphService()
