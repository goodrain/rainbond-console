# -*- coding: utf-8 -*-

from console.models.main import AppVersionTemplateRelation


class AppVersionTemplateRelationRepo(object):
    @staticmethod
    def get_by_group_id(group_id):
        return AppVersionTemplateRelation.objects.filter(group_id=group_id).first()

    @staticmethod
    def delete_by_group_id(group_id):
        return AppVersionTemplateRelation.objects.filter(group_id=group_id).delete()

    @staticmethod
    def create(**kwargs):
        relation = AppVersionTemplateRelation(**kwargs)
        relation.save()
        return relation

    @staticmethod
    def get_or_create(group_id, defaults=None):
        defaults = defaults or {}
        relation, _ = AppVersionTemplateRelation.objects.get_or_create(group_id=group_id, defaults=defaults)
        return relation


app_version_template_relation_repo = AppVersionTemplateRelationRepo()
