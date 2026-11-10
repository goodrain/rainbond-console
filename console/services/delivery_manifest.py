"""Pure template preparation and comparison; never reads or creates snapshots."""
import copy
import hashlib
import json
import re
from urllib.parse import urlsplit, urlunsplit

SENSITIVE = re.compile(r"password|passwd|token|secret|private.?key|api.?key|access.?key|credential|authorization", re.I)


class DeliveryError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def clean_source(value):
    parts = urlsplit(value or "")
    if parts.scheme and parts.netloc:
        return urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, "", ""))
    return value or ""


def canonical_spec(value):
    unordered = {
        "service_env_map_list", "service_connect_info_map_list", "dep_service_map_list", "port_map_list",
        "service_volume_map_list", "mnt_relation_list", "service_related_plugin_config", "app_config_groups", "component_keys",
        "plugins"
    }
    if isinstance(value, list):
        return [canonical_spec(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        result[key] = canonical_spec(item)
        if key in unordered and isinstance(result[key], list):
            result[key].sort(key=lambda entry: json.dumps(entry, sort_keys=True))
    return result


def sensitive_env(env):
    if env.get("is_sensitive") or SENSITIVE.search(env.get("attr_name", "")):
        return True
    try:
        return bool(urlsplit(str(env.get("attr_value", ""))).password)
    except ValueError:
        return False


def public_manifest(value):
    """Only configuration definitions leave the server; transport credentials never do."""
    if isinstance(value, list):
        return [public_manifest(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key in ("service_image", "service_slug", "plugin_image", "registry_auth", "vm_image_token") or SENSITIVE.search(key):
            continue
        result[key] = clean_source(item) if key in ("git_url", "source") else public_manifest(item)
    if value.get("attr_name") and (sensitive_env(value)):
        result.update(attr_value="", is_sensitive=True, required_on_install=True)
    return result


def baseline(manifest):
    # Full declarative data, including private values as server-only digests.
    components = []
    for component in manifest.get("apps", []):
        spec = copy.deepcopy(component)
        for key in ("need_share", "share_image", "share_slug_path", "service_image", "service_slug", "creater", "tenant_id"):
            spec.pop(key, None)
        components.append({
            "service_id": component["service_id"],
            "name": component["service_cname"],
            "digest": digest(canonical_spec(spec))
        })
    application_spec = {key: value for key, value in manifest.items() if key != "apps"}
    return {
        "components": sorted(components, key=lambda item: item["service_id"]),
        "application_digest": digest(canonical_spec(application_spec))
    }


def compare(before, after):
    old = {item["service_id"]: item for item in before["components"]}
    new = {item["service_id"]: item for item in after["components"]}
    details = []
    for key in sorted(set(old) | set(new)):
        kind = "added" if key not in old else "removed" if key not in new else "updated"
        if kind != "updated" or old[key]["digest"] != new[key]["digest"]:
            details.append({
                "service_id": key,
                "name": (new.get(key) or old[key])["name"],
                "type": kind,
                "fields": ["configuration"] if kind == "updated" else []
            })
    if before["application_digest"] != after["application_digest"] and not details:
        details = [{"service_id": "application", "name": "应用配置", "type": "updated", "fields": ["configuration"]}]
    return {
        "status": "changed" if details else "unchanged",
        "details": details,
        "summary": {
            kind + "_count": sum(item["type"] == kind for item in details)
            for kind in ("added", "updated", "removed")
        }
    }


def prepare(source, payload, template_id):
    name, version = str(payload.get("template_name", "")).strip(), str(payload.get("version", "")).strip()
    if not name or len(name) > 64 or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", version):
        raise DeliveryError("请填写模板名称和正确的版本号")
    description = str(payload.get("description", ""))
    if len(description) > 20000:
        raise DeliveryError("版本说明不能超过20000个字符")
    ids = payload.get("service_ids", [])
    available = {item["service_id"]: item for item in source.get("apps", [])}
    if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids) or any(key not in available for key in ids):
        raise DeliveryError("所选组件缺少成功构建产物，或已经变动，请刷新后重试")
    overrides = {item["service_id"]: item for item in payload.get("component_overrides", [])}
    selected = {available[key]["service_share_uuid"] for key in ids}
    if any(available[key].get("delivered_type") == "slug" for key in ids):
        raise DeliveryError("所选组件包含旧版源码包产物，请先使用镜像构建，再创建交付模板")
    manifest = copy.deepcopy(source)
    if any(not available[key].get("delivery_available", True) for key in ids):
        raise DeliveryError("所选组件没有成功构建产物，请先完成构建")
    manifest.update({
        "group_key": str(template_id),
        "group_name": name,
        "group_version": version,
        "annotations": {
            "version_info": description,
            "describe": str(payload.get("template_description", "")).strip(),
            "logo": str(payload.get("logo", "")).strip()
        }
    })
    manifest["apps"] = []
    for key in ids:
        component = copy.deepcopy(available[key])
        if any(dep["dep_service_key"] not in selected for dep in component.get("dep_service_map_list", [])):
            raise DeliveryError("请同时选择组件依赖的其他应用组件")
        if any(dep["service_share_uuid"] not in selected for dep in component.get("mnt_relation_list", [])):
            raise DeliveryError("请同时选择提供共享存储的组件")
        override = overrides.get(key, {})
        variables = component.get("service_env_map_list", [])
        incoming = override.get("service_env_map_list", variables)
        if len(incoming) != len(variables) or {env["attr_name"] for env in incoming} != {env["attr_name"] for env in variables}:
            raise DeliveryError("环境变量只允许修改值，不能添加、删除或修改名称")
        values = {env["attr_name"]: env.get("attr_value", "") for env in incoming}
        for env in variables:
            if sensitive_env(env):
                env.update(attr_value="", is_sensitive=True, required_on_install=True)
            else:
                env["attr_value"] = str(values[env["attr_name"]])
        if not component.get("vm") and component.get("extend_method") != "vm":
            scale = component.setdefault("extend_method_map", {})
            supplied = override.get("extend_method_map", {})
            daemonset = component.get("extend_method") in ("daemonset",
                                                           "daemon_set") or component.get("service_type") == "daemonset"
            fields = ("init_memory", "container_cpu") if daemonset else ("min_node", "max_node", "step_node", "init_memory",
                                                                         "container_cpu")
            for field in fields:
                value = supplied.get(field, scale.get(field))
                if type(value) is not int or value < (0 if field in ("init_memory", "container_cpu") else 1):
                    raise DeliveryError("组件资源与实例配置无效")
                scale[field] = value
            if "max_node" in fields and scale["max_node"] < scale["min_node"]:
                raise DeliveryError("最大实例数不能小于最小实例数")
            if component.get("extend_method") == "singleton" and scale["max_node"] != 1:
                raise DeliveryError("单实例组件只能配置一个实例")
            if daemonset:
                for field in ("min_node", "max_node", "step_node"):
                    scale.pop(field, None)
            component["memory"], component["cpu"] = scale["init_memory"], scale["container_cpu"]
        manifest["apps"].append(component)
    selected_keys = {available[key]["service_key"] for key in ids}
    manifest["ingress_http_routes"] = [
        route for route in manifest.get("ingress_http_routes", []) if route.get("component_key") in selected_keys
    ]
    groups = []
    for group in manifest.get("app_config_groups", []):
        group["component_keys"] = [key for key in group.get("component_keys", []) if key in selected_keys]
        if group["component_keys"]:
            groups.append(group)
    manifest["app_config_groups"] = groups
    used_plugins = {
        config["plugin_key"]
        for component in manifest["apps"]
        for config in component.get("service_related_plugin_config", [])
    }
    manifest["plugins"] = [plugin for plugin in manifest.get("plugins", []) if plugin["plugin_key"] in used_plugins]
    if payload.get("is_platform_plugin"):
        plugin = payload.get("plugin", {})
        if not all(plugin.get(field) for field in ("plugin_id", "plugin_name", "plugin_type", "entry_path")):
            raise DeliveryError("请填写完整的平台插件配置")
        manifest["platform_plugin"] = {**copy.deepcopy(plugin), "is_platform_plugin": True}
    return manifest


def template_metadata(payload):
    name = str(payload.get("template_name", "")).strip()
    description = str(payload.get("template_description", "")).strip()
    logo = str(payload.get("logo", "")).strip()
    if not name or len(name) > 64:
        raise DeliveryError("请填写64字以内的模板名称")
    if len(description) > 400 or len(logo) > 2048:
        raise DeliveryError("应用描述不能超过400字，Logo 地址不能超过2048字符")
    if logo:
        parts = urlsplit(logo)
        if parts.username or parts.password or not (logo.startswith("/") or parts.scheme in ("http", "https")):
            raise DeliveryError("请使用上传后的 Logo 图片地址")
    return {"name": name, "description": description, "logo": logo}


def retain_artifacts(manifest):
    """Use already-built immutable artifacts; this never queues a copy/build/snapshot job."""
    for component in manifest["apps"]:
        image = component.get("delivered_path")
        if not image or component.get("delivered_type") != "image":
            raise DeliveryError("组件缺少可引用的已构建镜像，请先完成构建")
        component["share_image"] = image
        for disk in (component.get("vm") or {}).get("disk_layout", []):
            if str(disk.get("disk_role", "")).lower() == "root":
                disk.update(image=image, source_type="http-artifact")
                disk.pop("source_uri", None)
    for plugin in manifest.get("plugins", []):
        if not plugin.get("built_image") or not plugin.get("delivery_available"):
            raise DeliveryError("所选组件的插件缺少成功构建镜像，请先完成插件构建")
        plugin["share_image"] = plugin["built_image"]
    return manifest
