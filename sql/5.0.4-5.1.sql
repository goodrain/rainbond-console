-- 2019-02-17创建三方服务endpoints表 third_party_service_endpoints


CREATE TABLE `third_party_service_endpoints` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `service_id` varchar(32),
  `service_cname` varchar(128),
  `tenant_id` varchar(32),
  `endpoints_type` varchar(32),
  `endpoints_info` text DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;


-- 2019-02-25新增三方服务管理权限（开发者以上级别拥有）
INSERT INTO `tenant_permission_group` (`group_name`) VALUES ('三方服务相关');

INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('add_endpoint', '添加实例', 1, NULL, 4);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('delete_endpoint', '删除实例', 1, NULL, 4);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('put_endpoint', '修改实例上下线', 1, NULL, 4);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('health_detection', '编辑健康检测', 1, NULL, 4);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('reset_secret_key', '重置秘钥', 1, NULL, 4);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('create_three_service', '创建三方服务', 1, NULL, 4);




INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 31);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 32);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 33);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 34);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 35);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 36);



INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 31);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 32);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 33);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 34);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 35);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 36);



INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 31);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 32);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 33);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 34);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 35);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 36);



-- 2019-03-12新增网关自定义配置表
CREATE TABLE `gateway_custom_configuration` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `rule_id` varchar(32),
  `value` text,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;


-- **2019-03-18修改云市表唯一索引字段值，删除原有索引，添加新索引

drop index `group_key` on rainbond_center_app;

ALTER TABLE `rainbond_center_app` ADD UNIQUE ( `group_key`, `version`, `enterprise_id`)


