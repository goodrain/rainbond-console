
-- 云市应用官方认证及安装量排序增加字段
ALTER TABLE `rainbond_center_app` ADD COLUMN `install_number` INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE `rainbond_center_app` ADD COLUMN `is_official` bool DEFAULT false NOT NULL;