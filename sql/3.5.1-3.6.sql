-- 修改插件配置项，添加协议字段
ALTER TABLE plugin_config_items ADD protocol VARCHAR(32) DEFAULT '' NULL;

CREATE TABLE service_plugin_config_var
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    service_id VARCHAR(32) NOT NULL,
    plugin_id VARCHAR(32) NOT NULL,
    build_version VARCHAR(32) NOT NULL,
    service_meta_type VARCHAR(32) NOT NULL,
    injection VARCHAR(32) NOT NULL,
    dest_service_id VARCHAR(32) NOT NULL,
    dest_service_alias VARCHAR(32) NOT NULL,
    container_port INT(11) NOT NULL,
    attrs VARCHAR(256) DEFAULT '',
    protocol VARCHAR(16) DEFAULT '',
    create_time DATETIME
);


CREATE TABLE app_export_record
(
    ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    group_key VARCHAR(32) NOT NULL,
    version VARCHAR(20) NOT NULL,
    format VARCHAR(15) DEFAULT '',
    event_id VARCHAR(32) DEFAULT '',
    status VARCHAR(10) DEFAULT '',
    file_path VARCHAR(256) DEFAULT '',
    create_time DATETIME,
    update_time DATETIME
);


-- 创建角色表，权限表，角色权限关系表,权限组表,应用权限表
CREATE TABLE `tenant_user_role` (`ID` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `role_name` varchar(32) NOT NULL, `tenant_id` integer NULL, `is_default` bool NOT NULL, UNIQUE (`role_name`, `tenant_id`));
CREATE TABLE `tenant_user_permission` (`ID` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `codename` varchar(32) NOT NULL, `per_info` varchar(32) NOT NULL, `is_select` bool NOT NULL, `group` integer NULL, `per_explanation` varchar(132) NULL, UNIQUE (`codename`, `per_info`));
CREATE TABLE `tenant_user_role_permission` (`ID` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `role_id` integer NOT NULL, `per_id` integer NOT NULL);
CREATE TABLE `tenant_permission_group` (`ID` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `group_name` varchar(64) NOT NULL);
CREATE TABLE `service_user_perms` (`ID` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `user_id` integer NOT NULL, `service_id` integer NOT NULL, `perm_id` integer NOT NULL);

-- 在原来的用户在团队中的身份表，用户在服务中的身份表中 添加'role_id'字段
ALTER TABLE `service_perms` ADD COLUMN `role_id` integer NULL;
ALTER TABLE `tenant_perms` ADD COLUMN `role_id` integer NULL;
ALTER TABLE `service_perms` MODIFY `identity` varchar(15) NULL;
ALTER TABLE `tenant_perms` MODIFY `identity` varchar(15) NULL;

-- 初始化默认角色
INSERT INTO `tenant_user_role` (`role_name`, `tenant_id`, `is_default`) VALUES ('owner', NULL, 1);
INSERT INTO `tenant_user_role` (`role_name`, `tenant_id`, `is_default`) VALUES ('admin', NULL, 1);
INSERT INTO `tenant_user_role` (`role_name`, `tenant_id`, `is_default`) VALUES ('developer', NULL, 1);
INSERT INTO `tenant_user_role` (`role_name`, `tenant_id`, `is_default`) VALUES ('viewer', NULL, 1);

-- 初始化默认权限组
INSERT INTO `tenant_permission_group` (`group_name`) VALUES ('团队相关');
INSERT INTO `tenant_permission_group` (`group_name`) VALUES ('应用相关');

-- 初始化权限信息
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('tenant_access', '登入团队', 1, NULL, 1);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('manage_team_member_permissions', '团队权限设置', 1, NULL, 1);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('tenant_open_region', '开通数据中心', 1, NULL, 1);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('manage_group', '应用组管理', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('view_service', '查看应用信息', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('deploy_service', '部署应用', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('create_service', '创建应用', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('delete_service', '删除应用', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('share_service', '应用组分享', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('stop_service', '关闭应用', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('start_service', '启动应用', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('restart_service', '重启应用', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('rollback_service', '回滚应用', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('manage_service_container', '应用容器管理', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('manage_service_extend', '应用伸缩管理', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('manage_service_config', '应用配置管理', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('manage_service_plugin', '应用扩展管理', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('manage_service_member_perms', '应用权限设置', 1, NULL, 2);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('view_plugin', '查看插件信息', 1, NULL, 1);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('manage_plugin', '插件管理', 1, NULL, 1);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('drop_tenant', '删除团队', 0, NULL, 1);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('transfer_ownership', '移交所有权', 0, NULL, 1);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('modify_team_name', '修改团队名称', 0, NULL, 1);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('tenant_manage_role', '自定义角色', 0, NULL, 1);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('import_and_export_service', '导入导出云市应用', 1, NULL, 1);


-- 初始化角色和权限的对应关系
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 1);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 2);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 3);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 4);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 5);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 6);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 7);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 8);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 9);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 10);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 11);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 12);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 13);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 14);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 15);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 16);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 17);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 18);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 19);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 20);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 21);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 22);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 23);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 24);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (1, 25);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 1);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 2);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 3);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 4);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 5);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 6);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 7);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 8);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 9);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 10);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 11);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 12);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 13);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 14);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 15);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 16);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 17);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 18);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 19);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 20);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 24);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (2, 25);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 1);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 4);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 5);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 6);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 7);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 10);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 11);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 12);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 13);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 14);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 15);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 16);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 17);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 19);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 20);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (3, 25);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (4, 1);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (4, 5);
INSERT INTO `tenant_user_role_permission` (`role_id`, `per_id`) VALUES (4, 19);
