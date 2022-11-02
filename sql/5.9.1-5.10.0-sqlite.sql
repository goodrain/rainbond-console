------5.9.1 -> 5.10.0 sqlite
BEGIN TRANSACTION;
CREATE TABLE "app_helm_overrides" (
 "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "app_id" int(11) NOT NULL,
  "app_model_id" varchar(32) NOT NULL,
  "overrides" longtext NOT NULL
);

ALTER TABLE rainbond_center_app RENAME TO rainbond_center_app_old;
CREATE TABLE "rainbond_center_app" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "app_id" varchar(32) NOT NULL, "app_name" varchar(64) NOT NULL,
    "create_user" integer NULL, "create_team" varchar(64) NULL,
    "pic" varchar(200) NULL,
    "source" varchar(128) NULL,
    "dev_status" varchar(32) NULL,
    "scope" varchar(50) NOT NULL,
    "describe" varchar(400) NULL,
    "is_ingerit" bool NOT NULL,
    "create_time" datetime NULL,
    "update_time" datetime NULL,
    "enterprise_id" varchar(32) NOT NULL,
    "install_number" integer NOT NULL,
    "is_official" bool NOT NULL,
    "details" text NULL
);
INSERT INTO rainbond_center_app
(app_id, app_name, create_user, create_team, pic, "source", dev_status, "scope", "describe", is_ingerit, create_time, update_time, enterprise_id, install_number, is_official, details)
SELECT app_id, app_name, create_user, create_team, pic, "source", dev_status, "scope", "describe", is_ingerit, create_time, update_time, enterprise_id, install_number, is_official, details
FROM rainbond_center_app_old;


CREATE TABLE "helm_repo" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "repo_name" varchar(64) NOT NULL UNIQUE,
    "repo_url" varchar(128) NOT NULL,
    "username" varchar(128) NOT NULL,
    "password" varchar(128) NOT NULL,
    "repo_id" varchar(33) NOT NULL UNIQUE
);

COMMIT;