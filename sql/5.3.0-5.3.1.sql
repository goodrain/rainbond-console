-- only support mysql
ALTER TABLE tenant_service_env_var MODIFY attr_value text;
ALTER TABLE tenant_service_monitor MODIFY `path` varchar(255);
ALTER TABLE tenant_info CHANGE `region` `region` varchar(64) Default '';
ALTER TABLE tenant_info DROP COLUMN `region`;
ALTER TABLE service_share_record ADD COLUMN `share_app_version_info` VARCHAR(255) DEFAULT '';
ALTER TABLE rainbond_center_app_version modify COLUMN version_alias VARCHAR(64);
ALTER TABLE service_share_record modify COLUMN share_version_alias VARCHAR(64);
