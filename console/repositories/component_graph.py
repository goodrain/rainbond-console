# -*- coding: utf8 -*-

from console.models.main import ComponentGraph
from console.exception.exceptions import ErrComponentGraphExists, ErrComponentGraphNotFound


class ComponentGraphRepository(object):
    @staticmethod
    def list(component_id):
        return ComponentGraph.objects.filter(component_id=component_id).order_by("sequence")

    @staticmethod
    def list_by_component_ids(component_ids):
        return ComponentGraph.objects.filter(component_id__in=component_ids)

    @staticmethod
    def list_gt_sequence(component_id, sequence):
        return ComponentGraph.objects.filter(component_id=component_id, sequence__gt=sequence)

    @staticmethod
    def list_between_sequence(component_id, left_sequence, right_sequence):
        return ComponentGraph.objects.filter(
            component_id=component_id, sequence__gte=left_sequence, sequence__lt=right_sequence)

    @staticmethod
    def get(component_id, graph_id):
        try:
            return ComponentGraph.objects.get(component_id=component_id, graph_id=graph_id)
        except ComponentGraph.DoesNotExist:
            raise ErrComponentGraphNotFound

    def create(self, component_id, graph_id, title, promql, sequence):
        # check if the component graph already exists
        try:
            self.get(component_id=component_id, graph_id=graph_id)
            raise ErrComponentGraphExists
        except ErrComponentGraphNotFound:
            pass
        ComponentGraph.objects.create(
            component_id=component_id,
            graph_id=graph_id,
            title=title,
            promql=promql,
            sequence=sequence,
        )

    @staticmethod
    def delete(component_id, graph_id):
        ComponentGraph.objects.filter(component_id=component_id, graph_id=graph_id).delete()

    @staticmethod
    def update(component_id, graph_id, **data):
        ComponentGraph.objects.filter(component_id=component_id, graph_id=graph_id).update(**data)


component_graph_repo = ComponentGraphRepository()
