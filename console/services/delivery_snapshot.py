"""Explicit one-way copy of saved snapshot content; never updates snapshot history."""
import copy
import json
from console.services.delivery_manifest import DeliveryError


def snapshot_source(version):
    try:
        source = json.loads(version.app_template)
    except (ValueError, TypeError):
        raise DeliveryError("快照内容不可用，请选择其他快照", 409)
    if not isinstance(source, dict) or not isinstance(source.get("apps"), list):
        raise DeliveryError("快照缺少组件信息", 409)
    application = source.get("application") or {"name": source.get("group_name", ""), "logo": "", "description": ""}
    # Copy deployable declarations only; snapshot/rollback and old publication IDs stay in history.
    source = {key: copy.deepcopy(value) for key, value in source.items() if key in (
        "template_version", "apps", "plugins", "governance_mode", "k8s_resources", "app_config_groups",
        "ingress_http_routes", "arch", "application")}
    source["application"] = copy.deepcopy(application)
    source["source_snapshot"] = {"version_id": str(version.ID), "version": version.version}
    for component in source["apps"]:
        image = component.get("share_image") or (component.get("service_image") or {}).get("image_url")
        slug = component.get("share_slug_path") or (component.get("service_slug") or {}).get("slug_path")
        artifact = component.get("delivered_path") or image or slug or ""
        kind = component.get("delivered_type") or ("image" if image else "slug" if slug else "")
        component.update(delivered_path=artifact, delivered_type=kind,
                         delivery_available=bool(artifact and kind == "image"))
        component.setdefault("build_version", component.get("deploy_version", ""))
    for plugin in source.get("plugins", []):
        image = plugin.get("share_image") or (plugin.get("plugin_image") or {}).get("image_url")
        plugin.update(built_image=image or "", delivery_available=bool(image))
    return source
