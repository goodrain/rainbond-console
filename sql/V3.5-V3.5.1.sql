-- 2018.04.19
ALTER TABLE plugin_config_items MODIFY attr_default_value VARCHAR(128);
ALTER TABLE tenant_service_plugin_attr MODIFY attr_default_value VARCHAR(128);
ALTER TABLE tenant_service_plugin_attr MODIFY attr_value VARCHAR(128);
ALTER TABLE tenant_service_plugin_attr MODIFY attr_alt_value VARCHAR(128);