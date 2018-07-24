
-- 云市应用官方认证及安装量排序增加字段
ALTER TABLE `rainbond_center_app` ADD COLUMN `install_number` INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE `rainbond_center_app` ADD COLUMN `is_official` bool DEFAULT false NOT NULL;


-- 云帮应用添加server_type字段
ALTER TABLE `tenant_service` ADD COLUMN `server_type` varchar(5) default 'git';
ALTER TABLE `tenant_service_delete` ADD COLUMN `server_type` varchar(5) default 'git';