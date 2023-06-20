------5.10.1 -> 5.11.0 sqlite

ALTER TABLE `tenant_services_port` ADD COLUMN `name` varchar(64) NULL;

-- 5.14.1 - 5.14.2 sql

ALTER TABLE `tenant_service` ADD COLUMN `arch` varchar(32) DEFAULT "amd64";
ALTER TABLE `rainbond_center_app_version` ADD COLUMN `arch` varchar(32) DEFAULT "amd64";
ALTER TABLE `rainbond_center_app` ADD COLUMN `arch` varchar(32) DEFAULT "amd64";
