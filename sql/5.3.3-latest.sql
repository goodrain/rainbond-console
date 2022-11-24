-- 5.3.3 - 5.4.0 sql
ALTER TABLE service_group ADD COLUMN `logo` VARCHAR(255) DEFAULT '';

-- 5.4.1 - 5.5.0 sql
ALTER TABLE tenant_info ADD COLUMN `namespace` VARCHAR(33) unique;
update tenant_info set namespace=tenant_id;
ALTER TABLE service_group ADD COLUMN `k8s_app` VARCHAR(64);
ALTER TABLE tenant_service ADD COLUMN `k8s_component_name` VARCHAR(100);
update tenant_service set k8s_component_name=service_alias;
ALTER TABLE tenant_service_delete ADD COLUMN `k8s_component_name` VARCHAR(100);

-- 5.5.0 - 5.5.1 sql
ALTER TABLE `service_domain` ADD COLUMN `path_rewrite` bool DEFAULT false NOT NULL;
ALTER TABLE `service_domain` ADD COLUMN `rewrites` longtext NOT NULL;

-- 5.6.0 - 5.7.0 sql
ALTER TABLE `rainbond_center_app_version` ADD COLUMN `is_plugin` bool DEFAULT false NOT NULL;
ALTER TABLE `plugin_config_items` MODIFY `attr_name` varchar(64) NOT NULL;
ALTER TABLE `plugin_config_items` MODIFY `attr_alt_value` LONGTEXT NOT NULL;
ALTER TABLE `plugin_config_items` MODIFY `attr_default_value` LONGTEXT;
ALTER TABLE `service_plugin_config_var` MODIFY `attrs` LONGTEXT NOT NULL;

-- 5.7.1 - 5.8.0 sql
CREATE TABLE IF NOT EXISTS `team_registry_auths` (
  `id` int NOT NULL AUTO_INCREMENT,
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `tenant_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `secret_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `domain` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `username` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `component_k8s_attributes` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `component_id` varchar(32) NOT NULL,
  `name` varchar(255) NOT NULL,
  `save_type` varchar(32) NOT NULL,
  `attribute_value` longtext CHARACTER SET utf8mb4,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `k8s_resources` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  `app_id` varchar(32) NOT NULL,
  `name` varchar(255) NOT NULL,
  `kind` varchar(255) NOT NULL,
  `content` longtext NOT NULL,
  `error_overview` longtext NOT NULL,
  `state` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `package_upload_record` (
    `ID` INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    `event_id` VARCHAR(32) DEFAULT '',
    `status` VARCHAR(15) DEFAULT '',
    `format` VARCHAR(15) DEFAULT '',
    `source_dir` VARCHAR(256) DEFAULT '',
    `team_name` VARCHAR(32) DEFAULT '',
    `region` VARCHAR(32) DEFAULT '',
    `component_id` VARCHAR(32) DEFAULT '',
    `create_time` DATETIME,
    `update_time` DATETIME
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4;

ALTER TABLE tenant_service ADD COLUMN job_strategy varchar(2047) DEFAULT '';

-- 5.9.0 - 5.10.0 sql

CREATE TABLE `app_helm_overrides` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `app_id` int(11) NOT NULL,
  `app_model_id` varchar(32) NOT NULL,
  `overrides` longtext NOT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE rainbond_center_app MODIFY COLUMN source varchar(128);

CREATE TABLE `helm_repo` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `repo_id` varchar(33) NOT NULL,
  `repo_name` varchar(64) NOT NULL,
  `repo_url` varchar(128) NOT NULL,
  `username` varchar(128) NOT NULL,
  `password` varchar(128) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `repo_id` (`repo_id`),
  UNIQUE KEY `repo_name` (`repo_name`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE tenant_info ADD logo longtext NULL;

-- 5.10.0 - 5.10.1 sql

ALTER TABLE tenant_service_delete ADD COLUMN job_strategy varchar(2047) DEFAULT '';
ALTER TABLE tenant_service_delete ADD COLUMN exec_user varchar(128) DEFAULT '';
ALTER TABLE tenant_service_delete ADD COLUMN app_name varchar(128) DEFAULT '';
