
-- 分享应用时给APP添加详情信息

ALTER TABLE `rainbond_center_app` ADD COLUMN `details` longtext NULL;

-- 云市插件表添加详情信息字段

ALTER TABLE `rainbond_center_plugin` ADD COLUMN `details` longtext NULL;

-- 添加判断更新字段

ALTER TABLE rainbond_center_app ADD `upgrade_time` varchar(30) DEFAULT "";


-- 添加判断应用是否更新字段

ALTER TABLE tenant_service ADD COLUMN `is_upgrate` bool DEFAULT false NOT NULL;

ALTER TABLE tenant_service_delete ADD COLUMN `is_upgrate` bool DEFAULT false NOT NULL;


-- 添加console_service与内部市场service对接的唯一字段

ALTER TABLE tenant_service ADD COLUMN `console_center_uuid` varchar(128) DEFAULT "";

ALTER TABLE tenant_service_delete ADD COLUMN `console_center_uuid` varchar(128) DEFAULT "";


ALTER TABLE rainbond_center_app ADD COLUMN `console_center_uuid` varchar(128) DEFAULT "";

-- 修改region_info证书相关字段格式

ALTER TABLE region_info MODIFY `ssl_ca_cert` TEXT;

ALTER TABLE region_info MODIFY `cert_file` TEXT;

ALTER TABLE region_info MODIFY `key_file` TEXT;

