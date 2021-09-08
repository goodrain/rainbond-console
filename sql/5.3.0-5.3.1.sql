-- only support mysql
ALTER TABLE `service_group` ADD COLUMN `app_store_name` varchar(255) NULL;
ALTER TABLE `service_group` ADD COLUMN `app_store_url` varchar(2047) NULL;
ALTER TABLE `service_group` ADD COLUMN `app_template_name` varchar(255) NULL;
ALTER TABLE `service_group` ADD COLUMN `version` varchar(255) NULL;
ALTER TABLE `service_group` ADD COLUMN `app_type` varchar(255) DEFAULT 'rainbond';
ALTER TABLE tenant_service_env_var MODIFY attr_value text;
ALTER TABLE tenant_service_monitor MODIFY `path` varchar(255);
ALTER TABLE tenant_info CHANGE `region` `region` varchar(64) Default '';
ALTER TABLE service_share_record ADD COLUMN `share_app_version_info` VARCHAR(255) DEFAULT '';

ALTER TABLE app_upgrade_record ADD COLUMN `upgrade_group_id` int DEFAULT 0;
ALTER TABLE `tenant_service_config` ADD COLUMN `volume_name` varchar(255) NULL AFTER `file_content`;
ALTER TABLE `app_upgrade_record` ADD COLUMN `snapshot_id` varchar(32) NULL AFTER `upgrade_group_id`;
ALTER TABLE `app_upgrade_record` ADD COLUMN `record_type` varchar(32) NULL;
ALTER TABLE `app_upgrade_record` ADD COLUMN `parent_id` int DEFAULT 0;

CREATE TABLE IF NOT EXISTS `app_upgrade_snapshots` (
     `ID` int NOT NULL AUTO_INCREMENT,
     `tenant_id` varchar(32) NOT NULL,
     `upgrade_group_id` int NOT NULL,
     `snapshot_id` varchar(32) NOT NULL,
     `snapshot` longtext NOT NULL,
     `update_time` datetime(6) NOT NULL,
     `create_time` datetime(6) NOT NULL,
     PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE rainbond_center_app_version modify COLUMN version_alias VARCHAR(64);
ALTER TABLE service_share_record modify COLUMN share_version_alias VARCHAR(64);

ALTER TABLE tenant_service add COLUMN container_gpu int(64) DEFAULT 0;
ALTER TABLE tenant_service_delete add COLUMN container_gpu int(64) DEFAULT 0;

--dedup tenant_service_group--
DELETE 
FROM
 tenant_service_group 
WHERE
 id NOT IN ( SELECT id FROM ( SELECT min( id ) AS id FROM tenant_service_group GROUP BY group_key, service_group_id ) AS b );
UPDATE tenant_service a
	JOIN service_group_relation b
	JOIN tenant_service_group c ON a.service_id = b.service_id 
	AND c.service_group_id = b.group_id 
	AND b.group_id 
	AND a.service_source = "market" 
	AND a.tenant_service_group_id <> c.ID
	SET a.tenant_service_group_id = c.ID;

-- update tenant_service_group version --
UPDATE `tenant_service_group` 
SET group_version = (
	SELECT
		max( ss.version ) AS version 
	FROM
		service_source ss,
		tenant_service ts 
	WHERE
		ss.service_id = ts.service_id 
		AND ts.tenant_service_group_id = tenant_service_group.ID 
	GROUP BY
		ts.tenant_service_group_id 
	) 
WHERE
	EXISTS (
	SELECT
		max( ss.version ) AS version 
	FROM
		service_source ss,
		tenant_service ts 
	WHERE
		ss.service_id = ts.service_id 
		AND ts.tenant_service_group_id = tenant_service_group.ID 
	GROUP BY
	ts.tenant_service_group_id 
	);

-- update service_share_uuid and service_key  --
UPDATE service_source SET service_share_uuid=CONCAT(SUBSTRING(service_share_uuid, 34),"+",SUBSTRING(service_share_uuid, 34));
UPDATE tenant_service a
JOIN service_source b ON a.service_id = b.service_id 
SET a.service_key = SUBSTRING( b.service_share_uuid, 34 )
WHERE
	a.service_source = "market";