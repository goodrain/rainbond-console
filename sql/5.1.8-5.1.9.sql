-- 更新版本
update console.console_sys_config set `value`="5.1.9" where `key`="RAINBOND_VERSION";


-- 证书
alter table console.service_domain_certificate modify `alias` varchar(64);
