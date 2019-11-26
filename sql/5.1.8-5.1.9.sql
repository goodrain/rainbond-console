CREATE TABLE `oauth_service` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(64) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT '0',
  `client_id` varchar(64) DEFAULT NULL,
  `client_secret` varchar(64) DEFAULT NULL,
  `redirect_uri` varchar(256) DEFAULT NULL,
  `auth_url` varchar(256) DEFAULT NULL,
  `access_token_url` varchar(256) DEFAULT NULL,
  `access_token_method` varchar(16) DEFAULT NULL,
  `api_url` varchar(256) DEFAULT NULL,
  `api_project_url` varchar(64) DEFAULT NULL,
  `oauth_type` varchar(16) DEFAULT NULL,
  `eid` varchar(32) DEFAULT NULL,
  `enable` tinyint(2) DEFAULT NULL,
  `is_deleted` tinyint(2) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=92 DEFAULT CHARSET=utf8;


CREATE TABLE `user_oauth_service` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `service_id` int(11) DEFAULT NULL,
  `is_auto_login` tinyint(2) DEFAULT NULL,
  `is_authenticated` tinyint(2) DEFAULT NULL,
  `is_expired` tinyint(2) DEFAULT NULL,
  `access_token` varchar(256) DEFAULT NULL,
  `oauth_user_id` int(16) DEFAULT NULL,
  `oauth_user_name` varchar(64) DEFAULT '',
  `oauth_user_email` varchar(64) DEFAULT '',
  `refresh_token` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8;