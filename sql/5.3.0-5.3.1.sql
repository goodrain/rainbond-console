-- only support mysql
ALTER TABLE tenant_service_env_var MODIFY attr_value text;
ALTER TABLE tenant_service_monitor MODIFY `path` varchar(255);
ALTER TABLE tenant_info CHANGE `region` `region` varchar(64) Default '';
ALTER TABLE service_share_record ADD COLUMN `share_app_version_info` VARCHAR(255) DEFAULT '';
