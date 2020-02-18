-- tenant_service
alter table tenant_service modify column extend_method varchar(32) DEFAULT "stateless_singleton";