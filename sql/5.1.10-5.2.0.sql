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