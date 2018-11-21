-- 新增访问控制、证书管理权限（仅团队创建者和管理员拥有）
INSERT INTO `tenant_permission_group` (`group_name`) VALUES ('网关相关');

INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('access control', '访问控制', 1, NULL, 3);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('certificate management', '证书管理', 1, NULL, 3);

INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 30);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 31);

INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 30);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 31);
