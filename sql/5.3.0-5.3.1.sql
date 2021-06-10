-- only support mysql
ALTER TABLE tenant_service_env_var MODIFY attr_value text;
ALTER TABLE tenant_service_monitor MODIFY `path` varchar(255);
ALTER TABLE tenant_info CHANGE `region` `region` varchar(64) Default '';
ALTER TABLE tenant_info DROP COLUMN `region`;
ALTER TABLE service_share_record ADD COLUMN `share_app_version_info` VARCHAR(255) DEFAULT '';

ALTER TABLE app_upgrade_record ADD COLUMN `upgrade_group_id` int DEFAULT 0;
ALTER TABLE `console`.`tenant_service_config` ADD COLUMN `volume_name` varchar(255) NULL AFTER `file_content`;
ALTER TABLE `console`.`app_upgrade_record` ADD COLUMN `snapshot_id` varchar(32) NULL AFTER `upgrade_group_id`;

CREATE TABLE IF NOT EXISTS `app_snapshots` (
     `ID` int NOT NULL AUTO_INCREMENT,
     `tenant_id` varchar(32) NOT NULL,
     `upgrade_group_id` int NOT NULL,
     `snapshot_id` varchar(32) NOT NULL,
     `snapshot` text NOT NULL,
     `update_time` datetime(6) NOT NULL,
     `create_time` datetime(6) NOT NULL,
     PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=588 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
