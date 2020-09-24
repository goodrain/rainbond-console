
CREATE TABLE `tenant_service_monitor` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `service_id` varchar(32) NOT NULL,
  `path` varchar(32) NOT NULL,
  `port` int(11) NOT NULL,
  `service_show_name` varchar(64) NOT NULL,
  `interval` varchar(10) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `tenant_service_monitor_name_tenant_id_df0b897f_uniq` (`name`,`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

ALTER TABLE console.service_group ADD `create_time` datetime DEFAULT NULL;
ALTER TABLE console.service_group ADD `update_time` datetime DEFAULT NULL;