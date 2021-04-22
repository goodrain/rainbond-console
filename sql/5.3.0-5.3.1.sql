CREATE TABLE IF NOT EXISTS `service_components` (
    `ID` int(11) NOT NULL AUTO_INCREMENT,
    `app_id` int NOT NULL,
    `service_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
    `component_id` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
    PRIMARY KEY (`ID`),
    KEY (`app_id`,`service_name`,`component_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `tenant_service_delete` ADD COLUMN `component_type` varchar(32) NULL AFTER `service_name`;
ALTER TABLE `tenant_service` ADD COLUMN `component_type` varchar(32) NULL AFTER `service_name`;