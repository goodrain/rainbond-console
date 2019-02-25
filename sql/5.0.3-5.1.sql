-- 创建三方服务endpoints表 third_party_service_endpoints


CREATE TABLE `third_party_service_endpoints` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `service_id` varchar(32),
  `service_cname` varchar(128),
  `tenant_id` varchar(32),
  `endpoints_type` varchar(32),
  `endpoints_info` text DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;


-- 新增三方服务管理权限（开发者以上级别拥有）
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('tripartite_service_manage', '三方服务管理', 1, NULL, 2);

INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 31);

INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 31);

INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 31);
