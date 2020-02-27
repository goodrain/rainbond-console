-- tenant_service
alter table tenant_service modify column extend_method varchar(32) DEFAULT "stateless_multiple";
alter table tenant_service modify volume_type varchar(64) DEFAULT NULL;

-- tenant_service_volume
alter table tenant_service_volume add volume_capacity int(11) NOT NULL DEFAULT '0';
alter table tenant_service_volume add  access_mode varchar(100) DEFAULT NULL;
alter table tenant_service_volume add  share_policy varchar(100) DEFAULT NULL;
alter table tenant_service_volume modify volume_type varchar(64) DEFAULT NULL;
alter table tenant_service_volume add volume_provider_name varchar(100) DEFAULT NULL;
alter table tenant_service_volume add  backup_policy varchar(100) DEFAULT NULL;
alter table tenant_service_volume add  reclaim_policy varchar(100) DEFAULT NULL;
alter table tenant_service_volume add  allow_expansion tinyint(1) DEFAULT NULL;

-- tenant_service_delete
alter table tenant_service_delete modify volume_type varchar(64) DEFAULT NULL;

-- tenant_service_recycle_bin
alter table tenant_service_recycle_bin modify volume_type varchar(64) DEFAULT NULL;

-- rainbond_center_app
alter table rainbond_center_app change group_key app_id varchar(64) DEFAULT NULL;
alter table rainbond_center_app change group_name app_name varchar(64) DEFAULT NULL;
alter table rainbond_center_app change version dev_status varchar(64) DEFAULT 'release';
alter table rainbond_center_app change share_user create_user varchar(64) DEFAULT NULL;
alter table rainbond_center_app change share_team create_team varchar(64) DEFAULT NULL;
alter table rainbond_center_app drop column template_version;
alter table rainbond_center_app drop column is_complete;
alter table rainbond_center_app drop column app_template;
alter table rainbond_center_app drop column record_id;
-- TODO create_user， create_team, app_template, record_id字段不明确

-- app_import_record
alter table app_import_record add column `enterprise_id` varchar(64) default null;

CREATE TABLE `rainbond_center_app_version` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `enterprise_id` varchar(32) NOT NULL,
  `app_id` varchar(32) NOT NULL,
  `version` varchar(32) NOT NULL,
  `app_alias` varchar(32) NOT NULL DEFAULT 'NA',
  `app_version_info` varchar(255) NOT NULL,
  `record_id` int(11) NOT NULL,
  `share_user` int(11) NOT NULL,
  `share_team` varchar(64) NOT NULL,
  `group_id` int(11) NOT NULL,
  `dev_status` varchar(32) DEFAULT NULL,
  `source` varchar(15) DEFAULT NULL,
  `scope` varchar(15) DEFAULT NULL,
  `app_template` longtext NOT NULL,
  `template_version` varchar(10) NOT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  `upgrade_time` varchar(30) NOT NULL,
  `install_number` int(11) NOT NULL,
  `is_official` tinyint(1) NOT NULL,
  `is_ingerit` tinyint(1) NOT NULL,
  `is_complete` tinyint(1) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `rainbond_center_app_vers_app_id_version_enterpris_d5151505_uniq` (`app_id`,`version`,`enterprise_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8;

CREATE TABLE `rainbond_center_app_tag_relation` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `enterprise_id` varchar(36) NOT NULL,
  `app_id` varchar(32) NOT NULL,
  `tag_id` int(11) NOT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8;

CREATE TABLE `rainbond_center_app_tag` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(32) NOT NULL,
  `enterprise_id` varchar(32) NOT NULL,
  `is_deleted` tinyint(1) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8;

alter table service_share_record add column app_id varchar(64) NOT NULL;
alter table service_share_record add column scope varchar(64) NOT NULL;
alter table service_share_record add column share_app_market_id varchar(64) NOT NULL;

alter table service_group add column note varchar(2048) NOT NULL;

alter table service_plugin_config_var add column min_memory int(11) NOT NULL;
alter table service_plugin_config_var add column min_cpu int(11) NOT NULL;
alter table service_plugin_config_var add column plugin_status tinyint(1) NOT NULL;