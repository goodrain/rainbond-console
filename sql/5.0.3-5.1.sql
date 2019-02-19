-- 创建三方服务endpoints表 third_party_service_endpoints


CREATE TABLE `third_party_service_endpoints` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `service_id` varchar(32),
  `service_cname` varchar(128),
  `tenant_id` varchar(32),
  `endpoints_type` varchar(32),
  `endpoints_info` text DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8;