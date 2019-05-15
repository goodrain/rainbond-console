-- **2019-04-28 增加 云市应用升级记录表、云市服务升级记录表
create table `app_upgrade_record`
(
    `ID`          int         not null auto_increment,
    `tenant_id`   varchar(33) not null,
    `group_id`    int         not null,
    `group_key`   varchar(32) not null,
    `group_name`  varchar(64) not null,
    `version`     varchar(20) not null,
    `old_version` varchar(20) not null,
    `status`      tinyint     not null,
    `create_time` timestamp   not null default current_timestamp,
    `update_time` timestamp   not null default current_timestamp on update current_timestamp(3),
    primary key (`ID`)
)
    ENGINE = InnoDB
    AUTO_INCREMENT = 38
    DEFAULT CHARSET = utf8;


create table `service_upgrade_record`
(
    `ID`                       int          not null auto_increment,
    `app_upgrade_record_id`    int          not null,
    `service_id`               varchar(32)  not null,
    `service_cname`            varchar(100) not null,
    `upgrade_type`             varchar(20)  not null,
    `event_id`                 varchar(32)  not null,
    `update`                   longtext     not null,
    `status`                   tinyint      not null,
    `create_time`              timestamp    not null default current_timestamp,
    `update_time`              timestamp    not null default current_timestamp on update current_timestamp(3),
    primary key (`ID`)
)
    ENGINE = InnoDB
    AUTO_INCREMENT = 38
    DEFAULT CHARSET = utf8;

DROP TABLE IF EXISTS `tenant_service_backup`;
CREATE TABLE `tenant_service_backup` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `region_name` varchar(32) NOT NULL,
  `tenant_id` varchar(32) NOT NULL,
  `service_id` varchar(32) NOT NULL,
  `backup_id` varchar(32) NOT NULL,
  `backup_data` longtext NOT NULL,
  `create_time` datetime(6) DEFAULT NULL,
  `update_time` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `backup_id` (`backup_id`)
) ENGINE=InnoDB AUTO_INCREMENT=250 DEFAULT CHARSET=utf8;

-- **2019-05-15 增加唯一索引
alter table gateway_custom_configuration
    modify rule_id varchar(32) unique not null;
