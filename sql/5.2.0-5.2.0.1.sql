alter table user_info add enterprise_center_user_id varchar(32) DEFAULT NULL;
alter table user_info add real_name varchar(64) DEFAULT NULL;

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

alter table tenant_service_delete modify version varchar(32) DEFAULT NULL;

CREATE TABLE IF NOT EXISTS `errlog` (
  `ID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `note` varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
