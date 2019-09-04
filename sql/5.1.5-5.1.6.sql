alter table enterprise_user_perm add token varchar(32) unique default null;

alter table console.service_source modify user_name varchar(255);
alter table console.service_source modify `password` varchar(255);
update console.console_sys_config set `value`="5.1.6" where `key`="RAINBOND_VERSION";
