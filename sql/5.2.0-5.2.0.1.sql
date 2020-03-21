alter table user_info add enterprise_center_user_id varchar(32) DEFAULT NULL;
alter table user_info add real_name varchar(64) DEFAULT NULL;

alter table region_info add region_type varchar(32) DEFAULT NULL;
alter table region_info add enterprise_id varchar(32) DEFAULT NULL;

