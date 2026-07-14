from typing import Any

from console.models.main import RegionConfig
from console.services.app_actions import app_manage_service
from console.services.enterprise_first_deploy_service import enterprise_first_deploy_service
from console.services.region_resource_processing import region_resource
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import RegionApp, Tenants

region_api = RegionInvokeApi()


class YamlK8SResource(object):
    def yaml_k8s_resource_name(
        self,
        event_id: str,
        app_id: int,
        tenant_id: str,
        namespace: str,
        region_id: str,
        enterprise_id: str,
    ) -> Any:
        region_app = RegionApp.objects.filter(app_id=app_id)
        if region_app:
            region_app_id = region_app[0].region_app_id
            data = {"event_id": event_id, "region_app_id": region_app_id, "tenant_id": tenant_id, "namespace": namespace}
            _, body = region_api.yaml_resource_name(enterprise_id, region_id, data)
            yaml_resource = body["bean"]  # type: ignore[index]
            app_resource = yaml_resource.pop("app_resource")
            body["bean"] = {"app_resource": app_resource, "error_yaml": yaml_resource}  # type: ignore[index]
            return body
        return []

    def yaml_k8s_resource_detailed(
        self,
        event_id: str,
        app_id: int,
        tenant_id: str,
        namespace: str,
        region_id: str,
        enterprise_id: str,
    ) -> Any:
        region_app = RegionApp.objects.filter(app_id=app_id)
        if region_app:
            region_app_id = region_app[0].region_app_id
            data = {
                "event_id": event_id,
                "region_app_id": region_app_id,
                "tenant_id": tenant_id,
                "namespace": namespace,
            }
            _, body = region_api.yaml_resource_detailed(enterprise_id, region_id, data)
            return body["bean"]  # type: ignore[index]
        return []

    def yaml_k8s_resource_import(
        self,
        event_id: str,
        app_id: int,
        tenant: Tenants,
        namespace: str,
        region: RegionConfig,
        enterprise_id: str,
        user: Any,
    ) -> Any:
        app = RegionApp.objects.filter(app_id=app_id)
        if app:
            app_obj: RegionApp = app[0]
            tracker = enterprise_first_deploy_service.safe_begin_deploy_tracking(
                enterprise_id=enterprise_id,
                tenant_name=getattr(tenant, "tenant_name", ""),
                region_name=region.region_name,
                deploy_type=enterprise_first_deploy_service.DEPLOY_TYPE_YAML,
                operator=getattr(user, "nick_name", ""),
                source_language="yaml",
                trigger="yaml_import",
                app_context={
                    "app_id": app_id,
                    "component_count": 0,
                },
                workload_context=enterprise_first_deploy_service.build_yaml_workload_context(event_id=event_id))
            data = {
                "event_id": event_id,
                "region_app_id": app_obj.region_app_id,
                "tenant_id": tenant.tenant_id,
                "namespace": namespace,
            }
            try:
                _, body = region_api.yaml_resource_import(enterprise_id, region.region_id, data)
                ac = body["bean"]  # type: ignore[index]
                region_resource.create_k8s_resources(ac["k8s_resources"], app_id)
                service_ids = region_resource.create_components(
                    app_obj, ac["component"], tenant, region.region_name, user.user_id)
                code, msg, services = app_manage_service.batch_action(region.region_name, tenant, user, "deploy", service_ids,
                                                                      None, None)
                if code != 200:
                    enterprise_first_deploy_service.safe_mark_failure(
                        tracker, reason=msg, failure_stage=enterprise_first_deploy_service.FAILURE_STAGE_BUILD)
                else:
                    event_ids, tracked_service_ids, service_aliases = \
                        enterprise_first_deploy_service.extract_deploy_event_context(services)
                    deploy_failure_reasons = enterprise_first_deploy_service.extract_deploy_failure_reasons(services)
                    if deploy_failure_reasons:
                        enterprise_first_deploy_service.safe_mark_failure(
                            tracker,
                            reason="; ".join(deploy_failure_reasons),
                            failure_stage=enterprise_first_deploy_service.FAILURE_STAGE_BUILD)
                    elif event_ids:
                        enterprise_first_deploy_service.safe_bind_events(tracker,
                                                                         event_ids,
                                                                         service_ids=tracked_service_ids,
                                                                         service_aliases=service_aliases)
                    else:
                        enterprise_first_deploy_service.safe_mark_success(tracker)
                return body["bean"]  # type: ignore[index]
            except Exception as exc:
                enterprise_first_deploy_service.safe_mark_failure(
                    tracker, reason=str(exc), failure_stage=enterprise_first_deploy_service.FAILURE_STAGE_PREFLIGHT)
                raise
        return []


yaml_k8s_resource = YamlK8SResource()
