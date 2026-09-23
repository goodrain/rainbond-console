"""Read-only projections for cleanup inventory. Never export full application config."""
import hashlib
import hmac
import json
import re
import time


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
    return "{} ({})".format(label, identifier) if label else identifier


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
        for section in ("apps", "plugins"):
            components = template.get(section, [])
            if not isinstance(components, list):
                raise ValueError("invalid template section")
            for component in components:
                if not isinstance(component, dict):
                    raise ValueError("invalid component")
                delivery = component.get("service_image") or {}
                for image in (component.get("share_image"), component.get("image"),
                              delivery.get("image_url") if isinstance(delivery, dict) else None):
                    clean = _image(image)
                    if clean:
                        images.add(clean)
        result["images"] = sorted(images)
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
        if number != current and version.get("final_status") == "success":
            rank += 1
            event_id = version.get("event_id")
            checkpoints = inspection.get("checkpoints") or {}
            if (component.get("retirement_references_complete") is True and component.get("snapshot_referenced") is False
                    and inspection.get("protocol") == 1 and inspection.get("current_version") == current
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


def snapshot_reference_resource(row, region):
    """Export retained snapshot image references, never backup config or secrets.

    A missing build image, plugin relation or custom Kubernetes override prevents
    this source from claiming complete coverage; known images still protect data.
    """
    result = _base("snapshot-reference:{}:{}".format(region, row["ID"]), region, "templates",
                   "application_snapshot", "保留快照 / {}".format(row["ID"]), "")
    result["source"] = "platform_snapshot_references"
    images = set()
    complete = True
    try:
        snapshot = json.loads(row.get("snapshot") or "")
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("components"), list):
            raise ValueError()
        group = snapshot.get("component_group") or {}
        if not isinstance(group, dict):
            raise ValueError()
        name = _display_name(group.get("group_name"), "保留快照")
        version = _display_name(group.get("group_version"), str(row["ID"]))
        result["name"] = "{} / {}".format(name, version)
        for component in snapshot["components"]:
            if not isinstance(component, dict) or not isinstance(component.get("service_base"), dict):
                raise ValueError()
            base = component["service_base"]
            if not isinstance(base.get("service_id"), str) or not base["service_id"]:
                raise ValueError()
            source = component.get("service_source") or {}
            if not isinstance(source, dict):
                raise ValueError()
            found = False
            for value in (base.get("image"), source.get("image")):
                if value in (None, ""):
                    continue
                image = _image(value)
                if image:
                    images.add(image)
                    found = True
                else:
                    complete = False
            if not found and base.get("service_source") != "third_party":
                complete = False
            if component.get("service_plugin_relation") or component.get("component_k8s_attributes"):
                complete = False
    except (ValueError, TypeError):
        complete = False
    result["images"] = sorted(images)
    result["observed"] = complete
    result["protection"] = "referenced" if complete else "reference_unknown"
    result["usageStatus"] = "referenced" if images else "unknown"
    return result
