"""Read-only projections for cleanup inventory. Never export full application config."""
import hashlib
import hmac
import json
import re
import time

import yaml


def verify_source_request(method, path, enterprise, region, timestamp, signature, key, now=None):
    if method != "GET" or not key or len(key) < 32:
        return False
    if not isinstance(timestamp, str) or not re.fullmatch(r"[0-9]{1,12}", timestamp):
        return False
    if not isinstance(signature, str) or not re.fullmatch(r"[a-f0-9]{64}", signature):
        return False
    try:
        issued = int(timestamp)
    except (ValueError, TypeError):
        return False
    if abs(int(time.time() if now is None else now) - issued) > 120:
        return False
    raw = "\n".join(["cleanup-inventory-v1", method, path, enterprise, region, str(issued)])
    expected = hmac.new(key, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return isinstance(signature, str) and hmac.compare_digest(expected, signature)


def _image(value):
    if not isinstance(value, str) or "://" in value or len(value) > 2048:
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*(?:@sha256:[a-fA-F0-9]{64})?", value):
        return None
    return value


def _base(identifier, region, category, kind, name, owner):
    return {"id": identifier, "cluster": region, "category": category, "resourceType": kind,
            "name": name, "owner": owner, "sizeBytes": 0, "sizeKnown": False,
            "observed": True, "unusedSince": None, "protection": "reference_unknown",
            "usageStatus": "unknown", "decision": "protected", "images": [], "actions": []}


def _display_name(*values):
    return next((value.strip() for value in values if isinstance(value, str) and value.strip()), "")


def failed_scope_label(row):
    identifier = str(row.get("id") or row.get("service_id") or "")
    name = _display_name(row.get("name"), row.get("service_cname"), row.get("service_alias"))
    owner = _display_name(row.get("owner_name"))
    label = " / ".join(value for value in (owner, name) if value)
    label = "{} ({})".format(label, identifier) if label else identifier
    explanations = {
        "snapshot_invalid_structure": "快照结构无法识别",
        "snapshot_missing_runtime_image": "未记录可核对的镜像",
        "snapshot_plugin_reference_unknown": "插件版本镜像引用不完整",
        "snapshot_k8s_override_unknown": "存在尚未解析的 K8s 覆盖",
    }
    reasons = [explanations[code] for code in (row.get("incompleteReasons") or [])
               if isinstance(code, str) and code in explanations]
    return "{}：{}".format(label, "；".join(reasons)) if reasons else label


def _embedded_workload_images(resources):
    images = set()
    if not isinstance(resources, list) or len(resources) > 1000:
        return images, False
    paths = {
        "Pod": ("spec", ),
        "Deployment": ("spec", "template", "spec"),
        "StatefulSet": ("spec", "template", "spec"),
        "DaemonSet": ("spec", "template", "spec"),
        "ReplicaSet": ("spec", "template", "spec"),
        "ReplicationController": ("spec", "template", "spec"),
        "Job": ("spec", "template", "spec"),
        "CronJob": ("spec", "jobTemplate", "spec", "template", "spec"),
    }
    non_workloads = {
        "Namespace", "Service", "Secret", "ConfigMap", "Ingress",
        "PersistentVolumeClaim", "PersistentVolume", "ServiceAccount", "Role",
        "RoleBinding", "ClusterRole", "ClusterRoleBinding", "NetworkPolicy",
        "ResourceQuota", "LimitRange", "PodDisruptionBudget",
        "HorizontalPodAutoscaler"
    }
    complete = True
    for resource in resources:
        try:
            content = resource.get("content") if isinstance(resource,
                                                            dict) else None
            if not isinstance(content,
                              str) or not content or len(content) > 1048576:
                raise ValueError()
            for document in yaml.safe_load_all(content):
                if not isinstance(document, dict):
                    raise ValueError()
                kind = document.get("kind")
                if kind in non_workloads:
                    continue
                if kind not in paths:
                    raise ValueError()
                spec = document
                for field in paths[kind]:
                    spec = spec[field]
                    if not isinstance(spec, dict):
                        raise ValueError()
                for field in ("containers", "initContainers",
                              "ephemeralContainers"):
                    containers = spec.get(field, [])
                    if not isinstance(containers, list) or (
                            field == "containers" and not containers):
                        raise ValueError()
                    for container in containers:
                        image = _image(container.get("image")) if isinstance(
                            container, dict) else None
                        if not image:
                            raise ValueError()
                        images.add(image)
        except (ValueError, TypeError, KeyError, yaml.YAMLError):
            complete = False
    return images, complete


def template_resource(row, region, hidden):
    result = _base("template:{}:{}".format(region, row["ID"]), region, "templates",
                   "application_snapshot" if hidden else "template_version",
                   "{} / {}".format(_display_name(row.get("app_name"), row.get("app_id")), row.get("version", "")),
                   "")
    result["source"] = "platform_templates"
    try:
        template = json.loads(row.get("app_template") or "{}")
        if not isinstance(template, dict):
            raise ValueError("invalid template")
        name = _display_name(template.get("group_name"), template.get("app_name"), row.get("app_name"), row.get("app_id"))
        result["name"] = "{} / {}".format(name, row.get("version", ""))
        images = set()
        size_images = set()
        size_complete = True
        for section in ("apps", "plugins"):
            components = template.get(section, [])
            if not isinstance(components, list):
                raise ValueError("invalid template section")
            for component in components:
                if not isinstance(component, dict):
                    raise ValueError("invalid component")
                # Match template installation precedence. Other image fields remain
                # reference evidence, but are not additional installed artifacts.
                installed = _image(component.get("share_image", component.get("image")))
                if installed:
                    size_images.add(installed)
                else:
                    size_complete = False
                delivery = component.get("service_image") or {}
                for image in (component.get("share_image"), component.get("image"),
                              delivery.get("image_url") if isinstance(delivery, dict) else None):
                    clean = _image(image)
                    if clean:
                        images.add(clean)
        embedded, embedded_complete = _embedded_workload_images(template.get("k8s_resources", []))
        images.update(embedded)
        size_images.update(embedded)
        if not embedded_complete:
            result["observed"] = False
            size_complete = False
        result["images"] = sorted(images)
        result["sizeImages"] = sorted(size_images) if size_complete else []
        result["usageStatus"] = "referenced" if images else "unknown"
    except (ValueError, TypeError):
        result["observed"] = False
    if result["observed"] and row.get("retirement"):
        result["retirement"] = row["retirement"]
    # Creation/update time is intentionally never copied into unusedSince.
    return result


def version_resources(component, payload, region):
    if not isinstance(payload, dict) or not isinstance(payload.get("list"), list):
        raise ValueError("incomplete version inventory")
    rows = []
    current = payload.get("deploy_version")
    inspection = payload.get("retirement") or {}
    rank = 0
    for version in payload["list"]:
        if not isinstance(version, dict) or not version.get("build_version"):
            raise ValueError("invalid build record")
        number = str(version["build_version"])
        name = component.get("service_cname") or component.get("service_alias") or component["service_id"]
        result = _base("version:{}:{}:{}".format(region, component["service_id"], number), region,
                       "rollbacks", "build_version", "{} / {}".format(name, number),
                       _display_name(component.get("owner_name"), name, component["service_id"]))
        result["source"] = "platform_versions"
        result["usageStatus"] = "current_deployment" if number == current else "history_unverified"
        if number == current:
            result["protection"] = "referenced"
        images = [_image(version.get("image_name"))]
        if version.get("delivered_type") == "image":
            images.append(_image(version.get("delivered_path")))
        result["images"] = sorted(set(image for image in images if image))
        runtime_image = _image(version.get("image_name"))
        if not runtime_image and version.get("delivered_type") == "image":
            runtime_image = _image(version.get("delivered_path"))
        result["sizeImages"] = [runtime_image] if runtime_image else []
        if number != current and version.get("final_status") == "success":
            rank += 1
            event_id = version.get("event_id")
            checkpoints = inspection.get("checkpoints") or {}
            if inspection.get("protocol") != 2:
                result["protection"] = "core_upgrade_required"
            if (component.get("retirement_references_complete") is True and component.get("snapshot_referenced") is False
                    and inspection.get("protocol") == 2 and inspection.get("current_version") == current
                    and inspection.get("active_operation") is False and current and event_id in checkpoints
                    and version.get("delivered_type") == "image" and result["images"]):
                result["retirement"] = {"protocol": 1, "kind": "build_version", "rank": rank, "expected": {
                    "service_id": component["service_id"], "version": number, "current_version": current,
                    "event_id": event_id, "image": _image(version.get("image_name")) or _image(version.get("delivered_path")),
                    "activation_revision": checkpoints[event_id],
                }}
        rows.append(result)
    return rows


def deployment_resource(row, region):
    """Project saved evidence only; never invoke upgrade state synchronization."""
    record_type = row.get("app_upgrade_record__record_type")
    kind = "recorded_rollback" if record_type == "rollback" else "recorded_upgrade"
    result = _base("deployment:{}:{}".format(region, row["ID"]), region, "rollbacks", kind,
                   "{} / {} → {}".format(row.get("service_cname") or row["service_id"],
                                         row.get("app_upgrade_record__old_version") or "—",
                                         row.get("app_upgrade_record__version") or "—"),
                   _display_name(row.get("owner_name"), row.get("service_cname"), row["service_id"]))
    statuses = {1: "pending", 2: "upgrading", 3: "upgraded", 4: "rolling_back", 5: "rolled_back",
                6: "partial_upgrade", 7: "partial_rollback", 8: "upgrade_failed", 9: "rollback_failed", 10: "deploy_failed"}
    result["recordStatus"] = statuses.get(row.get("status"), "unknown")
    result["source"] = "platform_deployments"
    result["usageStatus"] = "referenced" if row.get("status") in (1, 2, 4) else "history_unverified"
    result["references"] = [{"key": "app-record:{}".format(row["app_upgrade_record_id"]),
                             "kind": "application_record", "name": "{} / {} → {}".format(
                                 _display_name(row.get("app_upgrade_record__group_name"), row.get("owner_name"),
                                               str(row["app_upgrade_record_id"])),
                                 row.get("app_upgrade_record__old_version") or "—",
                                 row.get("app_upgrade_record__version") or "—")}]
    return result


# These attributes are decoded by the core into scheduling types only; none
# can add or replace a container image. Unknown attributes remain incomplete.
SNAPSHOT_SCHEDULING_ATTRIBUTES = frozenset(("affinity", "nodeSelector", "tolerations"))


def snapshot_reference_resource(row, region):
    """Project saved image evidence without exporting configuration or secrets."""
    result = _base("snapshot-reference:{}:{}".format(region, row["ID"]), region, "templates",
                   "application_snapshot", "保留快照 / {}".format(row["ID"]), "")
    result["source"] = "platform_snapshot_references"
    images = set()
    issues = set()
    try:
        snapshot = json.loads(row.get("snapshot") or "")
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("components"), list):
            raise ValueError()
        group = snapshot.get("component_group")
        if group is None:
            group = {}
        if not isinstance(group, dict):
            issues.add("snapshot_invalid_structure")
            group = {}
        name = _display_name(group.get("group_name"), "保留快照")
        version = _display_name(group.get("group_version"), str(row["ID"]))
        result["name"] = "{} / {}".format(name, version)
        for component in snapshot["components"]:
            if not isinstance(component, dict) or not isinstance(component.get("service_base"), dict):
                issues.add("snapshot_invalid_structure")
                continue
            base = component["service_base"]
            if not isinstance(base.get("service_id"), str) or not base["service_id"]:
                issues.add("snapshot_invalid_structure")
            source = component.get("service_source")
            if source is None:
                source = {}
            if not isinstance(source, dict):
                issues.add("snapshot_invalid_structure")
                source = {}
            found = False
            for value in (base.get("image"), source.get("image")):
                if value in (None, ""):
                    continue
                image = _image(value)
                if image:
                    images.add(image)
                    found = True
                else:
                    issues.add("snapshot_missing_runtime_image")
            if not found and base.get("service_source") != "third_party":
                issues.add("snapshot_missing_runtime_image")
            relations = component.get("service_plugin_relation")
            if relations is not None and (not isinstance(relations, list) or relations):
                issues.add("snapshot_plugin_reference_unknown")
            attributes = component.get("component_k8s_attributes")
            if attributes is None:
                attributes = []
            if not isinstance(attributes, list) or any(
                    not isinstance(attribute, dict)
                    or not isinstance(attribute.get("name"), str)
                    or attribute["name"] not in SNAPSHOT_SCHEDULING_ATTRIBUTES for attribute in attributes):
                issues.add("snapshot_k8s_override_unknown")
    except (ValueError, TypeError):
        issues.add("snapshot_invalid_structure")
    result["images"] = sorted(images)
    result["incompleteReasons"] = sorted(issues)
    result["observed"] = not issues
    result["protection"] = "reference_unknown" if issues else "referenced"
    result["usageStatus"] = "referenced" if images else "unknown"
    return result
