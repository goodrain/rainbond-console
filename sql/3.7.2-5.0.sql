-- 新增访问控制、证书管理权限（仅团队创建者和管理员拥有）
INSERT INTO `tenant_permission_group` (`group_name`) VALUES ('网关相关');

INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('access_control', '查看访问控制', 1, NULL, 3);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('control_operation', '访问控制操作', 1, NULL, 3);

INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('certificate_management', '访问证书管理', 1, NULL, 3);
INSERT INTO `tenant_user_permission` (`codename`, `per_info`, `is_select`, `per_explanation`, `group`) VALUES ('certificate_operation', '证书管理操作', 1, NULL, 3);

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
ALTER TABLE service_domain ADD COLUMN `domain_path`  TEXT NULL;
ALTER TABLE service_domain ADD COLUMN `domain_cookie` TEXT NULL;
ALTER TABLE service_domain ADD COLUMN `domain_heander` TEXT NULL;
ALTER TABLE service_domain ADD COLUMN `http_rule_id` varchar(128) DEFAULT '' NULL;
ALTER TABLE service_domain ADD COLUMN `type` integer DEFAULT 0;
ALTER TABLE service_domain ADD COLUMN `the_weight` integer DEFAULT 100;
ALTER TABLE service_domain ADD COLUMN `tenant_id` varchar(32) DEFAULT '';
ALTER TABLE service_domain ADD COLUMN `g_id` varchar(32) DEFAULT '';
ALTER TABLE service_domain ADD COLUMN `rule_extensions` TEXT NULL;
ALTER TABLE service_domain ADD COLUMN `region_id` varchar(32) DEFAULT '';
ALTER TABLE service_domain ADD COLUMN `is_outer_service` bool DEFAULT true NOT NULL;




-- 创建表service_tcp_domain

CREATE TABLE `service_tcp_domain` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `service_id` varchar(32),
  `service_name` varchar(32),
  `end_point` varchar(256),
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `container_port` int(11) DEFAULT 0,
  `service_alias` varchar(32) DEFAULT '',
  `group_name` varchar(32) DEFAULT '',
  `protocol` varchar(15) DEFAULT '',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;

ALTER TABLE service_tcp_domain ADD COLUMN `tcp_rule_id` varchar(128) DEFAULT '' NULL;
ALTER TABLE service_tcp_domain ADD COLUMN `tenant_id` varchar(32) DEFAULT '';
ALTER TABLE service_tcp_domain ADD COLUMN `type` integer DEFAULT 0;
ALTER TABLE service_tcp_domain ADD COLUMN `g_id` varchar(32) DEFAULT '';
ALTER TABLE service_tcp_domain ADD COLUMN `rule_extensions` TEXT NULL;
ALTER TABLE service_tcp_domain ADD COLUMN `region_id` varchar(32) DEFAULT '';
ALTER TABLE service_tcp_domain ADD COLUMN `is_outer_service` bool DEFAULT true NOT NULL;




-- 修改service_domain_certificate

ALTER TABLE service_domain_certificate ADD COLUMN `certificate_id` varchar(256) DEFAULT '' NOT NULL;
ALTER TABLE service_domain_certificate ADD COLUMN `certificate_type` varchar(64) DEFAULT '' NOT NULL;

-- 删除数据库表
drop table service_exec


-- tenant_service表中增加字段

ALTER TABLE tenant_service ADD COLUMN `build_upgrade` bool DEFAULT true NOT NULL;

ALTER TABLE tenant_service ADD COLUMN `service_name` varchar(100) DEFAULT '';

-- tenant_service_delete表中增加字段

ALTER TABLE tenant_service_delete ADD COLUMN `build_upgrade` bool DEFAULT true NOT NULL;

ALTER TABLE tenant_service_delete ADD COLUMN `service_name` varchar(100) DEFAULT '';



-- 批量修改组表中默认组——>>默认应用

update service_group set group_name = replace(group_name , '默认组' , '默认应用')

-- 修改service_event操作说明字段格式

ALTER TABLE service_event MODIFY `message` TEXT;


-- 修改service_group字段group_name长度最大值

alter table service_group modify column group_name varchar(128);
