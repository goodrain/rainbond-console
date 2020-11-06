
# -*- coding: utf8 -*-

from console.models.main import ComponentGraph
from console.exception.exceptions import ErrComponentGraphExists


class ComponentGraphRepository(object):
    @staticmethod
    def list(component_id):
        return ComponentGraph.objects.filter(component_id=component_id)

    @staticmethod
    def get(component_id, graph_id):
        try:
            return ComponentGraph.objects.get(component_id=component_id, graph_id=graph_id)
        except ComponentGraph.DoesNotExist:
            raise ErrComponentGraphExists

    def create(self, component_id, graph_id, title, promql, sequence):
        # check if the component graph already exists
        self.get(component_id=component_id, graph_id=graph_id)
        ComponentGraph.objects.create(
            component_id=component_id,
            graph_id=graph_id,
            title=title,
            promql=promql,
            sequence=sequence,
        )


component_graph_repo = ComponentGraphRepository()
