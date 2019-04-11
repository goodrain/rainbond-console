-- **2019-04-10在service_webhooks表中增加trigger字段，用来进行webhook触发匹配
alter table service_webhooks
    add `trigger` varchar(256) not null default '';

-- **2019-04-11在compose_group表中增加hub_user,hub_pass字段,统一记录账号密码
alter table compose_group
    add `hub_user` varchar(256) not null default '';

alter table compose_group
    add `hub_pass` varchar(256) not null default '';
