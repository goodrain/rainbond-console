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