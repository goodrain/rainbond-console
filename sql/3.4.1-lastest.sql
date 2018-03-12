-- 添加应用更新时间字段
ALTER TABLE tenant_service ADD update_time DATETIME DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE tenant_service_delete ADD update_time DATETIME DEFAULT CURRENT_TIMESTAMP;

-- 数据中心加描述字段
ALTER TABLE region_info ADD `desc` VARCHAR(128) DEFAULT "" NULL;

-- 修改超级管理员字段
ALTER TABLE user_administrator DROP email;
ALTER TABLE user_administrator ADD user_id INT(11)  NULL;


-- =========================3.5===============================
-- app_service
ALTER TABLE `app_service` ADD `update_version` INT(11) NULL DEFAULT 1;

-- app_service_volume
ALTER TABLE `app_service_volume` ADD `volume_type` VARCHAR(30) NULL DEFAULT '';
ALTER TABLE `app_service_volume` ADD `volume_name` VARCHAR(100) NULL DEFAULT '';


-- app_service_group
ALTER TABLE `app_service_group` ADD `deploy_time` datetime DEFAULT NULL;
ALTER TABLE `app_service_group` ADD `installed_count` INT(11) NULL DEFAULT 0;
ALTER TABLE `app_service_group` ADD `source` VARCHAR(32) NULL DEFAULT 'local';
ALTER TABLE `app_service_group` ADD `enterprise_id` INT(11) NULL DEFAULT 0;
ALTER TABLE `app_service_group` ADD `share_scope` VARCHAR(20) NULL DEFAULT '';
ALTER TABLE `app_service_group` ADD `is_publish_to_market` tinyint(1) DEFAULT 0;


-- tenant_service
ALTER TABLE `tenant_service` ADD `tenant_service_group_id` INT(11) NULL DEFAULT 0;
ALTER TABLE `tenant_service_delete` ADD `tenant_service_group_id` INT(11) NULL DEFAULT 0;


CREATE TABLE `tenant_service_group` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `tenant_id` varchar(32) DEFAULT NULL,
  `group_name` varchar(64) DEFAULT NULL,
  `group_alias` varchar(64) DEFAULT NULL,
  `group_key` varchar(32) DEFAULT NULL,
  `group_version` varchar(32) DEFAULT NULL,
  `region_name` varchar(20) DEFAULT NULL,
  `service_group_id` int(11) DEFAULT '0',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;



CREATE TABLE `tenant_enterprise_token` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `enterprise_id` int(11) DEFAULT 0,
  `access_target` varchar(32) DEFAULT NULL,
  `access_url` varchar(256) DEFAULT NULL,
  `access_id` varchar(32) DEFAULT NULL,
  `access_token` varchar(256) DEFAULT NULL,
  `key` text DEFAULT NULL,
  `crt` text DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;


CREATE TABLE `tenant_region_resource` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `enterprise_id` varchar(32) NOT NULL DEFAULT '',
  `tenant_id` varchar(32) DEFAULT NULL,
  `region_name` varchar(20) DEFAULT NULL,
   `memory_limit` int(11) DEFAULT 0,
  `memory_expire_date` datetime DEFAULT NULL,
   `disk_limit` int(11) DEFAULT 0,
  `disk_expire_date` datetime DEFAULT NULL,
   `net_limit` int(11) DEFAULT 0,
   `net_stock` int(11) DEFAULT 0,
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;


-- 新建'云市应用包'表
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
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX rainbond_center_app_group_key_uindex ON rainbond_center_app (group_key);
ALTER TABLE rainbond_center_app COMMENT = '云市应用包';


-- 新建'云市应用组继承关系'表
CREATE TABLE rainbond_center_app_inherit
(
    ID INT(11) NOT NULL PRIMARY KEY AUTO_INCREMENT,
    group_key VARCHAR(32) NOT NULL,
    derived_group_key VARCHAR(32) NOT NULL,
    version VARCHAR(20) NOT NULL
);
CREATE UNIQUE INDEX rainbond_center_app_inherit_group_key_uindex ON rainbond_center_app_inherit (group_key);
CREATE UNIQUE INDEX rainbond_center_app_inherit_version_uindex ON rainbond_center_app_inherit (version);
CREATE UNIQUE INDEX rainbond_center_app_inherit_derived_group_key_uindex ON rainbond_center_app_inherit (derived_group_key);
ALTER TABLE rainbond_center_app_inherit COMMENT = '云市应用组继承关系';


-- 新建'云市插件'表
CREATE TABLE rainbond_center_plugin
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    plugin_key VARCHAR(32) NOT NULL,
    version VARCHAR(20) NOT NULL,
    pic VARCHAR(100),
    scope VARCHAR(10) NOT NULL,
    source VARCHAR(15),
    share_user INTEGER,
    share_team VARCHAR(32) NOT NULL,
    plugin_template TEXT,
    is_complete TINYINT DEFAULT FALSE,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX rainbond_center_app_inherit_plugin_key_uindex ON rainbond_center_plugin (plugin_key);
CREATE UNIQUE INDEX rainbond_center_app_inherit_version_uindex ON rainbond_center_plugin (version);
ALTER TABLE rainbond_center_app_inherit COMMENT = '云市插件';


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
    create_time DATETIME DEFAULT now(),
    update_time DATETIME DEFAULT now()
);
ALTER TABLE service_share_record COMMENT = '服务分享记录';

-- 新建"服务分享事件记录"表
CREATE TABLE `service_share_record_event` (
 `ID` int(11) NOT NULL AUTO_INCREMENT,
 `record_id` varchar(32) DEFAULT NULL,
 `team_name` varchar(32) DEFAULT NULL,
 `event_id` varchar(32) DEFAULT NULL,
 `event_status` varchar(32) DEFAULT 'not_start',
 `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
 `update_time` datetime DEFAULT CURRENT_TIMESTAMP,
 `team_id` varchar(32) NOT NULL,
 `service_key` varchar(32) NOT NULL,
 `service_id` varchar(32) NOT NULL,
 `region_share_id` varchar(36) NOT NULL,
 PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8;
ALTER TABLE service_share_record_event COMMENT = '服务分享事件记录';
ALTER TABLE `service_share_record_event` ADD `service_name` VARCHAR(100) NOT NULL;
ALTER TABLE `service_share_record_event` ADD `service_alias` VARCHAR(10) NOT NULL;


ALTER TABLE region_info ADD wsurl varchar(256) DEFAULT "ws://region.goodrain.me:6060";
ALTER TABLE region_info ADD httpdomain varchar(256) DEFAULT NULL;
ALTER TABLE region_info ADD tcpdomain varchar(256) DEFAULT NULL;
-- tenant_service 表添加字段check_uuid
ALTER TABLE tenant_service ADD check_uuid VARCHAR(36) DEFAULT "";


-- 新建tenant_service_extend_method(应用伸缩方式)表
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
    is_restart TINYINT DEFAULT FALSE
);
ALTER TABLE tenant_service_extend_method COMMENT = '应用伸缩方式';


-- 新建 compose_group compose文件和组关系表
CREATE TABLE compose_group
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    group_id INT(11) NOT  NULL ,
    team_id VARCHAR(32) NOT NULL ,
    region VARCHAR(15) NOT NULL ,
    compose_content VARCHAR(4096),
    compose_id VARCHAR(32) NOT NULL,
    create_status VARCHAR(15) NOT NULL,
    check_uuid VARCHAR(36) DEFAULT "",
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 新建 compose文件和服务关系表
CREATE TABLE compose_service_relation
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    team_id VARCHAR(32) NOT NULL ,
    service_id VARCHAR(32) NOT NULL ,
    compose_id VARCHAR(32) NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- 新建表service_source 服务源信息
CREATE TABLE service_source
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    service_id VARCHAR(32) NOT NULL ,
    tenant_id VARCHAR(32) NOT NULL,
    user_name VARCHAR(32) DEFAULT "",
    password VARCHAR(32) DEFAULT "",
    extend_info VARCHAR(1024) DEFAULT "",
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE tenant_service ADD check_event_id VARCHAR(32) DEFAULT "";
ALTER TABLE compose_group ADD check_event_id VARCHAR(32) DEFAULT "";

-- 新建表team_gitlab_info 团队代码gitlab代码仓库信息
CREATE TABLE team_gitlab_info
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    team_id VARCHAR(32) NOT NULL,
    respo_url VARCHAR(100) DEFAULT "",
    git_project_id int(11) DEFAULT 0,
    code_version VARCHAR(100) DEFAULT "master",
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

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
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `check_uuid` varchar(36) DEFAULT '',
  `check_event_id` varchar(32) DEFAULT '',
  `docker_cmd` varchar(1024) DEFAULT '',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `service_id` (`service_id`),
  UNIQUE KEY `tenant_id` (`tenant_id`,`service_alias`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


ALTER TABLE tenant_service ADD docker_cmd VARCHAR (1024) DEFAULT "";
ALTER TABLE tenant_service ADD service_source VARCHAR (15) DEFAULT "";
ALTER TABLE tenant_service ADD create_status VARCHAR (15) DEFAULT 'complete';

ALTER TABLE tenant_service_delete ADD docker_cmd VARCHAR (1024) DEFAULT "";
ALTER TABLE tenant_service_delete ADD service_source VARCHAR (15) DEFAULT "";
ALTER TABLE tenant_service_delete ADD create_status VARCHAR (15) DEFAULT 'complete';



