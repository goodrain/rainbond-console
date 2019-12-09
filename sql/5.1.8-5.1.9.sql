-- 更新版本
update console.console_sys_config set `value`="5.1.9" where `key`="RAINBOND_VERSION";
------------------------------## module console ##--------------------------------------

-- console_sys_config
alter table console_sys_config modify `desc` varchar(100);

-- rainbond_center_app
alter table rainbond_center_app modify `share_team` varchar(64);
alter table rainbond_center_app modify `pic` varchar(200);

-- rainbond_center_plugin
alter table rainbond_center_plugin modify `plugin_name` varchar(64);

-- service_share_record
alter table service_share_record modify `team_name` varchar(64);

-- service_share_record_event 
alter table service_share_record_event modify `team_name` varchar(64);
alter table service_share_record_event modify `service_alias` varchar(64);
alter table service_share_record_event modify `service_name` varchar(64);

-- plugin_share_record_event
alter table plugin_share_record_event modify `team_name` varchar(64);
alter table plugin_share_record_event modify `plugin_name` varchar(64);

-- team_gitlab_info
alter table team_gitlab_info modify `respo_url` varchar(200);

-- tenant_service_recycle_bin
alter table tenant_service_recycle_bin modify `image` varchar(200);
alter table tenant_service_recycle_bin modify `volume_mount_path` varchar(200);
alter table tenant_service_recycle_bin modify `git_url` varchar(200);
alter table tenant_service_recycle_bin modify `volume_type` varchar(30);

-- app_import_record
alter table app_import_record modify `team_name` varchar(64);
alter table app_import_record modify `region` varchar(64);
alter table app_import_record modify `user_name` varchar(64);

-- groupapp_backup
alter table groupapp_backup modify `user` varchar(64);
alter table groupapp_backup modify `region` varchar(64);
alter table groupapp_backup modify `note` varchar(255);

-- groupapp_migrate
alter table groupapp_migrate modify `user` varchar(64);
alter table groupapp_migrate modify `migrate_region` varchar(64);

-- groupapp_backup_import 
alter table groupapp_backup_import modify `team_name` varchar(64);
alter table groupapp_backup_import modify `region` varchar(64);

-- applicants
alter table applicants modify `user_name` varchar(64);
alter table applicants modify `team_name` varchar(64);
alter table applicants modify `team_alias` varchar(64);

-- tenant_service_backup
alter table tenant_service_backup modify `region_name` varchar(64);

-- region_info
alter table region_info modify `region_id` varchar(36);
alter table region_info modify `region_name` varchar(64);
alter table region_info modify `region_alias` varchar(64);
alter table region_info modify `desc` varchar(200);

-------------------------------## module www ##-------------------------------------
-- user_info
alter table user_info modify `nick_name` varchar(64);
alter table user_info modify `password` varchar(64);
alter table user_info modify `phone` varchar(15);

-- tenant_info
alter table tenant_info modify `tenant_name` varchar(64);

-- tenant_region
alter table tenant_region modify `region_name` varchar(64);
alter table tenant_region modify `region_tenant_name` varchar(64);

-- tenant_region_resource
alter table tenant_region_resource modify `region_name` varchar(64);

-- tenant_service
alter table tenant_service modify `service_region` varchar(64);
alter table tenant_service modify `image` varchar(200);
alter table tenant_service modify `setting` varchar(200);
alter table tenant_service modify `volume_mount_path` varchar(200);
alter table tenant_service modify `volume_type` varchar(30);


-- tenant_service_delete
alter table tenant_service_delete modify `service_region` varchar(64);
alter table tenant_service_delete modify `image` varchar(200);
alter table tenant_service modify `setting` varchar(200);
alter table tenant_service modify `cmd` varchar(2048);
alter table tenant_service modify `volume_mount_path` varchar(200);
alter table tenant_service modify `git_url` varchar(200);
alter table tenant_service modify `volume_type` varchar(30);

-- tenant_service_auth
alter table tenant_service_auth modify `user` varchar(64);
alter table tenant_service_auth modify `password` varchar(200);

-- service_domain
alter table service_domain modify `service_name` varchar(64);
alter table service_domain modify `service_alias` varchar(64);
alter table service_domain modify `region_id` varchar(36);


-- service_domain_certificate
alter table service_domain_certificate modify `alias` varchar(64);

-- tenant_services_port
alter table tenant_services_port modify `port_alias` varchar(64);

-- service_group
alter table service_group modify `region_name` varchar(64);

-- service_group_relation
alter table service_group_relation modify `region_name` varchar(64);

-- tenant_service_image_relation
alter table tenant_service_image_relation modify `image_url` varchar(200);

-- tenant_service_rule
alter table tenant_service_rule modify `service_region` varchar(64);

-- service_event
alter table service_event modify `user_name` varchar(64);
alter table service_event modify `region` varchar(64);

-- service_probe
alter table service_probe modify `mode` varchar(20);
alter table service_probe modify `path` varchar(200);
alter table service_probe modify `cmd` varchar(1024);

-- console_config
alter table console_config modify `key` varchar(100);

-- tenant_service_group
alter table tenant_service_group modify `region_name` varchar(64);

-- service_tcp_domain
alter table service_tcp_domain modify `service_name` varchar(64);
alter table service_tcp_domain modify `service_alias` varchar(64);
alter table service_tcp_domain modify `region_id` varchar(36);

CREATE TABLE `autoscaler_rules` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `rule_id` varchar(32) NOT NULL,
  `service_id` varchar(32) NOT NULL,
  `enable` tinyint(1) NOT NULL,
  `xpa_type` varchar(3) NOT NULL,
  `min_replicas` int(11) NOT NULL,
  `max_replicas` int(11) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `rule_id` (`rule_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;

CREATE TABLE `autoscaler_rule_metrics` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `rule_id` varchar(32) NOT NULL,
  `metric_type` varchar(16) NOT NULL,
  `metric_name` varchar(255) NOT NULL,
  `metric_target_type` varchar(13) NOT NULL,
  `metric_target_value` int(11) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `autoscaler_rule_metrics_rule_id_metric_type_metr_da6a4fbb_uniq` (`rule_id`,`metric_type`,`metric_name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8;
