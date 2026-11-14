"""Authenticated real delivery APIs, independently scoped from application snapshots."""
from django.db import IntegrityError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponseRedirect
from typing import Any
from rest_framework.request import Request
from rest_framework.response import Response
from console.views.base import JWTAuthApiView
from console.services.delivery_manifest import DeliveryError
from console.services.delivery_templates import DeliveryService, scope_of
from console.services.delivery_access import team_access, target_access
from console.services.delivery_credentials import seal
from console.services.delivery_worker import start_delivery_worker
from www.utils.return_message import general_message, get_exception_message


class DeliveryAPI(JWTAuthApiView):
    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        self.perform_authentication(request)
        self.check_permissions(request)
        super().initial(request, *args, **kwargs)
        self.delivery = DeliveryService()
        start_delivery_worker()

    def handle_exception(self, exc: Exception) -> Response:
        if isinstance(exc, DeliveryError):
            return Response(general_message(exc.status, "failed", get_exception_message(exc)), status=exc.status)
        if isinstance(exc, (ValueError, TypeError, DjangoValidationError)):
            return Response(general_message(400, "failed", "请求参数无效"), status=400)
        if isinstance(exc, IntegrityError):
            return Response(general_message(409, "failed", "记录已存在或状态已变化，请刷新后重试"), status=409)
        return super().handle_exception(exc)

    def reply(self, bean: Any, status: int = 200) -> Response:
        return Response(general_message(status, "success", "操作成功", bean=bean), status=status)

    def scope(self, request: Request, team_name: str, app_id: str, write: bool = False) -> dict[str, str]:
        region_name = request.GET.get("region_name") or request.data.get("region_name")
        if not region_name:
            raise DeliveryError("请选择源集群")
        scope: dict[str, str] = {
            "enterprise_id": str(self.user.enterprise_id),
            "team_name": team_name,
            "app_id": str(app_id),
            "region_name": region_name
        }
        team_access(self.user, team_name, 310001 if write else 300002, app_id, self.is_enterprise_admin)
        from www.models.main import ServiceGroup
        if not ServiceGroup.objects.filter(ID=app_id, region_name=scope["region_name"]).exists():
            raise DeliveryError("源应用与集群不匹配", 404)
        return scope

    def admin(self, enterprise_id: str) -> None:
        if not self.is_enterprise_admin or str(self.user.enterprise_id) != enterprise_id:
            raise DeliveryError("仅平台管理员可以访问", 403)


class DeliveryTemplatesView(DeliveryAPI):
    def get(self, request: Request, team_name: str, app_id: str) -> Response:
        return self.reply(self.delivery.list(self.scope(request, team_name, app_id)))

    def post(self, request: Request, team_name: str, app_id: str) -> Response:
        scope = self.scope(request, team_name, app_id, write=True)
        if request.data.get("is_platform_plugin") and not self.is_enterprise_admin:
            raise DeliveryError("仅平台管理员可以创建平台插件模板", 403)
        if request.data.get("sync_id"):
            version = self.delivery.publish(self.user, scope, request.data["sync_id"])
        else:
            version = self.delivery.create(self.user, scope, request.data, request.data.get("request_id"))
        return self.reply(self.delivery.version_data(version), 201)


class DeliveryListingWithdrawalView(DeliveryAPI):
    def post(self, request: Request, team_name: str, app_id: str, version_id: str, request_id: str) -> Response:
        scope = self.scope(request, team_name, app_id, write=True)
        row = self.delivery.withdraw_listing(self.user, scope, version_id, request_id, request.data.get("action"))
        return self.reply(self.delivery.listing_data(row))


class DeliveryChangesView(DeliveryAPI):
    def get(self, request: Request, team_name: str, app_id: str) -> Response:
        return self.reply(self.delivery.changes(self.scope(request, team_name, app_id)))


class DeliverySourceView(DeliveryAPI):
    def get(self, request: Request, team_name: str, app_id: str) -> Response:
        from console.services.delivery_manifest import public_manifest
        source, _ = self.delivery.gateway.source(self.scope(request, team_name, app_id))
        return self.reply(public_manifest(source))


class DeliverySyncView(DeliveryAPI):
    def post(self, request: Request, team_name: str, app_id: str) -> Response:
        self.scope(request, team_name, app_id, write=True)
        raise DeliveryError("创建模板已无需同步，请刷新页面后重新创建", 409)


class DeliverySyncTaskView(DeliveryAPI):
    def get(self, request: Request, team_name: str, app_id: str, task_id: str) -> Response:
        return self.reply(self.delivery.sync(self.scope(request, team_name, app_id), task_id))

    def delete(self, request: Request, team_name: str, app_id: str, task_id: str) -> Response:
        scope = self.scope(request, team_name, app_id, write=True)
        self.delivery.cancel(scope, task_id)
        return self.reply(self.delivery.sync(scope, task_id))


class DeliverySyncRetryView(DeliveryAPI):
    def post(self, request: Request, team_name: str, app_id: str, task_id: str) -> Response:
        self.scope(request, team_name, app_id, write=True)
        raise DeliveryError("产物同步已调整到管理员审核后执行，请重新创建模板", 409)


class DeliverySyncLogsView(DeliveryAPI):
    def get(self, request: Request, team_name: str, app_id: str, task_id: str, component_key: str) -> Response:
        task = self.delivery.repo.task(self.scope(request, team_name, app_id), task_id)
        item = task.items.filter(key=component_key).first()
        if not item:
            raise DeliveryError("组件任务不存在", 404)
        return self.reply(self.delivery.gateway.logs(task, item) if item.event_id else {"lines": []})


class DeliveryVersionView(DeliveryAPI):
    def get(self, request: Request, team_name: str, app_id: str, version_id: str) -> Response:
        version = self.delivery.repo.version(self.scope(request, team_name, app_id), version_id, available=False)
        return self.reply(self.delivery.version_data(version))

    def delete(self, request: Request, team_name: str, app_id: str, version_id: str) -> Response:
        version = self.delivery.delete(self.user, self.scope(request, team_name, app_id, write=True), version_id)
        return self.reply({"id": str(version.id)})


class DeliveryOperationView(DeliveryAPI):
    def get(self, request: Request, team_name: str, app_id: str, version_id: str, operation: str) -> Response:
        if operation != "exports":
            raise DeliveryError("操作不存在", 404)
        scope = self.scope(request, team_name, app_id)
        version = self.delivery.repo.version(scope, version_id, available=False)
        tasks = version.tasks.filter(kind="offline").select_related("template", "version")
        return self.reply({
            "items": [self.delivery.task_data(task) for task in tasks],
            "formats": self.delivery.version_data(version)["export_formats"],
            "deleted": bool(version.deleted_at)
        })

    def post(self, request: Request, team_name: str, app_id: str, version_id: str, operation: str) -> Response:
        scope = self.scope(request, team_name, app_id, write=True)
        version = self.delivery.repo.version(scope, version_id)
        if operation == "listing-requests":
            return self.reply(self.delivery.listing_data(self.delivery.listing(self.user, scope, version_id, request.data)),
                              201)
        kind = {"installations": "delivery", "exports": "offline"}.get(operation)
        if not kind:
            raise DeliveryError("操作不存在", 404)
        if kind == "delivery":
            target_access(self.user, request.data.get("target"), scope, version, kind, self.is_enterprise_admin)
        data = {key: value for key, value in request.data.items() if key != "environment"}
        if request.data.get("environment"):
            data["encrypted_environment"] = seal(request.data["environment"])
        task = self.delivery.operation(self.user, scope, version_id, kind, data, request.data.get("request_id"))
        return self.reply(self.delivery.task_data(task), 202)


class DeliveryApplicationRecordsView(DeliveryAPI):
    def get(self, request: Request, team_name: str, app_id: str) -> Response:
        scope = self.scope(request, team_name, app_id)
        templates = self.delivery.repo.templates(scope)
        listings = self.delivery.m.DeliveryListingRequest.objects.filter(
            version__template__in=templates).select_related("version__template")
        tasks = self.delivery.m.DeliveryTask.objects.filter(template__in=templates, kind__in=["delivery", "offline",
                                                                                              "test"]).select_related(
                                                                                                  "version", "template")
        return self.reply({
            "listings": [self.delivery.listing_data(row) for row in listings],
            "deployments": [self.delivery.task_data(task) for task in tasks]
        })


class DevelopmentDeliveriesView(DeliveryAPI):
    def get(self, request: Request, enterprise_id: str) -> Response:
        self.admin(enterprise_id)
        rows = self.delivery.m.DeliveryListingRequest.objects.filter(
            version__template__enterprise_id=enterprise_id).select_related("version__template")
        if request.GET.get("group_id"):
            rows = rows.filter(version__template_id=request.GET["group_id"])
        tasks = self.delivery.m.DeliveryTask.objects.filter(template__enterprise_id=enterprise_id,
                                                            kind__in=["delivery", "test", "offline"]).select_related(
                                                                "template", "version")
        if request.GET.get("group_id"):
            tasks = tasks.filter(template_id=request.GET["group_id"])
        source_app_exists = None
        if request.GET.get("group_id"):
            profile = self.delivery.m.DeliveryTemplate.objects.filter(
                id=request.GET["group_id"], enterprise_id=enterprise_id).first()
            if profile:
                from www.models.main import Tenants, ServiceGroup
                teams = Tenants.objects.filter(enterprise_id=enterprise_id, tenant_name=profile.team_name)
                team_id = teams.values_list("tenant_id", flat=True).first()
                source_app_exists = bool(team_id and str(profile.app_id).isdigit()) and ServiceGroup.objects.filter(
                    ID=profile.app_id, region_name=profile.region_name, tenant_id=team_id).exists()
        return self.reply({
            "listings": [self.delivery.listing_data(row) for row in rows],
            "deployments": [self.delivery.task_data(task) for task in tasks],
            "source_app_exists": source_app_exists
        })


class DeliveryReviewView(DeliveryAPI):
    def post(self, request: Request, enterprise_id: str, request_id: str) -> Response:
        self.admin(enterprise_id)
        row = self.delivery.review(self.user,
                                   request_id,
                                   request.data.get("decision"),
                                   str(request.data.get("comment", "")),
                                   admin=True)
        return self.reply(self.delivery.listing_data(row))


class DeliveryTestView(DeliveryAPI):
    def post(self, request: Request, enterprise_id: str, request_id: str) -> Response:
        self.admin(enterprise_id)
        row = self.delivery.m.DeliveryListingRequest.objects.select_related("version__template").filter(
            id=request_id, version__template__enterprise_id=enterprise_id).first()
        if not row or row.version.deleted_at:
            raise DeliveryError("上架申请不存在或版本已删除", 404)
        scope = scope_of(row.version.template)
        target_access(self.user, request.data.get("target"), scope, row.version, "test", True)
        data = {key: value for key, value in request.data.items() if key != "environment"}
        data["listing_id"] = str(row.id)
        if request.data.get("environment"):
            data["encrypted_environment"] = seal(request.data["environment"])
        task = self.delivery.operation(self.user, scope, row.version_id, "test", data, request.data.get("request_id"))
        return self.reply(self.delivery.task_data(task), 202)


class DeliveryTaskUpgradeView(DeliveryAPI):
    def get(self, request: Request, task_id: str) -> Response:
        task = self.delivery.m.DeliveryTask.objects.select_related("template", "version").filter(
            id=task_id, template__enterprise_id=self.user.enterprise_id).first()
        if not task:
            raise DeliveryError("交付任务不存在", 404)
        team_access(self.user, task.template.team_name, 300002, task.template.app_id, self.is_enterprise_admin)
        return self.reply(self.delivery.gateway.upgrade_info(task, self.user, self.is_enterprise_admin))


class DeliveryTaskView(DeliveryAPI):
    def get(self, request: Request, task_id: str, download: bool = False) -> Response | HttpResponseRedirect:
        task = self.delivery.m.DeliveryTask.objects.select_related("template", "version").filter(
            id=task_id, template__enterprise_id=self.user.enterprise_id).first()
        if not task:
            raise DeliveryError("交付任务不存在", 404)
        team_access(self.user, task.template.team_name, 310002 if download else 300002, task.template.app_id,
                    self.is_enterprise_admin)
        if download:
            if task.kind != "offline" or task.status != "succeeded" or task.version.deleted_at:
                raise DeliveryError("离线包尚不可下载", 409)
            from console.services.app_import_and_export_service import export_service
            path = task.result.get("download_path", "")
            if not path.startswith("/v2/app/download/"):
                raise DeliveryError("离线包下载地址不可用", 409)
            return HttpResponseRedirect(
                export_service._wrapper_director_download_url(task.template.region_name, path.replace("/v2", "", 1)))
        return self.reply(self.delivery.task_data(task))


class DeliveryTargetsView(DeliveryAPI):
    def get(self, request: Request) -> Response:
        from www.models.main import Tenants, TenantRegionInfo
        from console.models.main import RegionConfig
        result = []
        for team in Tenants.objects.filter(enterprise_id=self.user.enterprise_id):
            try:
                team_access(self.user, team.tenant_name, 300001, admin=self.is_enterprise_admin)
            except DeliveryError:
                continue
            names = TenantRegionInfo.objects.filter(tenant_id=team.tenant_id).values_list("region_name", flat=True)
            regions = RegionConfig.objects.filter(enterprise_id=self.user.enterprise_id, region_name__in=names, status="1")
            result.append({
                "team_name": team.tenant_name,
                "team_alias": team.tenant_alias,
                "regions": [{
                    "name": region.region_name,
                    "alias": region.region_alias
                } for region in regions]
            })
        return self.reply({"teams": result})


class DeliveryTaskRetryView(DeliveryAPI):
    def post(self, request: Request, task_id: str) -> Response:
        from django.db import transaction
        with transaction.atomic():
            hint = self.delivery.m.DeliveryTask.objects.filter(
                id=task_id, template__enterprise_id=self.user.enterprise_id).first()
            if hint and hint.kind == "catalog_publish" and hint.version_id:
                self.delivery.m.DeliveryTemplateVersion.objects.select_for_update().get(id=hint.version_id)
            task = self.delivery.m.DeliveryTask.objects.select_for_update().select_related("template", "version").filter(
                id=task_id, template__enterprise_id=self.user.enterprise_id).first()
            if not task or task.status != "failed" or not task.version or task.version.deleted_at:
                raise DeliveryError("此任务不可重试", 409)
            if task.kind == "catalog_publish":
                if task.payload.get("destination", {}).get("type") == "market":
                    team_access(self.user, task.template.team_name, 310001, task.template.app_id, self.is_enterprise_admin)
                else:
                    self.admin(str(self.user.enterprise_id))
                task.items.filter(status="failed").update(status="queued", result={}, remote_id="", event_id="", error="")
                self.delivery.m.DeliveryListingRequest.objects.filter(publication_task=task).update(
                    publication_status="publishing")
            else:
                team_access(self.user, task.template.team_name, 310001, task.template.app_id, self.is_enterprise_admin)
                if task.kind in ("delivery", "test"):
                    target_access(self.user, task.payload.get("target"), scope_of(task.template), task.version, task.kind,
                                  self.is_enterprise_admin)
            task.status, task.error = "queued", ""
            task.save(update_fields=["status", "error", "updated_at"])
        return self.reply(self.delivery.task_data(task), 202)
