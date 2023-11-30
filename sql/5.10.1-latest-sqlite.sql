------5.10.1 -> 5.11.0 sqlite

ALTER TABLE `tenant_services_port` ADD COLUMN `name` varchar(64) NULL;

-- 5.14.1 - 5.14.2 sql

ALTER TABLE `tenant_service` ADD COLUMN `arch` varchar(32) DEFAULT "amd64";
ALTER TABLE `rainbond_center_app_version` ADD COLUMN `arch` varchar(32) DEFAULT "amd64";
ALTER TABLE `rainbond_center_app` ADD COLUMN `arch` varchar(32) DEFAULT "amd64";


--- 5.15.3 - 5.16.0 sql
ALTER TABLE 'oauth_service' RENAME TO 'oauth_service_bak';

CREATE TABLE "oauth_service" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" varchar(32) NOT NULL,
    "client_id" varchar(255) NOT NULL,
    "client_secret" varchar(255) NOT NULL,
    "redirect_uri" varchar(255) NOT NULL,
    "home_url" varchar(255) NOT NULL,
    "auth_url" varchar(255) NOT NULL,
    "access_token_url" varchar(255) NOT NULL,
    "api_url" varchar(255) NOT NULL,
    "oauth_type" varchar(16) NOT NULL,
    "eid" varchar(64) NOT NULL,
    "enable" tinyint(1) NOT NULL,
    "is_deleted" tinyint(1) NOT NULL,
    "is_console" tinyint(1) NOT NULL,
    "is_auto_login" tinyint(1) NOT NULL,
    "is_git" tinyint(1) NOT NULL
);
INSERT INTO oauth_service
(client_id, client_secret, redirect_uri, home_url, auth_url, access_token_url, api_url, oauth_type, eid, enable, is_deleted, is_console, is_auto_login, is_git)
SELECT client_id, client_secret, redirect_uri, home_url, auth_url, access_token_url, api_url, oauth_type, eid, enable, is_deleted, is_console, is_auto_login, is_git
FROM oauth_service_bak;
drop table oauth_service_bak;

CREATE TABLE "virtual_machine_image" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "tenant_id" varchar(32) NOT NULL,
    "name" varchar(64) NOT NULL,
    "image_url" varchar(200) NOT NULL
);