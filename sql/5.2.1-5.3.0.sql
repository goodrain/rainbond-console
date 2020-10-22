
CREATE TABLE IF NOT EXISTS `tenant_service_monitor` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `service_id` varchar(32) NOT NULL,
  `path` varchar(32) NOT NULL,
  `port` int(11) NOT NULL,
  `service_show_name` varchar(64) NOT NULL,
  `interval` varchar(10) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `tenant_service_monitor_name_tenant_id_df0b897f_uniq` (`name`,`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `region_app` (
    `ID` int(11) NOT NULL AUTO_INCREMENT,
  `region_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `region_app_id` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `app_id` int NOT NULL,
  PRIMARY KEY (`ID`),
  PRIMARY KEY (`region_name`,`region_app_id`,`app_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `app_config_group` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `region_name` varchar(64),
  `app_id` int(11),
  `config_group_name` varchar(64),
  `deploy_type` varchar(32) DEFAULT 'env',
  `enable` bool DEFAULT FALSE,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `app_config_group_region_app_id_config_group_name_uniq` (`region_name`, `app_id`,`config_group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `app_config_group_item` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `app_id` int(11),
  `config_group_name` varchar(64),
  `item_key` varchar(255),
  `item_value` varchar(21000),
  PRIMARY KEY (`ID`),
  UNIQUE KEY `app_config_group_app_id_config_group_name_item_key_uniq` (`app_id`,`config_group_name`, `item_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `app_config_group_service` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `app_id` int(11),
  `config_group_name` varchar(64),
  `service_id` varchar(32),
  PRIMARY KEY (`ID`),
  UNIQUE KEY `app_config_group_app_id_config_group_name_uniq` (`app_id`,`config_group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

ALTER TABLE console.service_group ADD `create_time` datetime DEFAULT NULL;
ALTER TABLE console.service_group ADD `update_time` datetime DEFAULT NULL;

ALTER TABLE `console`.`tenant_services_port` ADD COLUMN `k8s_service_name` varchar(63) NULL AFTER `is_outer_service`;
ALTER TABLE `console`.`service_group` ADD COLUMN `username` varchar(255) NULL AFTER `note`;
ALTER TABLE `console`.`service_group` ADD COLUMN `governance_mode` varchar(255) NULL AFTER `principal_id`;