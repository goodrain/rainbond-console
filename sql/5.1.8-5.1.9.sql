CREATE TABLE `oauth_service` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(64) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT '0',
  `client_id` varchar(64) DEFAULT NULL,
  `client_secret` varchar(64) DEFAULT NULL,
  `redirect_uri` varchar(256) DEFAULT NULL,
  `home_url` varchar(256) DEFAULT NULL,
  `auth_url` varchar(256) DEFAULT NULL,
  `access_token_url` varchar(256) DEFAULT NULL,
  `api_url` varchar(256) DEFAULT NULL,
  `oauth_type` varchar(16) DEFAULT NULL,
  `eid` varchar(32) DEFAULT NULL,
  `enable` tinyint(2) DEFAULT '1',
  `is_deleted` tinyint(2) DEFAULT '0',
  `is_console` tinyint(2) DEFAULT '0',
  `is_auto_login` tinyint(2) DEFAULT '0',
  `is_git` tinyint(2) DEFAULT '0',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=98 DEFAULT CHARSET=utf8;


CREATE TABLE `user_oauth_service` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `service_id` int(11) DEFAULT NULL,
  `is_auto_login` tinyint(2) DEFAULT NULL,
  `is_authenticated` tinyint(2) DEFAULT NULL,
  `is_expired` tinyint(2) DEFAULT NULL,
  `access_token` varchar(256) DEFAULT NULL,
  `oauth_user_id` varchar(64) DEFAULT NULL,
  `oauth_user_name` varchar(64) DEFAULT '',
  `oauth_user_email` varchar(64) DEFAULT '',
  `refresh_token` varchar(64) DEFAULT NULL,
  `code` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=87 DEFAULT CHARSET=utf8;

-- **2019-11-26 在tenant_service表中增加oauth_service_id字段，用来记录源码创建使用的oauth服务id
alter table console.tenant_service add column oauth_service_id int(11) null default null;
alter table console.tenant_service add column git_full_name varchar(64) null default null;
