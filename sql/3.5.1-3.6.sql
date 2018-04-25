-- 修改插件配置项，添加协议字段
ALTER TABLE plugin_config_items ADD protocol VARCHAR(32) DEFAULT '' NULL;