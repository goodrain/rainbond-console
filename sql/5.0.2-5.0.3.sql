

-- 2019-01-23 自动部署添加字段控制3中自动部署方式的打开与关闭（tenant_service）

ALTER TABLE tenant_service ADD COLUMN `open_code_webhooks` bool DEFAULT false NOT NULL;

ALTER TABLE tenant_service ADD COLUMN `open_image_webhooks` bool DEFAULT false NOT NULL;

ALTER TABLE tenant_service ADD COLUMN `open_api_webhooks` bool DEFAULT false NOT NULL;


-- 2019-01-23 自动部署添加字段控制3中自动部署方式的打开与关闭（tenant_service_delete）

ALTER TABLE tenant_service_delete ADD COLUMN `open_code_webhooks` bool DEFAULT false NOT NULL;

ALTER TABLE tenant_service_delete ADD COLUMN `open_image_webhooks` bool DEFAULT false NOT NULL;

ALTER TABLE tenant_service_delete ADD COLUMN `open_api_webhooks` bool DEFAULT false NOT NULL;


-- 2019-01-23 删除原有自动部署属性字段（tenant_service）

alter table tenant_service drop column open_webhooks;

-- 2019-01-23 删除原有自动部署属性字段（tenant_service_delete）

alter table tenant_service_delete drop column open_webhooks;


