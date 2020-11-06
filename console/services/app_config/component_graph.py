# -*- coding: utf8 -*-

from django.db import transaction

from console.repositories.component_graph import component_graph_repo
from www.utils.crypt import make_uuid


class ComponentGraphService(object):
    def create_component_graph(self, component_id, title, promql):
        promql = self.add_or_update_label(component_id, promql)
        graph_id = make_uuid()
        sequence = self._next_sequence(component_id)
        component_graph_repo.create(component_id, graph_id, title, promql, sequence)
        return component_graph_repo.get(component_id, graph_id).to_dict()

    @staticmethod
    def list_component_graphs(component_id):
        graphs = component_graph_repo.list(component_id)
        return [graph.to_dict() for graph in graphs]

    @transaction.atomic()
    def delete_component_graph(self, graph):
        component_graph_repo.delete(graph.component_id, graph.graph_id)
        self._sequence_move_forward(graph.component_id, graph.sequence)

    @transaction.atomic()
    def update_component_graph(self, graph, title, promql, sequence):
        data = {
            "title": title,
            "promql": self.add_or_update_label(graph.component_id, promql),
        }
        if sequence != graph.sequence:
            data["sequence"] = sequence
        self._sequence_move_back(graph.component_id, sequence, graph.sequence)
        component_graph_repo.update(graph.component_id, graph.graph_id, **data)
        return component_graph_repo.get(graph.component_id, graph.graph_id).to_dict()

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
        return sequences[len(sequences) - 1] + 1

    @staticmethod
    def _sequence_move_forward(component_id, sequence):
        graphs = component_graph_repo.list_gt_sequence(component_id=component_id, sequence=sequence)
        for graph in graphs:
            graph.sequence -= 1
            graph.save()

    @staticmethod
    def _sequence_move_back(component_id, left_sequence, right_sequence):
        graphs = component_graph_repo.list_between_sequence(
            component_id=component_id, left_sequence=left_sequence, right_sequence=right_sequence)
        for graph in graphs:
            graph.sequence += 1
            graph.save()


component_graph_service = ComponentGraphService()
