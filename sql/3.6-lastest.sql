-- 自动触发部署功能添加字段
ALTER TABLE `tenant_service` ADD COLUMN `secret` varchar(64) NULL;
ALTER TABLE `tenant_service` ADD COLUMN `open_webhooks` bool DEFAULT false NOT NULL;

-- 站内信添加标题，等级字段
ALTER TABLE `announcement` ADD COLUMN `title` varchar(64) DEFAULT 'title' NOT NULL;
ALTER TABLE `announcement` ADD COLUMN `level` varchar(32) DEFAULT 'low' NOT NULL;
ALTER TABLE `user_message` ADD COLUMN `title` varchar(64) DEFAULT 'title' NOT NULL;
ALTER TABLE `user_message` ADD COLUMN `level` varchar(32) DEFAULT 'low' NOT NULL;

-- 增加字段长度
ALTER TABLE `announcement` MODIFY `type` varchar(32);
ALTER TABLE `user_message` MODIFY `msg_type` varchar(32);