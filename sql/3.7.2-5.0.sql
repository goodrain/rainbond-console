-- 新增访问控制、证书管理权限（仅团队创建者和管理员拥有）
INSERT INTO `tenant_permission_group` (`group_name`) VALUES ('网关相关');

INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('access control', '查看访问控制', 1, NULL, 3);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('control operation', '访问控制操作', 1, NULL, 3);

INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('certificate management', '访问证书管理', 1, NULL, 3);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('certificate operation', '证书管理操作', 1, NULL, 3);

INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 30);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 31);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 32);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 33);

INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 30);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 31);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 32);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 33);

INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 30);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 31);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 32);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 33);

INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (13, 30);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (13, 31);


-- service_domain表中增加字段

ALTER TABLE service_domain ADD COLUMN `is_senior` bool DEFAULT false NOT NULL;
ALTER TABLE service_domain ADD COLUMN `service_alias` varchar(32) DEFAULT '';
ALTER TABLE service_domain ADD COLUMN `group_name` varchar(32) DEFAULT '';
ALTER TABLE service_domain ADD COLUMN `domain_path` varchar(256) DEFAULT '' NULL;
ALTER TABLE service_domain ADD COLUMN `domain_cookie` varchar(256) DEFAULT '' NULL;
ALTER TABLE service_domain ADD COLUMN `domain_heander` varchar(256) DEFAULT '' NULL;



