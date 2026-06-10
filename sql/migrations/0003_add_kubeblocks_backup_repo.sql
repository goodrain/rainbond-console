-- KubeBlocks BackupRepo 团队级管理数据库迁移脚本
-- 版本: 0003
-- 描述: 创建团队级 KubeBlocks BackupRepo 元数据表

CREATE TABLE IF NOT EXISTS `kubeblocks_backup_repo` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `tenant_id` varchar(32) NOT NULL COMMENT '团队ID',
  `team_name` varchar(64) NOT NULL COMMENT '团队名称',
  `region_name` varchar(64) NOT NULL COMMENT '数据中心名称',
  `namespace` varchar(64) NOT NULL COMMENT '团队命名空间',
  `display_name` varchar(64) NOT NULL COMMENT '显示名称',
  `repo_name` varchar(128) NOT NULL COMMENT 'KubeBlocks BackupRepo 名称',
  `secret_name` varchar(128) NOT NULL COMMENT '凭据 Secret 名称',
  `secret_namespace` varchar(64) NOT NULL DEFAULT 'rbd-plugins' COMMENT '凭据 Secret 命名空间',
  `storage_provider` varchar(32) NOT NULL DEFAULT 's3' COMMENT 'StorageProvider 名称',
  `access_method` varchar(16) NOT NULL DEFAULT 'Tool' COMMENT '访问方式',
  `bucket` varchar(255) NOT NULL COMMENT 'S3 Bucket',
  `endpoint` varchar(255) NOT NULL COMMENT 'S3 Endpoint',
  `region` varchar(64) DEFAULT '' COMMENT 'S3 Region',
  `volume_capacity` varchar(32) NOT NULL DEFAULT '100Gi' COMMENT 'BackupRepo 容量',
  `pv_reclaim_policy` varchar(16) NOT NULL DEFAULT 'Retain' COMMENT 'PV 回收策略',
  `path_prefix` varchar(255) DEFAULT '' COMMENT '备份路径前缀',
  `status` varchar(32) DEFAULT '' COMMENT '状态',
  `is_deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否已删除',
  `creator` varchar(64) DEFAULT '' COMMENT '创建人',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `uniq_region_repo_name` (`region_name`, `repo_name`),
  UNIQUE KEY `uniq_team_display_name` (`tenant_id`, `region_name`, `display_name`, `is_deleted`),
  KEY `idx_tenant_region` (`tenant_id`, `region_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='KubeBlocks BackupRepo 团队级元数据表';
