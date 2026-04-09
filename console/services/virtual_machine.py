import json

from console.repositories.k8s_attribute import k8s_attribute_repo
from console.repositories.virtual_machine import vm_repo
from www.apiclient.regionapi import RegionInvokeApi

region_api = RegionInvokeApi()

VM_EXTENSION_ENV_NAMES = {
    "ES_VM_NETWORK_MODE",
    "ES_VM_NETWORK_NAME",
    "ES_VM_FIXED_IP",
    "ES_VM_GPU_ENABLED",
    "ES_VM_GPU_RESOURCES",
    "ES_VM_USB_ENABLED",
    "ES_VM_USB_RESOURCES",
}


class VirtualMachineService(object):
    def list_vm_image(self, tenant_id):
        component_list = vm_repo.get_vm_images_by_tenant_id(tenant_id)
        return component_list

    def get_vm_capabilities(self, region_name, tenant_name):
        _, body = region_api.get_vm_capabilities(region_name, tenant_name)
        return body.get("bean", {})

    def clone_vm_image(self, tenant_id, source_name, target_name):
        source = vm_repo.get_vm_image_instance_by_tenant_id_and_name(tenant_id, source_name)
        if not source:
            return None
        return vm_repo.create_vm_image(
            tenant_id=tenant_id,
            name=target_name,
            image_url=source.image_url
        )

    def save_vm_runtime_config(self, tenant_id, service_id, runtime_config):
        self.validate_vm_runtime_config(runtime_config)
        envs = self._build_vm_extension_envs(runtime_config)
        attrs = k8s_attribute_repo.get_by_component_id_name(service_id, "env")
        existing_attribute_value = attrs[0].attribute_value if attrs and len(attrs) > 0 else ""
        merged_envs = self._merge_vm_extension_envs(existing_attribute_value, envs)
        attribute_value = json.dumps(merged_envs)
        if attrs and len(attrs) > 0:
            k8s_attribute_repo.update(service_id, "env", attribute_value=attribute_value)
        else:
            k8s_attribute_repo.create(
                tenant_id=tenant_id,
                component_id=service_id,
                name="env",
                save_type="json",
                attribute_value=attribute_value)

    def validate_vm_runtime_config(self, runtime_config):
        network_mode = runtime_config.get("network_mode") or "random"
        if network_mode == "fixed":
            if not runtime_config.get("network_name"):
                raise ValueError("固定 IP 模式必须选择业务网络")
            if not runtime_config.get("fixed_ip"):
                raise ValueError("固定 IP 模式必须填写固定 IP")

        gpu_enabled = self._as_bool(runtime_config.get("gpu_enabled"))
        if gpu_enabled and not self._as_list(runtime_config.get("gpu_resources")):
            raise ValueError("GPU 已开启时必须选择 GPU 资源")

        usb_enabled = self._as_bool(runtime_config.get("usb_enabled"))
        if usb_enabled and not self._as_list(runtime_config.get("usb_resources")):
            raise ValueError("USB 透传已开启时必须选择 USB 资源")

    def _build_vm_extension_envs(self, runtime_config):
        envs = []
        network_mode = runtime_config.get("network_mode") or "random"
        envs.append({
            "name": "ES_VM_NETWORK_MODE",
            "value": network_mode
        })

        if network_mode == "fixed":
            if runtime_config.get("network_name"):
                envs.append({
                    "name": "ES_VM_NETWORK_NAME",
                    "value": runtime_config.get("network_name")
                })
            if runtime_config.get("fixed_ip"):
                envs.append({
                    "name": "ES_VM_FIXED_IP",
                    "value": runtime_config.get("fixed_ip")
                })

        gpu_enabled = self._as_bool(runtime_config.get("gpu_enabled"))
        gpu_resources = self._as_list(runtime_config.get("gpu_resources"))
        if gpu_enabled and gpu_resources:
            envs.append({
                "name": "ES_VM_GPU_ENABLED",
                "value": "true"
            })
            envs.append({
                "name": "ES_VM_GPU_RESOURCES",
                "value": json.dumps(gpu_resources)
            })

        usb_enabled = self._as_bool(runtime_config.get("usb_enabled"))
        usb_resources = self._as_list(runtime_config.get("usb_resources"))
        if usb_enabled and usb_resources:
            envs.append({
                "name": "ES_VM_USB_ENABLED",
                "value": "true"
            })
            envs.append({
                "name": "ES_VM_USB_RESOURCES",
                "value": json.dumps(usb_resources)
            })

        return envs

    def _merge_vm_extension_envs(self, existing_attribute_value, envs):
        merged = []
        for env in self._parse_env_attribute_value(existing_attribute_value):
            if env.get("name") in VM_EXTENSION_ENV_NAMES:
                continue
            merged.append(env)
        merged.extend(envs)
        return merged

    def _parse_env_attribute_value(self, attribute_value):
        if not attribute_value:
            return []
        try:
            parsed = json.loads(attribute_value)
        except (TypeError, ValueError):
            return []

        if isinstance(parsed, dict):
            return [{
                "name": key,
                "value": value
            } for key, value in parsed.items()]

        if not isinstance(parsed, list):
            return []

        envs = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("key")
            if not name:
                continue
            envs.append({
                "name": name,
                "value": item.get("value", "")
            })
        return envs

    def _as_bool(self, value):
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")

    def _as_list(self, value):
        if isinstance(value, list):
            return value
        if not value:
            return []
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [item.strip() for item in value.split(",") if item.strip()]
        return []


vms = VirtualMachineService()
