alter table service_source add column group_key varchar(32) null comment "group of service from market";
alter table service_source add column version varchar(32) null comment "version of service from market";
alter table service_source add column service_share_uuid varchar(65) null comment "unique identification of service from market";