alter table user_oauth_service modify column access_token varchar(2047);
alter table `rainbond_center_app_tag` drop index `name`;
alter table `rainbond_center_app_tag` ADD unique(`name`,`enterprise_id`);
