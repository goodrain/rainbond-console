

-- 2019-01-23 删除原有自动部署属性字段（tenant_service）

alter table tenant_service drop column open_webhooks;

-- 2019-01-23 删除原有自动部署属性字段（tenant_service_delete）

alter table tenant_service_delete drop column deploy_keyword;


-- 2019-01-23 添加服务自动部署属性表

CREATE TABLE `service_webhooks` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `service_id` varchar(32),
  `open_code_webhooks` bool DEFAULT false,
  `open_image_webhooks` bool DEFAULT false,
  `open_api_webhooks` bool DEFAULT false,
  `deploy_keyword` varchar(128) DEFAULT 'deploy',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;