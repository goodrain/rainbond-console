alter table rainbond_center_app modify `scope` varchar(50);
update console_sys_config set `value`="5.1.5" where `key`="RAINBOND_VERSION";
