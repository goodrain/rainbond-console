# -*- coding: utf-8 -*-

from console.models.main import TeamHelmReleaseSource


class TeamHelmReleaseSourceRepository(object):
    def save_or_update(self, **params):
        defaults = dict(params)
        region_name = defaults.pop("region_name")
        namespace = defaults.pop("namespace")
        release_name = defaults.pop("release_name")
        obj, _ = TeamHelmReleaseSource.objects.update_or_create(
            region_name=region_name,
            namespace=namespace,
            release_name=release_name,
            defaults=defaults
        )
        return obj

    def get_by_release(self, region_name, namespace, release_name):
        record = TeamHelmReleaseSource.objects.filter(
            region_name=region_name,
            namespace=namespace,
            release_name=release_name
        ).first()
        if not record:
            return None
        return record.to_dict()

    def list_by_releases(self, region_name, namespace, release_names):
        names = [name for name in (release_names or []) if name]
        if not names:
            return {}
        records = TeamHelmReleaseSource.objects.filter(
            region_name=region_name,
            namespace=namespace,
            release_name__in=names
        )
        return {
            "{}/{}".format(record.namespace, record.release_name): record.to_dict()
            for record in records
        }

    def delete_by_release(self, region_name, namespace, release_name):
        return TeamHelmReleaseSource.objects.filter(
            region_name=region_name,
            namespace=namespace,
            release_name=release_name
        ).delete()


helm_release_source_repo = TeamHelmReleaseSourceRepository()
