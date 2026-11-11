VM_LOGIN_SECRET_ATTRIBUTE_NAMES = frozenset({
    "vm_login_password_hash",
    "login_password",
    "vm_login_password",
})
VM_LOGIN_USERNAME_ATTRIBUTE_NAME = "vm_ssh_username"
VM_LOGIN_KEY_ATTRIBUTE_NAME = "vm_ssh_authorized_key"
VM_LOGIN_LOG_REDACTED_ATTRIBUTE_NAMES = VM_LOGIN_SECRET_ATTRIBUTE_NAMES | {VM_LOGIN_KEY_ATTRIBUTE_NAME}


def _attribute_field(attribute, field):
    if isinstance(attribute, dict):
        return attribute.get(field, "")
    return getattr(attribute, field, "")


def is_vm_login_secret_attribute(attribute):
    return _attribute_field(attribute, "name") in VM_LOGIN_SECRET_ATTRIBUTE_NAMES


def is_vm_login_log_redacted_attribute_name(name):
    return name in VM_LOGIN_LOG_REDACTED_ATTRIBUTE_NAMES


def filter_vm_login_transfer_attributes(attributes):
    groups = {}
    for attribute in attributes or []:
        component_id = _attribute_field(attribute, "component_id") or ""
        groups.setdefault(component_id, []).append(attribute)

    filtered = []
    for component_attributes in groups.values():
        has_password_credential = any(
            _attribute_field(attribute, "name") in VM_LOGIN_SECRET_ATTRIBUTE_NAMES and
            _attribute_field(attribute, "attribute_value")
            for attribute in component_attributes
        )
        has_ssh_key = any(
            _attribute_field(attribute, "name") == VM_LOGIN_KEY_ATTRIBUTE_NAME and
            _attribute_field(attribute, "attribute_value")
            for attribute in component_attributes
        )
        password_login = has_password_credential and not has_ssh_key

        for attribute in component_attributes:
            if is_vm_login_secret_attribute(attribute):
                continue
            if password_login and _attribute_field(attribute, "name") == VM_LOGIN_USERNAME_ATTRIBUTE_NAME:
                continue
            filtered.append(attribute)
    return filtered
