"""Installation-scoped, signed GET-only inventory export."""
import os
from typing import Any

from django.db.models import Q, QuerySet
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from console.services.cleanup_retirement import template_retirement_targets, snapshot_protected_components, RetirementConflict
from console.services.cleanup_gateway import CleanupGatewayUnavailable
from console.services.cleanup_installation import resolve_gateway_key
from console.models.main import (AppVersionTemplateRelation, RainbondCenterApp, RainbondCenterAppVersion,
                                 ServiceUpgradeRecord, AppUpgradeSnapshot)
from console.repositories.region_repo import region_repo
from console.services.cleanup_inventory import (template_resource, verify_source_request, version_resources,
                                                deployment_resource, failed_scope_label, snapshot_reference_resource,
                                                registry_reference_resource)
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroup, ServiceGroupRelation, Tenants, TenantServiceInfo


class CleanupInventoryView(APIView):
    # Internal HMAC authentication below; browser login credentials are not accepted.
    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ["get"]

    def finalize_response(self, request: Request, response: Response, *args: Any, **kwargs: Any) -> Response:
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response

    def get(self, request: Request, enterprise_id: str, region_name: str) -> Response:
        allowed_enterprise = os.environ.get("CLEANUP_SOURCE_ENTERPRISE_ID", "")
        allowed_regions = os.environ.get("CLEANUP_SOURCE_REGIONS", "").split(",")
        # Optional explicit legacy scope narrows access; otherwise installation ownership is authoritative.
        if ((allowed_enterprise and enterprise_id != allowed_enterprise)
                or (os.environ.get("CLEANUP_SOURCE_REGIONS") and region_name not in allowed_regions)):
            return Response({"errorCode": "SOURCE_SCOPE_UNAVAILABLE"}, status=403)
        try:
            key = resolve_gateway_key(enterprise_id, region_name)
        except CleanupGatewayUnavailable:
            return Response({"errorCode": "SOURCE_AUTH_UNAVAILABLE"}, status=503)
        if not verify_source_request(request.method, request.get_full_path(), enterprise_id, region_name,
                                     request.headers.get("X-Cleanup-Source-Time"),
                                     request.headers.get("X-Cleanup-Source-Signature"), key):
            return Response({"errorCode": "FORBIDDEN"}, status=403)
        if not region_repo.get_enterprise_region_by_region_name(enterprise_id, region_name):
            return Response({"errorCode": "FORBIDDEN"}, status=403)
        kind = request.query_params.get("kind")
        try:
            cursor = int(request.query_params.get("cursor", "0"))
            upper = int(request.query_params.get("upper", "0"))
            if cursor < 0 or upper < 0 or kind not in ("templates", "versions", "deployments", "snapshots"):
                raise ValueError()
        except ValueError:
            return Response({"errorCode": "INVALID_REQUEST"}, status=400)
        reference_scope = request.query_params.get("reference_scope", "")
        if reference_scope:
            if reference_scope != "registry" or kind not in ("templates", "snapshots"):
                return Response({"errorCode": "INVALID_REQUEST"}, status=400)
            return self._registry_reference_inventory(enterprise_id, region_name, kind, cursor, upper, key)
        teams = Tenants.objects.filter(enterprise_id=enterprise_id)
        page: list[dict[str, Any]]
        if kind == "templates":
            template_query = RainbondCenterAppVersion.objects.filter(
                Q(enterprise_id=enterprise_id) | Q(share_team__in=teams.values_list("tenant_name", flat=True))).filter(
                Q(region_name=region_name) | Q(region_name="") | Q(region_name__isnull=True))
            if upper == 0:
                upper = template_query.order_by("-ID").values_list("ID", flat=True).first() or 0
            if cursor > upper:
                return Response({"errorCode": "INVALID_REQUEST"}, status=400)
            template_fields = ("ID", "app_id", "version", "share_team", "app_template", "enterprise_id", "region_name",
                               "source", "is_complete", "cleanup_activation_revision")
            page = list(template_query.filter(ID__gt=cursor, ID__lte=upper).order_by("ID").values(*template_fields)[:26])
        elif kind == "snapshots":
            # Include the enterprise's retained snapshots across regions. A
            # cross-region image match protects content; it never grants delete.
            snapshot_query = AppUpgradeSnapshot.objects.filter(tenant_id__in=teams.values_list("tenant_id", flat=True))
            if upper == 0:
                upper = snapshot_query.order_by("-ID").values_list("ID", flat=True).first() or 0
            if cursor > upper:
                return Response({"errorCode": "INVALID_REQUEST"}, status=400)
            page = [dict(row) for row in snapshot_query.filter(
                ID__gt=cursor, ID__lte=upper).order_by("ID").values("ID", "snapshot")[:26]]
        elif kind == "deployments":
            deployment_query = ServiceUpgradeRecord.objects.filter(
                app_upgrade_record__tenant_id__in=teams.values_list("tenant_id", flat=True),
                service__tenant_id__in=teams.values_list("tenant_id", flat=True), service__service_region=region_name)
            if upper == 0:
                upper = deployment_query.order_by("-ID").values_list("ID", flat=True).first() or 0
            if cursor > upper:
                return Response({"errorCode": "INVALID_REQUEST"}, status=400)
            deployment_fields = ("ID", "service_id", "service_cname", "status", "app_upgrade_record_id",
                                 "app_upgrade_record__version", "app_upgrade_record__old_version",
                                 "app_upgrade_record__record_type", "app_upgrade_record__group_name")
            page = list(
                deployment_query.filter(ID__gt=cursor, ID__lte=upper).order_by("ID").values(*deployment_fields)[:26])
        else:
            version_query = TenantServiceInfo.objects.filter(
                tenant_id__in=teams.values_list("tenant_id", flat=True), service_region=region_name)
            if upper == 0:
                upper = version_query.order_by("-ID").values_list("ID", flat=True).first() or 0
            if cursor > upper:
                return Response({"errorCode": "INVALID_REQUEST"}, status=400)
            version_fields = ("ID", "service_id", "service_alias", "service_cname", "tenant_id")
            page = list(version_query.filter(ID__gt=cursor, ID__lte=upper).order_by("ID").values(*version_fields)[:26])
        more = len(page) > 25
        page = page[:25]
        resources, failures = [], []
        team_rows = list(teams.values("tenant_id", "tenant_name", "tenant_alias"))
        team_labels = {team["tenant_name"]: team["tenant_alias"] or team["tenant_name"] for team in team_rows}
        if kind == "templates":
            template_names = dict(RainbondCenterApp.objects.filter(
                Q(enterprise_id=enterprise_id) | Q(create_team__in=team_labels),
                app_id__in=[row["app_id"] for row in page]).values_list("app_id", "app_name"))
            for row in page:
                row["app_name"] = template_names.get(row["app_id"], "")
        elif kind != "snapshots":
            team_ids = {team["tenant_id"]: team["tenant_alias"] or team["tenant_name"] for team in team_rows}
            relations = list(ServiceGroupRelation.objects.filter(
                tenant_id__in=team_ids, region_name=region_name,
                service_id__in=[row["service_id"] for row in page]).values("service_id", "tenant_id", "group_id"))
            app_labels = dict(ServiceGroup.objects.filter(
                tenant_id__in=team_ids, region_name=region_name,
                ID__in=[row["group_id"] for row in relations]).values_list("ID", "group_name"))
            owners: dict[str, set[str]] = {}
            for relation in relations:
                label = " / ".join(value for value in [team_ids.get(relation["tenant_id"], ""),
                                                       app_labels.get(relation["group_id"], "")] if value)
                if label:
                    owners.setdefault(relation["service_id"], set()).add(label)
            for row in page:
                row["owner_name"] = " · ".join(sorted(owners.get(row["service_id"], set())))
                if not row["owner_name"]:
                    row["owner_name"] = team_ids.get(row.get("tenant_id", ""), "")
        if kind == "templates":
            hidden = set(AppVersionTemplateRelation.objects.filter(
                tenant_id__in=teams.values_list("tenant_id", flat=True)).values_list("app_model_id", flat=True))
            try:
                targets = template_retirement_targets(enterprise_id, region_name, page, key)
            except RetirementConflict:
                # Incomplete safety evidence disables retirement, not inventory display.
                targets = {}
                failures.append("snapshot_references_unavailable")
            for row in page:
                row["retirement"] = targets.get(row["ID"])
            resources = [template_resource(row, region_name, row["app_id"] in hidden) for row in page]
            failures.extend(failed_scope_label(row) for row in resources if not row["observed"])
        elif kind == "snapshots":
            resources = [snapshot_reference_resource(row, region_name) for row in page]
            failures.extend(failed_scope_label(row) for row in resources if not row["observed"])
        elif kind == "deployments":
            resources = [deployment_resource(row, region_name) for row in page]
        else:
            try:
                protected_components = snapshot_protected_components(enterprise_id)
                references_complete = True
            except (RetirementConflict, ValueError, TypeError):
                protected_components = set()
                references_complete = False
                failures.append("snapshot_references_unavailable")
            names = dict(teams.values_list("tenant_id", "tenant_name"))
            api = RegionInvokeApi()
            for component in page:
                try:
                    body = api.get_service_build_versions(region_name, names[component["tenant_id"]], component["service_alias"])
                    if not isinstance(body, dict) or not isinstance(body.get("bean"), dict):
                        raise ValueError("source unavailable")
                    component["retirement_references_complete"] = references_complete
                    component["snapshot_referenced"] = component["service_id"] in protected_components
                    rows = version_resources(component, body["bean"], region_name)
                    if len(rows) > 5000:
                        raise ValueError("source limit")
                    resources.extend(rows)
                except Exception:
                    # Never return upstream bodies, URLs, credentials or full exception text.
                    failures.append(failed_scope_label(component))
        return Response({"enterprise": enterprise_id, "region": region_name, "kind": kind,
                         "resources": resources, "cursor": page[-1]["ID"] if more else 0, "upper": upper,
                         "failedScopes": failures, "referencesComplete": False})

    @staticmethod
    def _registry_reference_inventory(enterprise_id: str, region_name: str, kind: str,
                                      cursor: int, upper: int, key: bytes) -> Response:
        query: QuerySet[Any]
        fields: tuple[str, ...]
        # These rows are protection evidence, not a cross-enterprise resource
        # listing. The projection strips ownership, names and retirement actions.
        if kind == "templates":
            query = RainbondCenterAppVersion.objects.all()
            fields = ("ID", "app_id", "version", "app_template")
        else:
            query = AppUpgradeSnapshot.objects.all()
            fields = ("ID", "snapshot")
        if upper == 0:
            upper = query.order_by("-ID").values_list("ID", flat=True).first() or 0
        if cursor > upper:
            return Response({"errorCode": "INVALID_REQUEST"}, status=400)
        page = list(query.filter(ID__gt=cursor, ID__lte=upper).order_by("ID").values(*fields)[:26])
        more = len(page) > 25
        page = page[:25]
        resources = [registry_reference_resource(row, kind, region_name, key) for row in page]
        failures = [row["id"] for row in resources if not row["observed"]]
        # Another Region's retained runtime versions need their own bound audit.
        # Do not silently treat that uncollected source as empty.
        if region_repo.get_region_info_all().exclude(region_name=region_name).exists():
            failures.append("other_region_reference_audit_required")
        return Response({"enterprise": enterprise_id, "region": region_name, "kind": kind,
                         "referenceScope": "registry", "resources": resources,
                         "cursor": page[-1]["ID"] if more else 0, "upper": upper,
                         "failedScopes": failures, "referencesComplete": not failures})
