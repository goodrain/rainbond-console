-- 修改插件配置项，添加协议字段
ALTER TABLE plugin_config_items ADD protocol VARCHAR(32) DEFAULT '' NULL;

CREATE TABLE service_plugin_config_var
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    service_id VARCHAR(32) NOT NULL,
    plugin_id VARCHAR(32) NOT NULL,
    build_version VARCHAR(32) NOT NULL,
    service_meta_type VARCHAR(32) NOT NULL,
    injection VARCHAR(32) NOT NULL,
    dest_service_id VARCHAR(32) NOT NULL,
    dest_service_alias VARCHAR(32) NOT NULL,
    container_port INT(11) NOT NULL,
    attrs VARCHAR(256) DEFAULT '',
    protocol VARCHAR(16) DEFAULT '',
    create_time DATETIME
);