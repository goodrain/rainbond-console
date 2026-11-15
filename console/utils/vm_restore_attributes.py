"""Shared public boundary for Region restore state and Console journals.

Keep the predicate aligned with Region pkg/vmrestore.IsInternalAttribute.
No raw private record may be serialized through a public attribute DTO.
"""
from console.exception.main import ServiceHandleException

VM_RESTORE_PREFIX = "vm_restore_"
VM_RESTORE_MANIFEST_PREFIX = "vm_restore_manifest_"
VM_RESTORE_OPERATION_PREFIX = "vm_restore_operation_"
VM_RESTORE_ACTIVE_OPERATION = "vm_restore_active_operation"
VM_RESTORE_LEGACY_BINDINGS = "vm_volume_bindings"
# Go strings.TrimSpace uses Unicode White_Space; Python strip additionally
# removes U+001C through U+001F, which would reserve names Region leaves public.
GO_WHITESPACE = ("\t\n\v\f\r \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005"
                 "\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000")


def attribute_name(attribute):
    return attribute.get("name", "") if isinstance(attribute, dict) else getattr(attribute, "name", "")


def is_private_vm_attribute(name):
    # U+0130 simple-lowercases to ASCII i in Go, while Python expands it to
    # i + U+0307. It is the only differing lowercase mapping into ASCII.
    normalized = name.strip(GO_WHITESPACE).replace("\u0130", "i").lower() if isinstance(name, str) else ""
    return normalized == VM_RESTORE_LEGACY_BINDINGS or normalized.startswith(VM_RESTORE_PREFIX)


def reject_private_vm_attribute(name):
    if is_private_vm_attribute(name):
        raise ServiceHandleException(msg="VM restore control attributes are managed by the server",
                                     msg_show="虚拟机恢复控制属性由系统管理，不能通过此接口访问",
                                     status_code=403)


def public_vm_attributes(attributes):
    return [attribute for attribute in attributes or [] if not is_private_vm_attribute(attribute_name(attribute))]


def public_attribute_fields(attribute):
    """Only public content, never a database PK or caller-controlled scope."""
    reject_private_vm_attribute(attribute_name(attribute))
    if isinstance(attribute, dict):
        return {key: attribute[key] for key in ("name", "save_type", "attribute_value") if key in attribute}
    return {key: getattr(attribute, key, "") for key in ("name", "save_type", "attribute_value")}
