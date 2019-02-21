

-- 2019-01-23 删除原有自动部署属性字段（tenant_service）

alter table tenant_service drop column open_webhooks;

-- 2019-01-23 删除原有自动部署属性字段（tenant_service_delete）

alter table tenant_service_delete drop column open_webhooks;


-- 2019-01-23 添加服务自动部署属性表

CREATE TABLE `service_webhooks` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `service_id` varchar(32),
  `state` bool DEFAULT false,
  `webhooks_type` varchar(128),
  `deploy_keyword` varchar(128) DEFAULT 'deploy',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;


-- 2019-02-21 添加已删除字段open_webhooks（兼容老版本服务）

ALTER TABLE tenant_service ADD COLUMN `open_webhooks` bool DEFAULT false;

-- 2019-02-21 添加已删除字段open_webhooks（兼容老版本服务）

ALTER TABLE tenant_service_delete ADD COLUMN `open_webhooks` bool DEFAULT false;