alter table console.tenant_service modify column git_url varchar(2047);
alter table region.tenant_service_version modify column repo_url varchar(2047);
update console.console_sys_config set `value`="5.1.7" where `key`="RAINBOND_VERSION";