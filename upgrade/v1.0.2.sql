CREATE TABLE `app_service_packages` (
  `ID` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `service_key` VARCHAR(32)            NOT NULL,
  `app_version` VARCHAR(20)            NOT NULL,
  `name` VARCHAR(100)           NOT NULL,
  `memory` INTEGER NOT NULL,
  `node` INTEGER NOT NULL,
  `trial` INTEGER NOT NULL,
  `price` DOUBLE PRECISION NOT NULL,
  `total_price` DOUBLE PRECISION NOT NULL
);

CREATE TABLE `wechat_state` (
  `ID` INTEGER AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `state` VARCHAR(5000)          NOT NULL,
  `create_time` DATETIME NOT NULL,
  `update_time` DATETIME NOT NULL
);

ALTER TABLE `tenant_service` ADD COLUMN `service_origin` varchar(15) DEFAULT 'assistant' NOT NULL;

ALTER TABLE `tenant_service_delete` ADD COLUMN `service_origin` varchar(15) DEFAULT 'assistant' NOT NULL;

ALTER TABLE `app_service_packages` ADD COLUMN `dep_info` varchar(2000) DEFAULT '[]' NOT NULL;

ALTER TABLE tenant_info ADD expired_time datetime DEFAULT null;

ALTER TABLE `app_service` ADD COLUMN `show_app` BOOL DEFAULT 0 NOT NULL;

ALTER TABLE `app_service` ADD COLUMN `show_assistant` BOOL DEFAULT 0 NOT NULL;
