from console.utils.vm_restore_attributes import public_vm_attributes

VM_LOGIN_SECRET_ATTRIBUTE_NAMES = frozenset({
    "vm_login_password_hash",
    "login_password",
    "vm_login_password",
})
VM_LOGIN_USERNAME_ATTRIBUTE_NAME = "vm_ssh_username"
VM_LOGIN_KEY_ATTRIBUTE_NAME = "vm_ssh_authorized_key"
VM_LOGIN_LOG_REDACTED_ATTRIBUTE_NAMES = VM_LOGIN_SECRET_ATTRIBUTE_NAMES | {VM_LOGIN_KEY_ATTRIBUTE_NAME}
VM_LOGIN_TRANSFER_ATTRIBUTE_NAMES = VM_LOGIN_SECRET_ATTRIBUTE_NAMES | {
    VM_LOGIN_USERNAME_ATTRIBUTE_NAME,
    VM_LOGIN_KEY_ATTRIBUTE_NAME,
}


def _attribute_field(attribute, field):
    if isinstance(attribute, dict):
        return attribute.get(field, "")
    return getattr(attribute, field, "")


def is_vm_login_secret_attribute(attribute):
    return _attribute_field(attribute, "name") in VM_LOGIN_SECRET_ATTRIBUTE_NAMES


def is_vm_login_log_redacted_attribute_name(name):
    return name in VM_LOGIN_LOG_REDACTED_ATTRIBUTE_NAMES


def filter_vm_login_transfer_attributes(attributes):
    """Strip initialization identity from public templates, including old imports.

    Private backups and server-owned Region synchronization must retain their
    original attributes and must not use this public-transfer filter.
    """
    return [attribute for attribute in public_vm_attributes(attributes)
            if _attribute_field(attribute, "name") not in VM_LOGIN_TRANSFER_ATTRIBUTE_NAMES]
