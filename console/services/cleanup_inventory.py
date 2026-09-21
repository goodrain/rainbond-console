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
                   _display_name(row.get("owner_name"), row.get("share_team")))
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
    # Creation/update time is intentionally never copied into unusedSince.
    return result


def version_resources(component, payload, region):
    if not isinstance(payload, dict) or not isinstance(payload.get("list"), list):
        raise ValueError("incomplete version inventory")
    rows = []
    current = payload.get("deploy_version")
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
