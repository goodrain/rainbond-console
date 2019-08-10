alter table enterprise_user_perm add token varchar(32) unique default null;

alter table console.service_source modify user_name varchar(255);