alter table console.tenant_service modify column git_url varchar(2047);
alter table region.tenant_service_version modify column repo_url varchar(2047);
