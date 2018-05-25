-- 自动触发部署功能添加字段
ALTER TABLE `tenant_service` ADD COLUMN `secret` varchar(64) NULL;
ALTER TABLE `tenant_service` ADD COLUMN `open_webhooks` bool DEFAULT false NOT NULL;