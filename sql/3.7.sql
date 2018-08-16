
-- 云市应用官方认证及安装量排序增加字段
ALTER TABLE `rainbond_center_app` ADD COLUMN `install_number` INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE `rainbond_center_app` ADD COLUMN `is_official` bool DEFAULT false NOT NULL;


-- 云帮应用添加server_type字段
ALTER TABLE `tenant_service` ADD COLUMN `server_type` varchar(5) default 'git';
ALTER TABLE `tenant_service_delete` ADD COLUMN `server_type` varchar(5) default 'git';

-- 添加用户申请加入团队表
CREATE TABLE applicants
(
    id int PRIMARY KEY NOT NULL AUTO_INCREMENT,
    user_id int NOT NULL,
    user_name varchar(20) NOT NULL,
    team_id varchar(33) NOT NULL,
    team_name varchar(20) NOT NULL,
    apply_time datetime NOT NULL,
    team_alias varchar(30) NOT NULL,
    is_pass int DEFAULT 0  NOT NULL
);
CREATE UNIQUE INDEX applicants_id_uindex ON applicants (id);


-- 添加自动触发部署关系表
CREATE TABLE deploy_relation
(
    id int PRIMARY KEY NOT NULL AUTO_INCREMENT,
    service_id varchar(32) NOT NULL,
    secret_key varchar(200) NOT NULL,
    key_type varchar(10) NULL 
);

-- 添加https认证信息路径

ALTER TABLE region_info ADD ssl_ca_cert varchar(128) NULL;
ALTER TABLE region_info ADD cert_file varchar(128) NULL;
ALTER TABLE region_info ADD key_file varchar(128) NULL;