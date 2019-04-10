-- **2019-04-10在service_webhooks表中增加trigger字段，用来进行webhook触发匹配
alter table service_webhooks
    add `trigger` varchar(256) not null default '';
