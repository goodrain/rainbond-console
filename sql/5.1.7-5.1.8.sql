
-- 2019-10-10 新增团队相关权限（拥有者以上级别拥有）
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('tenant_close_region', '关闭数据中心', 1, NULL, 1);


INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 37);


INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 37);


-- 2019-10-10 为租户与数据中心关系表添加逻辑删除字段
ALTER TABLE tenant_region ADD COLUMN is_deleted TINYINT DEFAULT FALSE,
