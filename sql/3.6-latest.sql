CREATE TABLE user_message
(
    ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    message_id VARCHAR(32),
    receiver_id INT,
    content VARCHAR(256),
    is_read TINYINT DEFAULT 0,
    create_time DATETIME,
    update_time DATETIME,
    msg_type VARCHAR(32),
    announcement_id VARCHAR(32),
    title VARCHAR(64) NOT NULL ,
    level VARCHAR(32) NOT NULL
);

CREATE TABLE app_import_record
(
    ID INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    event_id VARCHAR(32) DEFAULT '',
    status VARCHAR(15) DEFAULT '',
    scope VARCHAR(15) DEFAULT '',
    format VARCHAR(15) DEFAULT '',
    source_dir VARCHAR(256) DEFAULT '',
    team_name VARCHAR(32) DEFAULT '',
    region VARCHAR(32) DEFAULT '',
    create_time DATETIME,
    update_time DATETIME
);

CREATE TABLE groupapp_backup
(
    ID INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    group_id INT,
    group_uuid VARCHAR(32),
    note VARCHAR(128) DEFAULT '',
    mode VARCHAR(15) NOT NULL,
    version VARCHAR(32) NOT NULL ,
    team_id VARCHAR(32) NOT NULL ,
    user VARCHAR(32) NOT NULL ,
    backup_id VARCHAR(36) NOT NULL ,
    region VARCHAR(15) NOT NULL ,
    event_id VARCHAR(32) NOT NULL ,
    status VARCHAR(15),
    source_dir VARCHAR(256) DEFAULT '',
    backup_server_info VARCHAR(256) DEFAULT '',
    backup_size INT DEFAULT 0,
    total_memory INT DEFAULT 0,
    source_type VARCHAR (32) DEFAULT '',
    create_time DATETIME
);

-- 自动触发部署功能添加字段
ALTER TABLE `tenant_service` ADD COLUMN `secret` varchar(64) NULL;
ALTER TABLE `tenant_service` ADD COLUMN `open_webhooks` bool DEFAULT false NOT NULL;

ALTER TABLE `tenant_service_delete` ADD COLUMN `secret` varchar(64) NULL;
ALTER TABLE `tenant_service_delete` ADD COLUMN `open_webhooks` bool DEFAULT false NOT NULL;

-- 站内信添加标题，等级字段
ALTER TABLE `announcement` ADD COLUMN `title` varchar(64) DEFAULT 'title' NOT NULL;
ALTER TABLE `announcement` ADD COLUMN `level` varchar(32) DEFAULT 'low' NOT NULL;

-- 增加字段长度
ALTER TABLE `announcement` MODIFY `type` varchar(32);

-- 应用迁移表
CREATE TABLE groupapp_migrate
(
    ID int PRIMARY KEY NOT NULL AUTO_INCREMENT,
    group_id int,
    event_id varchar(32),
    group_uuid varchar(32) NOT NULL,
    version varchar(32),
    backup_id varchar(36),
    migrate_team varchar(32),
    user varchar(20),
    migrate_region varchar(15),
    status varchar(15),
    restore_id varchar(36) default null ,
    create_time datetime
);
CREATE UNIQUE INDEX groupapp_migrate_ID_uindex ON groupapp_migrate (ID);