"""Adapter to existing team and region APIs. Applicant access is granted last."""


class TeamApplicationProvisioner:
    def namespace_exists(self, namespace):
        from www.models.main import Tenants
        return Tenants.objects.filter(namespace=namespace).exists()

    def alias_exists(self, enterprise_id, alias):
        from www.models.main import Tenants
        return Tenants.objects.filter(enterprise_id=enterprise_id, tenant_alias=alias).exists()

    def regions(self, enterprise_id, names):
        from console.models.main import RegionConfig
        rows = list(RegionConfig.objects.filter(enterprise_id=enterprise_id, region_name__in=names, status="1"))
        mapping = {row.region_name: row for row in rows}
        if len(mapping) != len(names):
            return None
        return [mapping[name].region_alias for name in names]

    def applicant(self, row):
        from www.models.main import Users
        return Users.objects.get(user_id=row.applicant_id, enterprise_id=row.enterprise_id, is_active=True)

    def create(self, row, reviewer):
        from console.services.team_services import team_services
        from www.models.main import TenantEnterprise
        enterprise = TenantEnterprise.objects.get(enterprise_id=row.enterprise_id)
        return team_services.create_team(reviewer, enterprise, row.regions, row.team_alias, row.namespace, row.logo)

    def apply_region(self, row, region):
        from console.services.region_services import region_services
        from www.apiclient.regionapi import RegionInvokeApi
        region_services.create_tenant_on_region(row.enterprise_id, row.team_name, region, row.namespace, False)
        response, _ = RegionInvokeApi().set_tenant_resource_limit(row.enterprise_id, row.team_name, region, {
            "limit_cpu": row.quota["cpu_millicores"], "limit_memory": row.quota["memory_mib"],
            "limit_storage": row.quota["storage_gib"]})
        if int(response.get("status", 0)) != 200:
            raise RuntimeError("quota application failed")

    def grant(self, row, applicant, reviewer):
        from console.services.team_services import team_services
        from console.services.perm_services import role_kind_services, user_kind_role_service
        from www.models.main import Tenants, PermRelTenant, Users
        team = Tenants.objects.get(tenant_id=row.team_id, enterprise_id=row.enterprise_id)
        role = role_kind_services.get_role_by_name(kind="team", kind_id=team.tenant_id, name="管理员")
        team_services.add_user_role_to_team(team, [applicant.user_id], [role.ID])
        PermRelTenant.objects.filter(tenant_id=team.pk, user_id=applicant.user_id).update(identity="owner")
        if team.creater != applicant.user_id:
            original_owner = Users.objects.filter(user_id=team.creater).first()
            if original_owner:
                user_kind_role_service.delete_user_roles(kind="team", kind_id=team.tenant_id, user=original_owner)
            PermRelTenant.objects.filter(tenant_id=team.pk, user_id=team.creater).delete()
        team.creater = applicant.user_id
        team.limit_memory = row.quota["memory_mib"]
        team.save(update_fields=["creater", "limit_memory"])
