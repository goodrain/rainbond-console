-- 应用版本功能数据库迁移脚本
-- 版本: 0002
-- 描述: 创建应用与隐藏模板绑定关系表

CREATE TABLE IF NOT EXISTS `app_version_template_relation` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `tenant_id` varchar(32) NOT NULL COMMENT '租户id',
  `group_id` int(11) NOT NULL COMMENT '应用组id',
  `app_model_id` varchar(32) NOT NULL COMMENT '隐藏模板id',
  `app_model_name` varchar(64) NOT NULL COMMENT '隐藏模板名称',
  `template_type` varchar(32) NOT NULL DEFAULT 'application_version' COMMENT '模板类型',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `uniq_group_id` (`group_id`),
  KEY `idx_tenant_id` (`tenant_id`),
  KEY `idx_app_model_id` (`app_model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='应用版本隐藏模板绑定关系表';
