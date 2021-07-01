BEGIN TRANSACTION;
ALTER TABLE tenant_service_env_var RENAME TO tenant_service_env_var_old;
ALTER TABLE tenant_service_monitor RENAME TO tenant_service_monitor_old;
ALTER TABLE tenant_info RENAME TO tenant_info_old;
ALTER TABLE rainbond_center_app_version RENAME TO rainbond_center_app_version_old;
ALTER TABLE service_share_record RENAME TO service_share_record_old;

CREATE TABLE "tenant_service_env_var" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "tenant_id" varchar(32) NOT NULL,
    "service_id" varchar(32) NOT NULL,
    "container_port" integer NOT NULL,
    "name" varchar(1024) NOT NULL,
    "attr_name" varchar(1024) NOT NULL,
    "attr_value" text,
    "is_change" bool NOT NULL,
    "scope" varchar(10) NOT NULL,
    "create_time" datetime NOT NULL
);

CREATE TABLE "tenant_service_monitor" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" varchar(64) NOT NULL,
    "tenant_id" varchar(32) NOT NULL,
    "service_id" varchar(32) NOT NULL,
    "path" varchar(255) NOT NULL,
    "port" integer NOT NULL,
    "service_show_name" varchar(64) NOT NULL,
    "interval" varchar(10) NOT NULL
);

CREATE TABLE "tenant_info" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "tenant_id" varchar(33) NOT NULL UNIQUE,
    "tenant_name" varchar(64) NOT NULL UNIQUE,
    "region" varchar(64) Default '',
    "is_active" bool NOT NULL,
    "pay_type" varchar(5) NOT NULL,
    "balance" decimal NOT NULL,
    "create_time" datetime NOT NULL,
    "creater" integer NOT NULL,
    "limit_memory" integer NOT NULL,
    "update_time" datetime NOT NULL,
    "pay_level" varchar(30) NOT NULL,
    "expired_time" datetime NULL,
    "tenant_alias" varchar(64) NULL,
    "enterprise_id" varchar(32) NULL
);

CREATE TABLE IF NOT EXISTS "app_upgrade_snapshots" (
     "ID" integer NOT NULL PRIMARY KEY  AUTOINCREMENT,
     "tenant_id" varchar(32) NOT NULL,
     "upgrade_group_id" int NOT NULL DEFAULT 0,
     "snapshot_id" varchar(32) NOT NULL,
     "snapshot" longtext NOT NULL,
     "update_time" datetime(6) NOT NULL,
     "create_time" datetime(6) NOT NULL
);

CREATE TABLE "rainbond_center_app_version" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "enterprise_id" varchar(32) NOT NULL,
    "app_id" varchar(32) NOT NULL,
    "version" varchar(32) NOT NULL,
    "version_alias" varchar(64) NOT NULL,
    "app_version_info" varchar(255) NOT NULL,
    "record_id" integer NOT NULL,
    "share_user" integer NOT NULL,
    "share_team" varchar(64) NOT NULL,
    "group_id" integer NOT NULL,
    "dev_status" varchar(32) NULL,
    "source" varchar(15) NULL,
    "scope" varchar(15) NULL,
    "app_template" text NOT NULL,
    "template_version" varchar(10) NOT NULL,
    "create_time" datetime NULL,
    "update_time" datetime NULL,
    "upgrade_time" varchar(30) NOT NULL,
    "install_number" integer NOT NULL,
    "is_official" bool NOT NULL,
    "is_ingerit" bool NOT NULL,
    "is_complete" bool NOT NULL,
    "template_type" varchar(32) NULL,
    "release_user_id" integer NULL,
    "region_name" varchar(64) NULL
);

CREATE TABLE "service_share_record" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "group_share_id" varchar(32) NOT NULL UNIQUE,
    "group_id" varchar(32) NOT NULL,
    "team_name" varchar(64) NOT NULL,
    "event_id" varchar(32) NULL,
    "share_version" varchar(15) NULL,
    "share_version_alias" varchar(64) NULL,
    "is_success" bool NOT NULL,
    "step" integer NOT NULL,
    "status" integer NOT NULL,
    "app_id" varchar(64) NULL,
    "scope" varchar(64) NULL,
    "share_app_market_name" varchar(64) NULL,
    "create_time" datetime NOT NULL,
    "update_time" datetime NOT NULL,
    `share_app_version_info` VARCHAR(255) DEFAULT ''
);

INSERT INTO tenant_service_env_var (`ID`, `tenant_id`, `service_id`, `container_port`, `name`, `attr_name`, `attr_value`, `is_change`, `scope`, `create_time`)
  SELECT `ID`, `tenant_id`, `service_id`, `container_port`, `name`, `attr_name`, `attr_value`, `is_change`, `scope`, `create_time`  FROM tenant_service_env_var_old;

INSERT INTO tenant_service_monitor (`ID`, `name`, `tenant_id`, `service_id`, `path`, `port`, `service_show_name`, `interval`)
  SELECT `ID`, `name`, `tenant_id`, `service_id`, `path`, `port`, `service_show_name`, `interval` FROM tenant_service_monitor_old;

INSERT INTO tenant_info (`ID`, `tenant_id`, `tenant_name`, `region`, `is_active`, `pay_type`, `balance`, `create_time`, `creater`, `limit_memory`, `update_time`, `pay_level`, `expired_time`, `tenant_alias`, `enterprise_id`)
  SELECT `ID`, `tenant_id`, `tenant_name`, `region`, `is_active`, `pay_type`, `balance`, `create_time`, `creater`, `limit_memory`, `update_time`, `pay_level`, `expired_time`, `tenant_alias`, `enterprise_id` FROM tenant_info_old;

INSERT INTO rainbond_center_app_version (`ID`, `enterprise_id`, `app_id`, `version`, `version_alias`, `app_version_info`, `record_id`, `share_user`, `share_team`, `group_id`, `dev_status`, `source`, `scope`, `app_template`, `template_version`,
`create_time`,`update_time`,`upgrade_time`,`install_number`,`is_official`,`is_ingerit`,`is_complete`,`template_type`,`release_user_id`,`region_name`)
  SELECT `ID`, `enterprise_id`, `app_id`, `version`, `version_alias`, `app_version_info`, `record_id`, `share_user`, `share_team`, `group_id`, `dev_status`, `source`, `scope`, `app_template`, `template_version`,
`create_time`,`update_time`,`upgrade_time`,`install_number`,`is_official`,`is_ingerit`,`is_complete`,`template_type`,`release_user_id`,`region_name` FROM rainbond_center_app_version_old;

INSERT INTO service_share_record (`ID`, `group_share_id`, `group_id`, `team_name`, `event_id`, `share_version`, `share_version_alias`, `is_success`, `step`, `status`, `app_id`, `scope`, `share_app_market_name`, `create_time`, `update_time`)
  SELECT `ID`, `group_share_id`, `group_id`, `team_name`, `event_id`, `share_version`, `share_version_alias`, `is_success`, `step`, `status`, `app_id`, `scope`, `share_app_market_name`, `create_time`, `update_time` FROM service_share_record_old;

ALTER TABLE app_upgrade_record ADD COLUMN `upgrade_group_id` int DEFAULT 0;
ALTER TABLE `tenant_service_config` ADD COLUMN `volume_name` varchar(255) NULL;
ALTER TABLE `app_upgrade_record` ADD COLUMN `snapshot_id` varchar(32) NULL;
ALTER TABLE `app_upgrade_record` ADD COLUMN `record_type` varchar(32) NULL;
ALTER TABLE `app_upgrade_record` ADD COLUMN `parent_id` int DEFAULT 0;

ALTER TABLE tenant_service add COLUMN container_gpu int(64) DEFAULT 0;
ALTER TABLE tenant_service_delete add COLUMN container_gpu int(64) DEFAULT 0;

ALTER TABLE `service_group` ADD COLUMN `app_store_name` varchar(255) NULL;
ALTER TABLE `service_group` ADD COLUMN `app_store_url` varchar(2047) NULL;
ALTER TABLE `service_group` ADD COLUMN `app_template_name` varchar(255) NULL;
ALTER TABLE `service_group` ADD COLUMN `version` varchar(255) NULL;
COMMIT;
