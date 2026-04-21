def resolve_vm_boot_source(tenant, image_name, image_url, source_uri=""):
    image_url = str(image_url or "").strip()
    source_uri = str(source_uri or "").strip()

    if image_url and not requires_vm_source_build(image_url):
        return {
            "image": image_url,
            "vm_url": "",
        }

    boot_source = image_url or source_uri
    if not requires_vm_source_build(boot_source):
        return {
            "image": image_url,
            "vm_url": "",
        }
    return {
        "image": build_vm_runtime_image_name(tenant, image_name),
        "vm_url": boot_source,
    }


def requires_vm_source_build(image_url):
    value = str(image_url or "").strip().lower()
    return value.startswith("http://") or value.startswith("https://") or value.startswith("/grdata/")


def build_vm_runtime_image_name(tenant, image_name):
    namespace = (
        getattr(tenant, "namespace", "") or
        getattr(tenant, "tenant_name", "") or
        getattr(tenant, "tenant_id", "") or
        "vm"
    )
    image_name = str(image_name or "vm-image")
    return "{}:{}".format(namespace, image_name)
