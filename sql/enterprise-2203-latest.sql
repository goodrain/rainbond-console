ALTER TABLE user_info ADD COLUMN `password_expiration_time` datetime(6) NULL;
ALTER TABLE operation_log ADD new_information longtext;
ALTER TABLE operation_log ADD old_information longtext;
ALTER TABLE operation_log ADD information_type varchar(32) default 'no_details';
-- 2203升级到2208 --
alter TABLE service_domain ADD enable_mod_security tinyint(1) NOT NULL;
alter TABLE service_domain ADD white_ip longtext;
-- 2211升级到2302 --
CREATE TABLE `menus` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `eid` varchar(33) NOT NULL,
  `title` varchar(64) NOT NULL,
  `path` longtext NOT NULL,
  `parent_id` int(11) NOT NULL,
  `iframe` bool DEFAULT false NOT NULL,
  `sequence` int(11) NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
ALTER TABLE service_domain ADD black_ip longtext;
ALTER TABLE service_domain ADD black_or_white varchar(32) default 'close';
ALTER TABLE service_domain ADD waf_rules longtext;

-- 2302升级到2303 --
ALTER TABLE `tenant_service_volume` ADD COLUMN `nfs_path` varchar(400) NULL;
ALTER TABLE `tenant_service_volume` ADD COLUMN `nfs_server` varchar(400) NULL;

-- 2303升级到2306 --
CREATE TABLE service_security_context (
    ID int(11) NOT NULL AUTO_INCREMENT,
    service_id varchar(32) NULL,
    seccomp_profile varchar(1024) NULL,
    run_as_non_root BOOL NULL,
    allow_privilege_escalation BOOL NULL,
    run_as_user INTEGER NULL,
    run_as_group INTEGER NULL,
    capabilities LONGTEXT NULL,
    read_only_root_filesystem BOOL NULL,
    PRIMARY KEY (`ID`)
)
ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE console.app_gray_release (
    ID int(11) NOT NULL AUTO_INCREMENT,
	app_id varchar(32) NULL,
	entry_component_id varchar(32) NULL,
	flow_entry_rule LONGTEXT NULL,
	gray_strategy_type varchar(32) NULL,
	gray_strategy LONGTEXT NULL,
	entry_http_route varchar(128) NULL,
	status BOOL DEFAULT 0 NULL,
	trace_type varchar(32) NULL,
	PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE service_domain ADD is_limiting BOOL default FALSE;
ALTER TABLE service_domain ADD burst_traffic_number int(11) NOT NULL default 1;
ALTER TABLE service_domain ADD limiting_policy_name varchar(32) NULL;

CREATE TABLE limiting_policy (
    ID int(11) NOT NULL AUTO_INCREMENT,
	limiting_name varchar(32) NULL,
	access_memory_size INTEGER DEFAULT 20 NULL,
	max_access_rate INTEGER DEFAULT 20 NULL,
	tenant_id varchar(32) NULL,
	PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2303升级到2306 BS --
ALTER TABLE user_info ADD COLUMN oss_app_status bool DEFAULT false NOT NULL;
ALTER TABLE user_info ADD COLUMN oss_psid varchar(32) DEFAULT '';



------ 2306s升级到2309 -----------
CREATE TABLE service_inspection (
    ID int(11) NOT NULL AUTO_INCREMENT,
    service_id varchar(32) NULL,
    code_open BOOL DEFAULT 0 NULL,
    normative_open BOOL DEFAULT 0 NULL,
    PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE service_gateway_domain (
    ID int(11) NOT NULL AUTO_INCREMENT,
    service_id varchar(32) NULL,
    port INTEGER DEFAULT 5000 NULL,
    protocol varchar(32) DEFAULT "http" NULL,
    hosts LONGTEXT NULL,
    route_yaml LONGTEXT NULL,
    PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE component_report (
    ID int(11) NOT NULL AUTO_INCREMENT,
    component_id varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    create_time datetime DEFAULT NULL,
    primary_link varchar(1024) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    level int DEFAULT NULL,
    type varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    message varchar(4096) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
    PRIMARY KEY (`ID`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
