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

CREATE TABLE `k8s_resources` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `create_time` datetime(6) NOT NULL,
  `update_time` datetime(6) NOT NULL,
  `app_id` varchar(32) NOT NULL,
  `name` varchar(255) NOT NULL,
  `kind` varchar(255) NOT NULL,
  `content` longtext NOT NULL,
  `status` longtext NOT NULL,
  `success` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4;