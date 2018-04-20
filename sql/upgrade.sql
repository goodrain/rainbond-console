-- 新建表compose_group
CREATE TABLE `compose_group` (
  `ID` int(11)  PRIMARY KEY NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `team_id` varchar(32) NOT NULL,
  `region` varchar(15) NOT NULL,
  `compose_content` varchar(4096) DEFAULT NULL,
  `compose_id` varchar(32) NOT NULL,
  `create_status` varchar(15) NOT NULL,
  `check_uuid` varchar(36) DEFAULT '',
  `create_time` datetime  DEFAULT NULL,
  `check_event_id` varchar(32) DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
-- 新建 compose文件和服务关系表
CREATE TABLE compose_service_relation
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    team_id VARCHAR(32) NOT NULL ,
    service_id VARCHAR(32) NOT NULL ,
    compose_id VARCHAR(32) NOT NULL,
    create_time DATETIME DEFAULT NULL
);

-- 新建 rainbond_center_app 表
CREATE TABLE rainbond_center_app
(
    ID INT(11) NOT NULL PRIMARY KEY AUTO_INCREMENT,
    group_key VARCHAR(32) NOT NULL,
    group_name VARCHAR(64) NOT NULL,
    share_user INTEGER NOT NULL,
    share_team VARCHAR(32) NOT NULL,
    record_id int(11),
    tenant_service_group_id INTEGER DEFAULT 0 NOT NULL,
    pic VARCHAR(100),
    `describe` VARCHAR(400),
    source VARCHAR(15),
    version VARCHAR(20) NOT NULL,
    scope VARCHAR(10),
    app_template TEXT,
    is_complete TINYINT DEFAULT FALSE,
    is_ingerit TINYINT DEFAULT TRUE,
    create_time DATETIME DEFAULT NULL,
    update_time DATETIME DEFAULT NULL
);
-- 创建rainbond_center_app 索引文件
CREATE UNIQUE INDEX rainbond_center_app_group_key_uindex ON rainbond_center_app (group_key);
--
-- 表的结构 `rainbond_center_app_inherit`
--
CREATE TABLE `rainbond_center_app_inherit` (
  `ID` int(11) NOT NULL PRIMARY KEY AUTO_INCREMENT,
  `group_key` varchar(32) NOT NULL,
  `derived_group_key` varchar(32) NOT NULL,
  `version` varchar(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='云市插件';
-- 添加rainbond_center_app_inherit索引
CREATE UNIQUE INDEX rainbond_center_app_inherit_group_key_uindex ON rainbond_center_app_inherit (group_key);
CREATE UNIQUE INDEX rainbond_center_app_inherit_version_uindex ON rainbond_center_app_inherit (version);
CREATE UNIQUE INDEX rainbond_center_app_inherit_derived_group_key_uindex ON rainbond_center_app_inherit (derived_group_key);
--
-- 添加表 `rainbond_center_plugin`
--
CREATE TABLE `rainbond_center_plugin` (
  `ID` int(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
  `plugin_key` varchar(32) NOT NULL,
  `version` varchar(20) NOT NULL,
  `pic` varchar(100) DEFAULT NULL,
  `scope` varchar(10) NOT NULL,
  `source` varchar(15) DEFAULT NULL,
  `share_user` int(11) DEFAULT NULL,
  `share_team` varchar(32) NOT NULL,
  `plugin_template` text,
  `is_complete` tinyint(4) DEFAULT '0',
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
-- 添加索引
CREATE UNIQUE INDEX rainbond_center_app_inherit_plugin_key_uindex ON rainbond_center_plugin (plugin_key);
CREATE UNIQUE INDEX rainbond_center_app_inherit_version_uindex ON rainbond_center_plugin (version);
-- 新建"服务分享记录"表
CREATE TABLE service_share_record
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    group_share_id VARCHAR(32),
    group_id VARCHAR(32),
    team_name VARCHAR(32),
    event_id VARCHAR(32),
    share_version VARCHAR(15) DEFAULT "V1.0",
    is_success TINYINT(1),
    step INT(3) DEFAULT 0,
    create_time DATETIME DEFAULT NULL ,
    update_time DATETIME DEFAULT NULL
);
ALTER TABLE service_share_record COMMENT = '服务分享记录';
-- 新建"服务分享事件记录"表
CREATE TABLE `service_share_record_event` (
 `ID` int(11) NOT NULL AUTO_INCREMENT,
 `record_id` varchar(32) DEFAULT NULL,
 `team_name` varchar(32) DEFAULT NULL,
 `event_id` varchar(32) DEFAULT NULL,
 `event_status` varchar(32) DEFAULT 'not_start',
 `create_time` datetime DEFAULT NULL,
 `update_time` datetime DEFAULT NULL,
 `team_id` varchar(32) NOT NULL,
 `service_key` varchar(32) NOT NULL,
 `service_id` varchar(32) NOT NULL,
 `region_share_id` varchar(36) NOT NULL,
 PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8;
ALTER TABLE service_share_record_event COMMENT = '服务分享事件记录';
ALTER TABLE `service_share_record_event` ADD `service_name` VARCHAR(100) NOT NULL;
ALTER TABLE `service_share_record_event` ADD `service_alias` VARCHAR(10) NOT NULL;

CREATE TABLE tenant_service_extend_method
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    service_key VARCHAR(32),
    version VARCHAR(20) NOT NULL,
    min_node INTEGER DEFAULT 1,
    max_node INTEGER DEFAULT 20,
    step_node INTEGER DEFAULT 1,
    min_memory INTEGER DEFAULT 1,
    max_memory INTEGER DEFAULT 20,
    step_memory INTEGER DEFAULT 1,
    is_restart TINYINT DEFAULT 0
);

-- 数据中心添加字段
ALTER TABLE region_info ADD `desc` VARCHAR(128) DEFAULT "" NULL;
ALTER TABLE region_info ADD wsurl varchar(256) DEFAULT "ws://region.goodrain.me:6060";
ALTER TABLE region_info ADD httpdomain varchar(256) DEFAULT NULL;
ALTER TABLE region_info ADD tcpdomain varchar(256) DEFAULT NULL;

-- 创建表region_property
CREATE TABLE `region_property` (
  `ID` int(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
  `region` varchar(16) NOT NULL,
  `property` varchar(32) NOT NULL,
  `value` varchar(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 创建服务源信息表
CREATE TABLE service_source
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    service_id VARCHAR(32) NOT NULL ,
    team_id VARCHAR(32) NOT NULL,
    user_name VARCHAR(32) DEFAULT "",
    password VARCHAR(32) DEFAULT "",
    extend_info VARCHAR(1024) DEFAULT "",
    create_time DATETIME DEFAULT NULL
);

-- 新建表team_gitlab_info 团队代码gitlab代码仓库信息
CREATE TABLE `team_gitlab_info` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `team_id` varchar(32) NOT NULL,
  `respo_url` varchar(100) DEFAULT '',
  `git_project_id` int(11) DEFAULT '0',
  `code_version` varchar(100) DEFAULT 'master',
  `create_time` datetime DEFAULT NULL ,
  `repo_name` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 更新 tenant_service表
ALTER TABLE tenant_service ADD update_time DATETIME DEFAULT NULL;
ALTER TABLE tenant_service ADD check_uuid VARCHAR(36) DEFAULT "";
ALTER TABLE tenant_service ADD check_event_id VARCHAR(32) DEFAULT "";
ALTER TABLE tenant_service ADD docker_cmd VARCHAR (1024) DEFAULT "";
ALTER TABLE tenant_service ADD service_source VARCHAR (15) DEFAULT "";
ALTER TABLE tenant_service ADD create_status VARCHAR (15) DEFAULT 'complete';
-- 更新 tenant_service_delete表
ALTER TABLE tenant_service_delete ADD update_time DATETIME DEFAULT NULL;
ALTER TABLE tenant_service_delete ADD check_uuid VARCHAR(36) DEFAULT "";
ALTER TABLE tenant_service_delete ADD check_event_id VARCHAR(32) DEFAULT "";
ALTER TABLE tenant_service_delete ADD docker_cmd VARCHAR (1024) DEFAULT "";
ALTER TABLE tenant_service_delete ADD service_source VARCHAR (15) DEFAULT "";
ALTER TABLE tenant_service_delete ADD create_status VARCHAR (15) DEFAULT 'complete';

-- 新建表 服务回收站
CREATE TABLE `tenant_service_recycle_bin` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `service_id` varchar(32) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `service_key` varchar(32) NOT NULL,
  `service_alias` varchar(100) NOT NULL,
  `service_cname` varchar(100) NOT NULL,
  `service_region` varchar(15) NOT NULL,
  `desc` varchar(200) DEFAULT NULL,
  `category` varchar(15) NOT NULL,
  `service_port` int(11) NOT NULL,
  `is_web_service` tinyint(1) NOT NULL,
  `version` varchar(20) NOT NULL,
  `update_version` int(11) NOT NULL,
  `image` varchar(100) NOT NULL,
  `cmd` varchar(2048) DEFAULT NULL,
  `setting` varchar(100) DEFAULT NULL,
  `extend_method` varchar(15) NOT NULL,
  `env` varchar(200) DEFAULT NULL,
  `min_node` int(11) NOT NULL,
  `min_cpu` int(11) NOT NULL,
  `min_memory` int(11) NOT NULL,
  `inner_port` int(11) NOT NULL,
  `volume_mount_path` varchar(50) DEFAULT NULL,
  `host_path` varchar(300) DEFAULT NULL,
  `deploy_version` varchar(20) DEFAULT NULL,
  `code_from` varchar(20) DEFAULT NULL,
  `git_url` varchar(100) DEFAULT NULL,
  `create_time` datetime NOT NULL,
  `git_project_id` int(11) NOT NULL,
  `is_code_upload` tinyint(1) NOT NULL,
  `code_version` varchar(100) DEFAULT NULL,
  `service_type` varchar(50) DEFAULT NULL,
  `creater` int(11) NOT NULL,
  `language` varchar(40) DEFAULT NULL,
  `protocol` varchar(15) NOT NULL,
  `total_memory` int(11) NOT NULL,
  `is_service` tinyint(1) NOT NULL,
  `namespace` varchar(100) NOT NULL,
  `volume_type` varchar(15) NOT NULL,
  `port_type` varchar(15) NOT NULL,
  `service_origin` varchar(15) NOT NULL,
  `expired_time` datetime DEFAULT NULL,
  `tenant_service_group_id` int(11) DEFAULT '0',
  `service_source` varchar(15) DEFAULT NULL,
  `create_status` varchar(15) DEFAULT NULL,
  `update_time` datetime DEFAULT NULL ,
  `check_uuid` varchar(36) DEFAULT '',
  `check_event_id` varchar(32) DEFAULT '',
  `docker_cmd` varchar(1024) DEFAULT '',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `service_id` (`service_id`),
  UNIQUE KEY `tenant_id` (`tenant_id`,`service_alias`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 超级管理员添加字段
ALTER TABLE user_administrator ADD user_id INT(11)  NULL;

----- 2018.03.16

-- 新增服务依赖回收站
CREATE TABLE `tenant_service_relation_recycle_bin` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `service_id` varchar(32) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `dep_service_id` varchar(32) NOT NULL,
  `dep_service_type` varchar(50) DEFAULT '',
  `dep_order` int(11),
  PRIMARY KEY (`ID`),
  UNIQUE KEY `service_id` (`service_id`,`dep_service_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

----- 2018.03.19
ALTER TABLE rainbond_center_app ADD template_version VARCHAR(10) DEFAULT 'v2' NULL;

----- 2018.03.22 数据中心信息表添加字段 scope
ALTER TABLE region_info ADD scope VARCHAR(10) DEFAULT "private" NULL;

----- 2018.03.23 添加用户企业信息表
CREATE TABLE enterprise_user_perm
(
    id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    enterprise_id VARCHAR(32) NOT NULL ,
    user_id INT NOT NULL  ,
    identity VARCHAR(15) DEFAULT "admin"
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 2018.04.19
ALTER TABLE plugin_config_items MODIFY attr_default_value VARCHAR(128);
ALTER TABLE tenant_service_plugin_attr MODIFY attr_default_value VARCHAR(128);
ALTER TABLE tenant_service_plugin_attr MODIFY attr_value VARCHAR(128);
ALTER TABLE tenant_service_plugin_attr MODIFY attr_alt_value VARCHAR(128);