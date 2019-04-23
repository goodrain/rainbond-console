-- **2019-04-12在service_source表中增加group_key, version, service_share_uuid字段，用于记录云市信息
alter table service_source add column group_key varchar(32) null comment "group of service from market";
alter table service_source add column `version` varchar(32) null comment "version of service from market";
alter table service_source add column service_share_uuid varchar(65) null comment "unique identification of service from market";

-- **2019-04-10在service_webhooks表中增加trigger字段，用来进行webhook触发匹配
alter table service_webhooks
    add `trigger` varchar(256) not null default '';

-- **2019-04-11在compose_group表中增加hub_user,hub_pass字段,统一记录账号密码
alter table compose_group
    add `hub_user` varchar(256) not null default '';

alter table compose_group
    add `hub_pass` varchar(256) not null default '';
