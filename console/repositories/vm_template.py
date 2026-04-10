# -*- coding: utf8 -*-
from www.models.main import VMTemplate, VMTemplateDisk, VMTemplateVersion


class VMTemplateRepo(object):
    def get_template_by_name(self, tenant_id, name):
        return VMTemplate.objects.filter(tenant_id=tenant_id, name=name).first()

    def list_templates(self, tenant_id):
        return VMTemplate.objects.filter(tenant_id=tenant_id).order_by("-ID")

    def get_template(self, tenant_id, template_id):
        return VMTemplate.objects.filter(tenant_id=tenant_id, ID=template_id).first()

    def create_template(self, **kwargs):
        return VMTemplate.objects.create(**kwargs)

    def save_template(self, template):
        template.save()
        return template

    def list_template_versions(self, tenant_id, template_id):
        return VMTemplateVersion.objects.filter(tenant_id=tenant_id, template_id=template_id).order_by("-ID")

    def get_template_version(self, tenant_id, version_id):
        return VMTemplateVersion.objects.filter(tenant_id=tenant_id, ID=version_id).first()

    def get_template_versions_by_ids(self, tenant_id, version_ids):
        if not version_ids:
            return []
        return VMTemplateVersion.objects.filter(tenant_id=tenant_id, ID__in=version_ids)

    def create_template_version(self, **kwargs):
        return VMTemplateVersion.objects.create(**kwargs)

    def save_template_version(self, version):
        version.save()
        return version

    def list_template_disks(self, tenant_id, template_version_id):
        return VMTemplateDisk.objects.filter(
            tenant_id=tenant_id, template_version_id=template_version_id
        ).order_by("order_index", "ID")

    def list_template_disks_by_version_ids(self, tenant_id, version_ids):
        if not version_ids:
            return []
        return VMTemplateDisk.objects.filter(
            tenant_id=tenant_id, template_version_id__in=version_ids
        ).order_by("order_index", "ID")

    def create_template_disk(self, **kwargs):
        return VMTemplateDisk.objects.create(**kwargs)

    def delete_template_disks(self, tenant_id, template_version_id):
        return VMTemplateDisk.objects.filter(
            tenant_id=tenant_id, template_version_id=template_version_id
        ).delete()


vm_template_repo = VMTemplateRepo()
