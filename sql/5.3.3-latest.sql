-- 5.3.3 - 5.4.0 sql
ALTER TABLE service_group ADD COLUMN `logo` VARCHAR(255) DEFAULT '';

-- 5.4.1 - 5.4.2 sql
ALTER TABLE tenant_info ADD COLUMN `namespace` VARCHAR(33) unique;
update tenant_info set namespace=tenant_id;
ALTER TABLE service_group ADD COLUMN `k8s_app` VARCHAR(64);
ALTER TABLE tenant_service ADD COLUMN `k8s_component_name` VARCHAR(100);
update tenant_service set k8s_component_name=service_alias;
ALTER TABLE tenant_service_delete ADD COLUMN `k8s_component_name` VARCHAR(100);
