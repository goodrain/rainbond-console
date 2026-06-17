# -*- coding: utf8 -*-
"""
  Created on 18/1/30.
"""
# NOTE: www.models.label models (Labels/ServiceLabels/NodeLabels) are not
# imported during django.setup(), so they are absent from the app registry and
# django-stubs cannot resolve `.objects`. The per-line ignores below suppress
# those false positives; remove them once the models are registered.
from typing import List, Optional

from django.db.models import QuerySet

from www.models.label import ServiceLabels, NodeLabels, Labels
from www.utils.crypt import make_uuid
import datetime


class ServiceLabelsReporsitory(object):
    def get_service_labels(self, service_id: str) -> QuerySet[ServiceLabels]:
        return ServiceLabels.objects.filter(service_id=service_id)  # type: ignore[attr-defined]

    def delete_service_labels(self, service_id: str, label_id: str) -> None:
        ServiceLabels.objects.filter(service_id=service_id, label_id=label_id).delete()  # type: ignore[attr-defined]

    def delete_service_all_labels(self, service_id: str) -> None:
        ServiceLabels.objects.filter(service_id=service_id).delete()  # type: ignore[attr-defined]

    def get_service_label(self, service_id: str, label_id: str) -> Optional[ServiceLabels]:
        return ServiceLabels.objects.filter(service_id=service_id, label_id=label_id).first()  # type: ignore[attr-defined]

    @staticmethod
    def list_by_component_ids(component_ids: List[str]) -> QuerySet[ServiceLabels]:
        return ServiceLabels.objects.filter(service_id__in=component_ids)  # type: ignore[attr-defined]

    @staticmethod
    def bulk_create(labels: List[ServiceLabels]) -> None:
        ServiceLabels.objects.bulk_create(labels)  # type: ignore[attr-defined]

    def overwrite_by_component_ids(self, component_ids: List[str], labels: List[ServiceLabels]) -> None:
        ServiceLabels.objects.filter(service_id__in=component_ids).delete()  # type: ignore[attr-defined]
        self.bulk_create(labels)


class NodeLabelsReporsitory(object):
    def get_node_label_by_region(self, region_id: str) -> QuerySet[NodeLabels]:
        return NodeLabels.objects.filter(region_id=region_id)  # type: ignore[attr-defined]

    def get_all_labels(self) -> QuerySet[NodeLabels]:
        labels = NodeLabels.objects.all()  # type: ignore[attr-defined]
        return labels


class LabelsReporsitory(object):
    def get_labels_by_label_ids(self, label_ids: List[str]) -> QuerySet[Labels]:
        return Labels.objects.filter(label_id__in=label_ids)  # type: ignore[attr-defined]

    def get_label_by_label_id(self, label_id: str) -> Optional[Labels]:
        labels = Labels.objects.filter(label_id=label_id)  # type: ignore[attr-defined]
        if labels:
            return labels[0]
        return None

    def get_all_labels(self) -> QuerySet[Labels]:
        labels = Labels.objects.all()  # type: ignore[attr-defined]
        return labels

    def create_label(self, label_name: str, label_alias: str) -> Labels:
        label_id = make_uuid("labels")
        create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        label = Labels(label_id=label_id, label_name=label_name, label_alias=label_alias, create_time=create_time)
        label.save()
        return label

    def get_labels_by_label_name(self, label_name: str) -> Optional[Labels]:
        return Labels.objects.filter(label_name=label_name).first()  # type: ignore[attr-defined]

    @staticmethod
    def list_by_label_ids(label_ids: List[str]) -> QuerySet[Labels]:
        return Labels.objects.filter(label_id__in=label_ids)  # type: ignore[attr-defined]

    @staticmethod
    def bulk_create(labels: List[Labels]) -> List[Labels]:
        return Labels.objects.bulk_create(labels)  # type: ignore[attr-defined]


service_label_repo = ServiceLabelsReporsitory()
label_repo = LabelsReporsitory()
node_label_repo = NodeLabelsReporsitory()
