"""Template lifecycle. No snapshot APIs, models, IDs or browser-side state."""
import copy
import uuid
from urllib.parse import quote
from django.db import transaction
from django.utils import timezone
from console.repositories.delivery_template_repo import DeliveryRepository
from console.services.delivery_manifest import DeliveryError, baseline, compare, digest, prepare, public_manifest


def actor(user):
    return user.nick_name or str(user.user_id)


def scope_of(template):
    return {key: getattr(template, key) for key in ("enterprise_id", "team_name", "region_name", "app_id")}


class DeliveryService:
    def __init__(self, models=None, gateway=None):
        self.repo = DeliveryRepository(models)
        self.m = self.repo.models
        if gateway is None:
            from console.services.delivery_gateway import DeliveryGateway
            gateway = DeliveryGateway()
        self.gateway = gateway

    def _identity(self, user, scope):
        if str(user.enterprise_id) != scope["enterprise_id"]:
            raise DeliveryError("无权访问此模板", 403)

    def start(self, user, scope, data, request_key=None):
        self._identity(user, scope)
        request_key = "sync:" + str(user.user_id) + ":" + str(request_key or uuid.uuid4())
        existing = self.m.DeliveryTask.objects.filter(request_key=request_key, template__in=self.repo.templates(scope)).first()
        if existing:
            return existing
        source, app_name = self.gateway.source(scope)
        with transaction.atomic():
            template, _ = self.m.DeliveryTemplate.objects.get_or_create(**scope,
                                                                        defaults={
                                                                            "name": str(data.get("template_name", ""))[:64],
                                                                            "app_name": app_name
                                                                        })
            manifest = public_manifest(prepare(source, data, template.id.hex))
            if template.versions.filter(version=manifest["group_version"]).exists():
                raise DeliveryError("此模板版本号已存在，请使用新的版本号", 409)
            task = self.m.DeliveryTask.objects.create(template=template,
                                                      kind="sync",
                                                      actor_id=user.user_id,
                                                      actor_name=actor(user),
                                                      request_key=request_key,
                                                      payload={
                                                          "manifest": manifest,
                                                          "baseline": baseline(source),
                                                          "description": data.get("description", "")
                                                      })
            for component in manifest["apps"]:
                self.m.DeliveryTaskItem.objects.create(task=task, key=component["service_id"], component=component)
            for plugin in manifest.get("plugins", []):
                self.m.DeliveryTaskItem.objects.create(task=task, key="plugin:" + plugin["plugin_id"], component=plugin)
        return task

    def advance(self, task_id):
        """One persisted execution step. Called by the worker, never by status GET."""
        with transaction.atomic():
            task = self.m.DeliveryTask.objects.select_for_update().select_related("template", "version").get(id=task_id)
            if task.status not in ("queued", "running"):
                return
            try:
                if task.kind == "sync":
                    self._advance_sync(task)
                elif task.kind == "offline":
                    if task.status == "queued":
                        task.result = self.gateway.export(task)
                        task.status = "running"
                    else:
                        result = self.gateway.export_status(task)
                        if result.get("status") in ("success", "failed"):
                            task.status = "succeeded" if result["status"] == "success" else "failed"
                            task.result.update(result)
                elif task.kind in ("delivery", "test"):
                    if task.status == "queued":
                        task.result = self.gateway.install(task)
                        task.status = "running"
                    else:
                        task.status = self.gateway.installation_status(task)
                elif task.kind == "catalog_publish":
                    if task.payload["destination"]["type"] == "market":
                        self.gateway.prepare_catalog(task)
                        if not task.items.exists():
                            manifest = task.version.manifest
                            for component in manifest["apps"]:
                                self.m.DeliveryTaskItem.objects.create(task=task,
                                                                       key=component["service_id"],
                                                                       component=component)
                            for plugin in manifest.get("plugins", []):
                                self.m.DeliveryTaskItem.objects.create(task=task,
                                                                       key="plugin:" + plugin["plugin_id"],
                                                                       component=plugin)
                        self._advance_sync(task)
                    else:
                        task.status = "succeeded"
                    if task.status == "succeeded":
                        task.result = self.gateway.publish_catalog(task)
            except DeliveryError as error:
                task.status, task.error = "failed", error.message[:256]
            except Exception:
                # Upstream bodies may contain registry credentials. Only safe errors reach UI/audit.
                task.status = "failed"
                task.error = "任务执行失败，请检查组件事件或重试任务"
            task.save(update_fields=["status", "payload", "result", "error", "updated_at"])
            if task.kind == "catalog_publish":
                self.m.DeliveryListingRequest.objects.filter(publication_task=task).update(publication_status={
                    "succeeded": "published",
                    "failed": "failed"
                }.get(task.status, "publishing"))

    def _advance_sync(self, task):
        task.status = "running"
        for item in task.items.order_by("key"):
            if item.status in ("success", "failed"):
                continue
            try:
                if item.status == "queued":
                    item.result = self.gateway.dispatch(task, item)
                    item.remote_id = item.result["share_id"]
                    item.event_id = item.result.get("event_id", "")
                    item.status = "syncing"
                else:
                    state = self.gateway.status(task, item).get("status", "")
                    if state in ("success", "failure", "failed", "timeout"):
                        item.status = "success" if state == "success" else "failed"
            except DeliveryError as error:
                item.status, item.error = "failed", error.message[:256]
            except Exception:
                item.status, item.error = "failed", "组件产物同步失败，请查看组件日志"
            item.save()
        states = list(task.items.values_list("status", flat=True))
        if "failed" in states:
            task.status = "failed"
        elif states and all(state == "success" for state in states):
            task.status = "succeeded"

    def sync(self, scope, task_id):
        task = self.repo.task(scope, task_id)
        if task.kind != "sync":
            raise DeliveryError("任务类型无效")
        items = list(task.items.order_by("key"))
        return {
            "id":
            str(task.id),
            "status": {
                "queued": "syncing",
                "running": "syncing",
                "succeeded": "success"
            }.get(task.status, task.status),
            "components": [{
                "service_id": item.key,
                "name": item.component.get("service_cname", item.key),
                "status": item.status,
                "error": item.error
            } for item in items],
            "percent":
            int(sum(item.status == "success" for item in items) * 100 / len(items)) if items else 0,
            "version_id":
            str(task.version_id) if task.version_id else ""
        }

    def retry(self, scope, task_id):
        with transaction.atomic():
            task = self.repo.task(scope, task_id)
            task = self.m.DeliveryTask.objects.select_for_update().get(id=task.id)
            if task.status != "failed" or task.kind != "sync":
                raise DeliveryError("当前任务不能重试", 409)
            task.items.filter(status="failed").update(status="queued", remote_id="", event_id="", result={}, error="")
            task.status, task.error = "queued", ""
            task.save()
        return task

    def cancel(self, scope, task_id):
        with transaction.atomic():
            task = self.repo.task(scope, task_id)
            task = self.m.DeliveryTask.objects.select_for_update().get(id=task.id)
            if task.version_id:
                raise DeliveryError("此模板版本已经发布", 409)
            task.status = "cancelled"
            task.save()
        return task

    def publish(self, user, scope, sync_id):
        self._identity(user, scope)
        with transaction.atomic():
            job = self.repo.task(scope, sync_id)
            job = self.m.DeliveryTask.objects.select_for_update().get(id=job.id)
            if job.version_id:
                return self.repo.version(scope, job.version_id, available=False)
            if job.kind != "sync" or job.status != "succeeded" or job.items.exclude(status="success").exists():
                raise DeliveryError("请等待全部组件同步成功后发布", 409)
            manifest = copy.deepcopy(job.payload["manifest"])
            results = {item.key: item.result for item in job.items.all()}
            for component in manifest["apps"]:
                result = results[component["service_id"]]
                if result.get("image_name"):
                    component["share_image"] = result["image_name"]
                    component.pop("share_slug_path", None)
                    for disk in (component.get("vm") or {}).get("disk_layout", []):
                        if str(disk.get("disk_role", "")).lower() == "root":
                            disk.update(image=result["image_name"], source_type="http-artifact")
                            disk.pop("source_uri", None)
                if result.get("slug_path"):
                    component["share_slug_path"] = result["slug_path"]
                    component.pop("share_image", None)
            for plugin in manifest.get("plugins", []):
                result = results["plugin:" + plugin["plugin_id"]]
                plugin["share_image"] = result.get("image_name", "")
            if job.template.versions.filter(version=manifest["group_version"]).exists():
                raise DeliveryError("版本号已经存在，请重新发布新版本", 409)
            row = self.m.DeliveryTemplateVersion.objects.create(template=job.template,
                                                                version=manifest["group_version"],
                                                                description=job.payload["description"],
                                                                manifest=manifest,
                                                                source_baseline=job.payload["baseline"],
                                                                digest=digest(manifest),
                                                                sync_id=job.id,
                                                                creator_id=user.user_id,
                                                                creator_name=actor(user))
            job.version = row
            job.save(update_fields=["version", "updated_at"])
            job.template.name = manifest["group_name"]
            job.template.save(update_fields=["name"])
            return row

    def version_data(self, version):
        template = version.template
        manifest = public_manifest(version.manifest)
        scope = scope_of(template)
        parameters = []
        for component in manifest["apps"]:
            variables = component.get("service_env_map_list", []) + component.get("service_connect_info_map_list", [])
            for env in variables:
                if env.get("required_on_install"):
                    parameters.append({
                        "service_id": component["service_id"],
                        "name": component["service_cname"],
                        "attr_name": env["attr_name"]
                    })
        return {
            "id":
            str(version.id),
            "template_id":
            str(template.id),
            "version_id":
            str(version.id),
            "template_name":
            manifest["group_name"],
            "version":
            version.version,
            "description":
            version.description,
            "scope":
            ":".join(quote(scope[key], safe="") for key in ("enterprise_id", "team_name", "region_name", "app_id")),
            "status":
            "deleted" if version.deleted_at else "published",
            "destination":
            "local",
            "creator_name":
            version.creator_name,
            "created_at":
            version.created_at.isoformat(),
            "deleted_at":
            version.deleted_at.isoformat() if version.deleted_at else "",
            "deleted_by":
            version.deleted_by,
            "is_platform_plugin":
            bool(manifest.get("platform_plugin")),
            "plugin":
            manifest.get("platform_plugin", {}),
            "manifest_digest":
            version.digest,
            "manifest":
            manifest,
            "components": [{
                "service_id": c["service_id"],
                "name": c["service_cname"],
                "service_alias": c.get("service_alias"),
                "source_type": c.get("service_source", "image"),
                "source": c.get("git_url") or c.get("image", ""),
                "branch": c.get("code_branch", ""),
                "commit": c.get("code_version", ""),
                "deploy_version": c.get("deploy_version"),
                "vm": c.get("vm")
            } for c in manifest["apps"]],
            "installation_parameters":
            parameters,
            "component_overrides": [{
                "service_id": c["service_id"],
                "extend_method": c.get("extend_method"),
                "service_env_map_list": c.get("service_env_map_list", []),
                "extend_method_map": c.get("extend_method_map", {})
            } for c in manifest["apps"]]
        }

    def list(self, scope):
        templates = self.repo.templates(scope)
        versions = self.m.DeliveryTemplateVersion.objects.filter(template__in=templates).select_related("template")
        jobs = self.m.DeliveryTask.objects.filter(template__in=templates, kind="sync",
                                                  version__isnull=True).exclude(status="cancelled")
        return {
            "items": [self.version_data(row) for row in versions],
            "active_syncs": [{
                "id": str(job.id),
                "created_at": job.created_at.isoformat()
            } for job in jobs[:10]]
        }

    def changes(self, scope):
        latest = self.m.DeliveryTemplateVersion.objects.filter(template__in=self.repo.templates(scope),
                                                               deleted_at__isnull=True).first()
        if not latest:
            return {"checks": []}
        source, _ = self.gateway.source(scope)
        return {
            "checks": [{
                "baseline_id": str(latest.id),
                "template_name": latest.template.name,
                "version": latest.version,
                **compare(latest.source_baseline, baseline(source))
            }]
        }

    def delete(self, user, scope, version_id):
        self._identity(user, scope)
        with transaction.atomic():
            row = self.repo.version(scope, version_id)
            row = self.m.DeliveryTemplateVersion.objects.select_for_update().get(id=row.id)
            row.deleted_at, row.deleted_by = timezone.now(), actor(user)
            row.save(update_fields=["deleted_at", "deleted_by"])
            row.listings.filter(status="pending").update(status="cancelled", reviewed_at=timezone.now(), comment="源版本已删除")
        return row

    def operation(self, user, scope, version_id, kind, data, request_key=None):
        self._identity(user, scope)
        if kind not in ("delivery", "test", "offline"):
            raise DeliveryError("不支持的交付操作")
        with transaction.atomic():
            version = self.repo.version(scope, version_id)
            # Shared lock with delete: no new operations after retirement.
            version = self.m.DeliveryTemplateVersion.objects.select_for_update().get(id=version.id)
            if version.deleted_at:
                raise DeliveryError("版本已删除", 409)
            task, created = self.m.DeliveryTask.objects.get_or_create(
                request_key="operation:" + str(user.user_id) + ":" + str(request_key or uuid.uuid4()),
                defaults={
                    "template": version.template,
                    "version": version,
                    "kind": kind,
                    "actor_id": user.user_id,
                    "actor_name": actor(user),
                    "payload": copy.deepcopy(data)
                })
            conflicts = (task.version_id != version.id, task.kind != kind, task.payload.get("target") != data.get("target"))
            if not created and any(conflicts):
                raise DeliveryError("此请求标识已用于其他交付操作", 409)
            return task

    def listing(self, user, scope, version_id, data):
        self._identity(user, scope)
        with transaction.atomic():
            version = self.repo.version(scope, version_id)
            version = self.m.DeliveryTemplateVersion.objects.select_for_update().get(id=version.id)
            reason = str(data.get("reason", "")).strip()
            if not reason or len(reason) > 500:
                raise DeliveryError("请填写500字以内的上架说明")
            destination = data.get("destination") or {"type": "local"}
            if version.listings.filter(status__in=["pending", "approved"], destination=destination).exists():
                raise DeliveryError("此版本已申请上架", 409)
            if destination.get("type") not in (
                    "local", "market") or destination.get("type") == "market" and not destination.get("market_id"):
                raise DeliveryError("请选择上架位置")
            return self.m.DeliveryListingRequest.objects.create(version=version,
                                                                destination=destination,
                                                                reason=reason,
                                                                applicant_id=user.user_id,
                                                                applicant_name=actor(user))

    def review(self, user, request_id, decision, comment, admin=False):
        if not admin:
            raise DeliveryError("仅平台管理员可以审核", 403)
        with transaction.atomic():
            row = self.m.DeliveryListingRequest.objects.select_for_update().select_related("version__template").filter(
                id=request_id, version__template__enterprise_id=user.enterprise_id).first()
            if not row:
                raise DeliveryError("上架申请不存在", 404)
            if row.status != "pending" or row.version.deleted_at:
                raise DeliveryError("此申请已处理或版本已删除", 409)
            if decision not in ("approved", "rejected") or len(comment) > 500 or decision == "rejected" and not comment.strip():
                raise DeliveryError("驳回需要填写原因")
            row.status, row.comment, row.reviewer_name, row.reviewed_at = decision, comment.strip(), actor(user), timezone.now()
            if decision == "approved":
                row.publication_task = self.m.DeliveryTask.objects.create(template=row.version.template,
                                                                          version=row.version,
                                                                          kind="catalog_publish",
                                                                          actor_id=user.user_id,
                                                                          actor_name=actor(user),
                                                                          request_key="listing:" + str(row.id),
                                                                          payload={"destination": row.destination})
                row.publication_status = "publishing"
            row.save()
        return row

    def listing_data(self, row):
        template = row.version.template
        return {
            "id":
            str(row.id),
            "group_id":
            str(template.id),
            "enterprise_id":
            template.enterprise_id,
            "source": {
                "enterprise_id": template.enterprise_id,
                "teamName": template.team_name,
                "regionName": template.region_name,
                "appID": template.app_id
            },
            "app_name":
            template.app_name,
            "template":
            self.version_data(row.version),
            "reason":
            row.reason,
            "status":
            row.status,
            "publication_status":
            row.publication_status,
            "destination":
            row.destination,
            "applicant_id":
            str(row.applicant_id),
            "applicant_name":
            row.applicant_name,
            "submitted_at":
            row.submitted_at.isoformat(),
            "reviewer_name":
            row.reviewer_name,
            "review_comment":
            row.comment,
            "reviewed_at":
            row.reviewed_at.isoformat() if row.reviewed_at else "",
            "actions": [{
                "action": "submit",
                "user_name": row.applicant_name,
                "time": row.submitted_at.isoformat()
            }] + ([{
                "action": row.status,
                "user_name": row.reviewer_name,
                "time": row.reviewed_at.isoformat(),
                "comment": row.comment
            }] if row.reviewed_at else [])
        }

    def task_data(self, task):
        target = copy.deepcopy(task.payload.get("target"))
        if target and task.result.get("app_id"):
            target["app_id"] = task.result["app_id"]
        return {
            "id":
            str(task.id),
            "enterprise_id":
            task.template.enterprise_id,
            "template_id":
            str(task.version_id or ""),
            "version":
            task.version.version if task.version else "",
            "template_name":
            task.template.name,
            "kind":
            task.kind,
            "status":
            task.status,
            "target":
            target,
            "listing_id":
            task.payload.get("listing_id", ""),
            "user_id":
            str(task.actor_id),
            "user_name":
            task.actor_name,
            "created_at":
            task.created_at.isoformat(),
            "error":
            task.error,
            "download_url":
            "/console/delivery-tasks/{}/download".format(task.id)
            if task.kind == "offline" and task.status == "succeeded" and not task.version.deleted_at else ""
        }
