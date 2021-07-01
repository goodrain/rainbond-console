-- only support mysql
ALTER TABLE `rbdconsole`.`service_group`
ADD COLUMN `app_store_name` varchar(255) NULL AFTER `app_type`,
ADD COLUMN `app_store_url` varchar(2047) NULL AFTER `app_store_name`,
ADD COLUMN `app_template_name` varchar(255) NULL AFTER `app_store_url`,
ADD COLUMN `version` varchar(255) NULL AFTER `app_template_name`;

ALTER TABLE tenant_service_env_var MODIFY attr_value text;
ALTER TABLE tenant_service_monitor MODIFY `path` varchar(255);
ALTER TABLE tenant_info CHANGE `region` `region` varchar(64) Default '';
ALTER TABLE service_share_record ADD COLUMN `share_app_version_info` VARCHAR(255) DEFAULT '';

ALTER TABLE app_upgrade_record ADD COLUMN `upgrade_group_id` int DEFAULT 0;
ALTER TABLE `tenant_service_config` ADD COLUMN `volume_name` varchar(255) NULL AFTER `file_content`;
ALTER TABLE `app_upgrade_record` ADD COLUMN `snapshot_id` varchar(32) NULL AFTER `upgrade_group_id`;
ALTER TABLE `app_upgrade_record` ADD COLUMN `record_type` varchar(32) NULL;
ALTER TABLE `app_upgrade_record` ADD COLUMN `parent_id` int DEFAULT 0;

CREATE TABLE IF NOT EXISTS `app_upgrade_snapshots` (
     `ID` int NOT NULL AUTO_INCREMENT,
     `tenant_id` varchar(32) NOT NULL,
     `upgrade_group_id` int NOT NULL,
     `snapshot_id` varchar(32) NOT NULL,
     `snapshot` longtext NOT NULL,
     `update_time` datetime(6) NOT NULL,
     `create_time` datetime(6) NOT NULL,
     PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=588 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

ALTER TABLE rainbond_center_app_version modify COLUMN version_alias VARCHAR(64);
ALTER TABLE service_share_record modify COLUMN share_version_alias VARCHAR(64);

ALTER TABLE tenant_service add COLUMN container_gpu int(64) DEFAULT 0;
ALTER TABLE tenant_service_delete add COLUMN container_gpu int(64) DEFAULT 0;
