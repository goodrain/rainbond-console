
-- 分享应用时给APP添加详情信息

ALTER TABLE `rainbond_center_app` ADD COLUMN `details` longtext NULL;



-- 添加判断更新字段

ALTER TABLE rainbond_center_app ADD `upgrade_time` varchar(30) DEFAULT "";


