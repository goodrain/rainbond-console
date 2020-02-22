-- rainbond_center_app
alter table rainbond_center_app modify `dev_status` varchar(32) null default 'releass';

-- rainbond_center_app_tag
CREATE TABLE `rainbond_center_app_tag` (
  `ID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(32) DEFAULT NULL,
  `enterprise_id` varchar(36) DEFAULT NULL,
  `is_deleted` tinyint(4) DEFAULT '0',
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8;

-- rainbond_center_app_tag_relation
CREATE TABLE `rainbond_center_app_tag_relation` (
  `ID` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `group_key` varchar(32) DEFAULT NULL,
  `version` varchar(32) DEFAULT NULL,
  `tag_id` varchar(32) DEFAULT NULL,
  `enterprise_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8;
