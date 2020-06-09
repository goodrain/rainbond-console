alter table user_info add enterprise_center_user_id varchar(32) DEFAULT NULL;
alter table user_info add real_name varchar(64) DEFAULT NULL;

alter table region_info add region_type varchar(32) DEFAULT '[]';
alter table region_info add enterprise_id varchar(32) DEFAULT NULL;

alter table console_sys_config add enterprise_id varchar(32) DEFAULT NULL;
alter table tenant_enterprise add logo varchar(128) DEFAULT NULL;

CREATE TABLE `user_access_key` (
  `ID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `note` varchar(32) NOT NULL DEFAULT '',
  `access_key` varchar(64) NOT NULL DEFAULT '',
  `expire_time` int(16) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `note` (`note`,`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

alter table service_share_record add share_version_alias varchar(32) DEFAULT NULL;

CREATE TABLE IF NOT EXISTS `errlog` (
  `ID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `msg` varchar(2047) NOT NULL DEFAULT '',
  `username` varchar(255) NOT NULL DEFAULT '',
  `enterprise_id` varchar(255) NOT NULL DEFAULT '',
  `address` varchar(2047) NOT NULL DEFAULT '',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

alter table service_group add order_index int(16) DEFAULT 0;

alter table service_domain add auto_ssl TINYINT(1) DEFAULT 0;
alter table service_domain add auto_ssl_config varchar(32) DEFAULT NULL;
alter table console.tenant_service_delete modify version varchar(255);

alter table console.tenant_service_delete modify version varchar(255);

CREATE TABLE `user_role` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `role_id` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=91 DEFAULT CHARSET=utf8;

CREATE TABLE `perms_info` (
  `ID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(32) NOT NULL DEFAULT '',
  `desc` varchar(64) NOT NULL DEFAULT '',
  `code` int(11) NOT NULL,
  `group` varchar(32) NOT NULL DEFAULT '',
  `kind` varchar(32) NOT NULL DEFAULT '',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `unique_name` (`name`),
  UNIQUE KEY `un_code` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=1339 DEFAULT CHARSET=utf8;

CREATE TABLE `role_perms` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `role_id` int(11) NOT NULL,
  `perm_code` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5632 DEFAULT CHARSET=utf8;

CREATE TABLE `role_info` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(32) NOT NULL DEFAULT '',
  `kind_id` varchar(64) NOT NULL DEFAULT '',
  `kind` varchar(32) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=96 DEFAULT CHARSET=utf8;

alter table console.tenant_info modify region varchar(64);

alter table console.compose_group modify region varchar(64);
alter table console.tenant_service_recycle_bin modify service_region varchar(64);
alter table console.service_attach_info modify region varchar(64);
alter table console.service_consume modify region varchar(64);
alter table console.tenant_service_statics modify region varchar(64);
alter table console.tenant_plugin modify region varchar(64);
alter table console.plugin_build_version modify region varchar(64);