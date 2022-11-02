BEGIN TRANSACTION;
ALTER TABLE rainbond_center_app_version ADD COLUMN is_plugin bool DEFAULT false NOT NULL;
ALTER TABLE plugin_config_items RENAME TO plugin_config_items_old;
ALTER TABLE service_plugin_config_var RENAME TO service_plugin_config_var_old;

CREATE TABLE "plugin_config_items" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "plugin_id" varchar(32) NOT NULL,
    "build_version" varchar(32) NOT NULL,
    "service_meta_type" varchar(32) NOT NULL,
    "attr_name" varchar(64) NOT NULL,
    "attr_type" varchar(16) NOT NULL,
    "attr_alt_value" longtext NOT NULL,
    "attr_default_value" longtext NOT NULL,
    "is_change" tinyint(1) NOT NULL,
    "create_time" datetime(6) NOT NULL,
    "attr_info" varchar(32),
    "protocol" varchar(32)
);

CREATE TABLE "service_plugin_config_var" (
    "ID" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "service_id" varchar(32) NOT NULL,
    "plugin_id" varchar(32) NOT NULL,
    "build_version" varchar(32) NOT NULL,
    "service_meta_type" varchar(32) NOT NULL,
    "injection" varchar(32) NOT NULL,
    "dest_service_id" varchar(32) NOT NULL,
    "dest_service_alias" varchar(32) NOT NULL,
    "container_port" int(11) NOT NULL,
    "attrs" longtext NOT NULL,
    "protocol" varchar(16) NOT NULL,
    "create_time" datetime(6) NOT NULL
);

INSERT INTO plugin_config_items (`ID`, `plugin_id`, `build_version`, `service_meta_type`, `attr_name`, `attr_type`, `attr_alt_value`, `attr_default_value`, `is_change`, `create_time`, `attr_info`, `protocol`)
SELECT `ID`, `plugin_id`, `build_version`, `service_meta_ty    pe`, `attr_name`, `attr_type`, `attr_alt_value`, `attr_default_value`, `is_change`, `    create_time`, `attr_info`, `protocol` FROM plugin_config_items_old;

INSERT INTO service_plugin_config_var (`ID`, `service_id`, `plugin_id`, `build_version`, `service_meta_type`, `injection`, `dest_service_id`, `dest_service_alias`, `container_port`, `attrs`, `protocol`, `create_time`)
SELECT `ID`, `service_id`, `plugin_id`, `build_versio    n`, `service_meta_type`, `injection`, `dest_service_id`, `dest_service_alias`, `conta    iner_port`, `attrs`, `protocol`, `create_time` FROM service_plugin_config_var_old;
COMMIT;
