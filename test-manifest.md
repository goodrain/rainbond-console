# 测试能力清单

> 此文件由 `scripts/manage_test_manifest.py render` 自动生成，请勿手工编辑。

| Capability ID | 中文标题 | 状态 | 测试类型 | 业务入口 | 测试文件 |
|---|---|---|---|---|---|
| console.app-backup.create | 创建应用备份 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_starts_group_backup |
| console.app-backup.custom-volume-guard | 组件使用自定义存储时阻止备份 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_rejects_custom_volume_usage |
| console.app-backup.delete | 删除应用备份 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.delete | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_delete_removes_group_backup |
| console.app-backup.delete-id-required | 删除应用备份前必须提供备份 ID | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.delete | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_delete_requires_backup_id |
| console.app-backup.delete-in-progress | 备份进行中时阻止删除该备份记录 | active | regression | console.services.backup_service.GroupAppBackupService.delete_group_backup_by_backup_id | console/tests/backup_service_test.py::GroupAppBackupServiceDeleteInProgressTests |
| console.app-backup.delete-status-lookup-failure | 删除备份时状态查询失败返回错误 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.delete | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_delete_returns_error_when_status_lookup_fails |
| console.app-backup.export | 导出应用备份 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_returns_attachment_response |
| console.app-backup.export-failure | 应用备份导出失败时返回错误 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_returns_error_when_service_fails |
| console.app-backup.export-group-missing | 导出备份时拦截不存在的应用组 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_rejects_missing_group |
| console.app-backup.export-group-required | 导出应用备份前必须提供组 ID | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_requires_group_id |
| console.app-backup.export-id-required | 导出备份前必须提供备份 ID | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_requires_backup_id |
| console.app-backup.export-team-missing | 导出备份时拦截不存在的团队 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_rejects_missing_team |
| console.app-backup.export-teamname-required | 导出应用备份前必须提供团队名 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_requires_team_name |
| console.app-backup.force-bypass-guards | 强制备份时跳过前置校验 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_force_bypasses_backup_guards |
| console.app-backup.group-required | 创建应用备份前必须提供组 ID | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_requires_group_id |
| console.app-backup.import | 导入应用备份 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_creates_restore_record |
| console.app-backup.import-failure | 应用备份导入失败时返回错误 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_returns_error_when_service_fails |
| console.app-backup.import-file-required | 导入备份前必须上传备份文件 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_requires_file |
| console.app-backup.import-file-size-guard | 拦截超大备份导入文件 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_rejects_file_larger_than_limit |
| console.app-backup.import-group-required | 导入应用备份前必须提供组 ID | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_requires_group_id |
| console.app-backup.list-all | 查询团队全部备份列表 | active | regression | console.views.center_pool.groupapp_backup.AllTeamGroupAppsBackupView.get | console/tests/groupapp_backup_listing_test.py::GroupAppsBackupListingTests.test_all_team_group_apps_backup_view_marks_deleted_groups |
| console.app-backup.list-by-app | 查询单个应用备份列表 | active | regression | console.views.center_pool.groupapp_backup.TeamGroupAppsBackupView.get | console/tests/groupapp_backup_listing_test.py::GroupAppsBackupListingTests.test_team_group_apps_backup_view_returns_backup_list |
| console.app-backup.list-by-app-group-required | 查询应用备份列表时必须提供组 ID | active | regression | console.views.center_pool.groupapp_backup.TeamGroupAppsBackupView.get | console/tests/groupapp_backup_listing_test.py::GroupAppsBackupListingTests.test_team_group_apps_backup_view_requires_group_id |
| console.app-backup.list-status | 查询应用备份状态列表 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewTests.test_get_returns_backup_status_list_without_internal_server_info |
| console.app-backup.list-status-empty | 备份状态列表不存在时返回成功空结果 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewTests.test_get_returns_success_when_status_not_found |
| console.app-backup.list-status-failure | 备份状态列表查询失败时返回错误 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewTests.test_get_returns_error_when_status_query_fails |
| console.app-backup.list-status-group-required | 查询备份状态列表时必须提供组 ID | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewTests.test_get_requires_group_id |
| console.app-backup.mode-required | 创建应用备份前必须选择模式 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_requires_backup_mode |
| console.app-backup.note-required | 创建应用备份前必须填写说明 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_requires_backup_note |
| console.app-backup.object-storage-unconfigured | 对象存储未配置时标记备份列表状态 | active | regression | console.views.center_pool.groupapp_backup.TeamGroupAppsBackupView.get | console/tests/groupapp_backup_listing_test.py::GroupAppsBackupListingTests.test_team_group_apps_backup_view_marks_object_storage_unconfigured |
| console.app-backup.query-status | 查询应用备份状态 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_get_returns_group_backup_status |
| console.app-backup.query-status-failure | 查询单个备份状态失败时返回错误 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_get_returns_error_when_status_query_fails |
| console.app-backup.query-status-guard | 查询备份状态时必须提供备份 ID | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_get_requires_backup_id |
| console.app-backup.region-app-scope | 按当前 region 应用范围限制备份组件 | active | regression | console.services.backup_service.GroupAppBackupService._get_effective_group_services | console/tests/backup_service_test.py::GroupAppBackupServiceScopeTests |
| console.app-backup.state-service-guard | 有状态组件未关闭时阻止备份 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_rejects_running_stateful_services |
| console.app-backup.status-sanitize | 隐藏备份状态中的内部服务端信息 | active | regression | console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewWorkflowTests.test_get_returns_backup_status_list_without_internal_server_info |
| console.app-backup.version-check | 备份版本与平台版本不一致时阻止恢复 | active | regression | console.services.backup_data_service.PlatformDataBackupServices.version_than | console/tests/backup_data_service_version_than_test.py::VersionThanTests |
| console.app-check.cmd-args-yaml | 将检测出的组件 cmd 和 args 持久化为 YAML 数组 | active | regression | console.services.app_check_service.AppCheckService.save_service_info | console/tests/app_check_k8s_attribute_test.py::AppCheckK8sAttributeTests |
| console.app-config-group.create | 创建应用配置组 | active | regression | console.services.app_config_group.AppConfigGroupService.create_config_group | console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_create_config_group_creates_remote_and_local_records |
| console.app-config-group.delete | 删除应用配置组 | active | regression | console.services.app_config_group.AppConfigGroupService.delete_config_group | console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_delete_config_group_deletes_remote_and_local_records |
| console.app-config-group.get | 查看应用配置组详情 | active | regression | console.services.app_config_group.AppConfigGroupService.get_config_group | console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_get_config_group_returns_built_response |
| console.app-config-group.list | 查询应用配置组列表 | active | regression | console.services.app_config_group.AppConfigGroupService.list_config_groups | console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_list_config_groups_returns_items_and_total |
| console.app-config-group.update | 更新应用配置组 | active | regression | console.services.app_config_group.AppConfigGroupService.update_config_group | console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_update_config_group_updates_remote_and_local_records |
| console.app-config.volume-service-module-export | 应用配置存储服务模块导出 | active | regression | console.services.app_config.volume_service.volume_service | console/tests/app_config_volume_service_import_test.py::AppConfigVolumeServiceImportTests.test_volume_service_module_exports_package_singleton |
| console.app-creator.full-permissions | App creator full permissions | active | regression | console.services.perm_services.UserKindPermService.get_user_perms | console/tests/perm_services_test.py |
| console.app-export.query-status | 查询应用导出状态 | active | regression | console.services.app_import_and_export_service.AppExportService.get_export_status | console/tests/app_import_and_export_service_test.py::AppExportServiceMetadataTestCase.test_get_export_status_updates_exporting_record_and_wraps_download_url |
| console.app-import.abandon | 放弃应用导入 | active | regression | console.views.center_pool.app_import.CenterAppImportView.delete | console/tests/app_import_and_export_service_test.py::CenterAppImportViewWorkflowTestCase.test_delete_abandons_import |
| console.app-import.create-dir | 创建导入目录 | active | regression | console.views.center_pool.app_import.CenterAppTarballDirView.post | console/tests/app_import_and_export_service_test.py::AppImportPreparationWorkflowTestCase.test_tarball_dir_post_creates_import_dir |
| console.app-import.delete-dir | 删除导入目录 | active | regression | console.views.center_pool.app_import.CenterAppTarballDirView.delete | console/tests/app_import_and_export_service_test.py::AppImportPreparationWorkflowTestCase.test_tarball_dir_delete_removes_import_dir |
| console.app-import.identity-collision | 处理导入应用模板身份冲突 | active | regression | console.services.app_import_and_export_service.AppImportService.__save_enterprise_import_info | console/tests/app_import_and_export_service_test.py::AppImportServiceMetadataTestCase.test_save_enterprise_import_info_splits_same_key_when_name_differs<br>console/tests/app_import_and_export_service_test.py::AppImportServiceMetadataTestCase.test_save_enterprise_import_info_keeps_same_key_and_name_as_multiple_versions<br>console/tests/app_import_and_export_service_test.py::AppImportServiceMetadataTestCase.test_save_enterprise_import_info_splits_same_key_name_version_when_content_differs |
| console.app-import.init | 初始化应用导入 | active | regression | console.views.center_pool.app_import.EnterpriseAppImportInitView.post | console/tests/app_import_and_export_service_test.py::AppImportPreparationWorkflowTestCase.test_enterprise_import_init_creates_record_when_none_exists |
| console.app-import.list-dir | 查询导入目录中的应用包 | active | regression | console.views.center_pool.app_import.CenterAppTarballDirView.get | console/tests/app_import_and_export_service_test.py::AppImportPreparationWorkflowTestCase.test_tarball_dir_get_lists_imported_packages |
| console.app-import.openapi-query-status | 查询 OpenAPI 应用导入状态 | active | regression | console.services.app_import_and_export_service.AppImportService.openapi_deploy_app_get_import_by_event_id | console/tests/app_import_and_export_service_test.py::AppImportStatusUpdateTestCase.test_openapi_deploy_app_get_import_by_event_id_skips_unchanged_status_save |
| console.app-import.query-status | 查询应用导入状态 | active | regression | console.views.center_pool.app_import.CenterAppImportView.get | console/tests/app_import_and_export_service_test.py::CenterAppImportViewWorkflowTestCase.test_get_returns_import_status<br>console/tests/app_import_and_export_service_test.py::CenterAppImportViewWorkflowTestCase.test_get_preserves_database_error_when_transaction_is_broken<br>console/tests/app_import_and_export_service_test.py::AppImportStatusUpdateTestCase.test_get_and_update_import_by_event_id_skips_unchanged_running_status_save<br>console/tests/app_import_and_export_service_test.py::AppImportStatusUpdateTestCase.test_get_and_update_import_by_event_id_saves_partial_success_once |
| console.app-import.start | 开始应用导入 | active | regression | console.views.center_pool.app_import.CenterAppImportView.post | console/tests/app_import_and_export_service_test.py::CenterAppImportViewWorkflowTestCase.test_post_starts_app_import |
| console.app-migrate.port-bind-failure-visible | 端口绑定失败时记录并返回，且不跳过后续端口 | active | regression | console.services.groupapp_recovery.groupapps_migrate.GroupappsMigrateService.__save_port | console/tests/groupapps_migrate_save_port_test.py::SavePortHttpFailureVisibleTest.test_first_port_failure_does_not_skip_second_and_is_reported |
| console.app-migration.cleanup-group-missing | 清理旧应用时拦截已删除的原组 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsView.delete | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_rejects_missing_original_group |
| console.app-migration.cleanup-group-required | 清理旧应用前必须提供原组 ID | active | regression | console.views.center_pool.groupapp_migration.GroupAppsView.delete | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_requires_group_id |
| console.app-migration.cleanup-new-group-required | 清理旧应用前必须提供恢复后的组 ID | active | regression | console.views.center_pool.groupapp_migration.GroupAppsView.delete | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_requires_new_group_id |
| console.app-migration.cleanup-old-app | 恢复后清理旧应用数据 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsView.delete | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_cleans_old_group_after_restore |
| console.app-migration.cleanup-same-group-noop | 恢复到当前组时跳过清理 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsView.delete | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_skips_cleanup_when_restored_to_same_group |
| console.app-migration.cleanup-target-group-missing | 清理旧应用时拦截不存在的新组 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsView.delete | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_rejects_missing_restored_group |
| console.app-migration.query-status | 查询应用迁移状态 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsMigrateView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_get_returns_migration_status |
| console.app-migration.record-missing | 迁移记录不存在时返回未找到 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsMigrateView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_get_returns_not_found_when_record_missing |
| console.app-migration.restore-id-required | 查询迁移状态时必须提供恢复 ID | active | regression | console.views.center_pool.groupapp_migration.GroupAppsMigrateView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_get_requires_restore_id |
| console.app-migration.start | 启动应用迁移 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_starts_group_migration |
| console.app-migration.target-region-guard | 拦截团队无权限的迁移目标集群 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_rejects_region_without_team_access |
| console.app-migration.target-team-missing | 拦截不存在的迁移目标团队 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_rejects_missing_target_team |
| console.app-migration.team-required | 启动应用迁移前必须指定目标团队 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_requires_target_team |
| console.app-migration.unfinished-record | 查询未完成的应用迁移记录 | active | regression | console.views.center_pool.groupapp_migration.MigrateRecordView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrateRecordViewTests.test_get_returns_unfinished_migration_record |
| console.app-migration.unfinished-record-empty | 无未完成迁移记录时返回已完成状态 | active | regression | console.views.center_pool.groupapp_migration.MigrateRecordView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrateRecordViewTests.test_get_returns_finished_when_no_unfinished_record |
| console.app-migration.unfinished-record-guard | 查询未完成迁移记录时必须提供 group_uuid | active | regression | console.views.center_pool.groupapp_migration.MigrateRecordView.get | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrateRecordViewTests.test_get_requires_group_uuid |
| console.app-migration.usable-region-guard | 目标团队无可用集群时阻止迁移 | active | regression | console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post | console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_rejects_when_target_team_has_no_usable_regions |
| console.app-publish.candidates | App Publish Candidates | active | regression | console.services.mcp_query_service.call_tool[console.app-publish.candidates] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_publish_candidates_returns_models |
| console.app-scale.vertical-gpu-default | 垂直伸缩未传 GPU 时保留组件当前值 | active | regression | console.services.app_actions.app_manage.AppManageService.vertical_upgrade | console/tests/vertical_upgrade_gpu_test.py::VerticalUpgradeGPUTests.test_omitted_gpu_keeps_current_value_instead_of_null<br>console/tests/vertical_upgrade_gpu_test.py::VerticalUpgradeGPUTests.test_omitted_gpu_defaults_to_zero_when_current_is_none<br>console/tests/vertical_upgrade_gpu_test.py::VerticalUpgradeGPUTests.test_explicit_gpu_is_applied_and_sent_to_region |
| console.app-share.complete | App Share Complete | active | regression | console.services.mcp_query_service.call_tool[console.app-share.complete] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_complete_app_share_calls_share_service_complete |
| console.app-share.create-record | App Share Create Record | active | regression | console.services.mcp_query_service.call_tool[console.app-share.create-record] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_share_record_supports_snapshot_mode |
| console.app-share.events | App Share Events | active | regression | console.services.mcp_query_service.call_tool[console.app-share.events] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_list_app_share_events_returns_service_and_plugin_events |
| console.app-share.get-event | App Share Get Event | active | regression | console.services.mcp_query_service.call_tool[console.app-share.get-event] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_share_event_returns_event_status |
| console.app-share.giveup | App Share Giveup | active | regression | console.services.mcp_query_service.call_tool[console.app-share.giveup] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_giveup_app_share_deletes_draft_record |
| console.app-share.info | App Share Info | active | regression | console.services.mcp_query_service.call_tool[console.app-share.info] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_share_info_returns_snapshot_payload |
| console.app-share.start-event | App Share Start Event | active | regression | console.services.mcp_query_service.call_tool[console.app-share.start-event] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_start_app_share_event_calls_sync_event |
| console.app-share.submit-info | App Share Submit Info | active | regression | console.services.mcp_query_service.call_tool[console.app-share.submit-info] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_submit_app_share_info_calls_share_service |
| console.app-status.aggregate-rainbond-components | 根据组件状态聚合 Rainbond 应用状态 | active | regression | console.services.group_service.GroupService.get_app_status | console/tests/group_service_test.py::GroupServiceAppStatusAggregationTests.test_get_app_status_uses_component_aggregation_for_rainbond_apps |
| console.app-status.closed-with-undeploy-components | 将关闭与未部署组件组合识别为应用已关闭 | active | regression | console.services.topological_services.TopologicalService.get_app_status | console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_closed_and_undeploy_components_make_app_closed |
| console.app-status.list-closed-with-undeploy-components | 当组件为关闭或未部署时将列表应用状态聚合为关闭 | active | regression | console.services.group_service.GroupService._add_component_status_to_apps | console/tests/group_service_test.py::GroupServiceAppStatusAggregationTests.test_add_component_status_to_apps_marks_closed_when_components_are_closed_or_undeploy |
| console.app-status.partial-abnormal-mixed-components | 将运行中与异常混合组件识别为部分异常 | active | regression | console.services.topological_services.TopologicalService.get_app_status | console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_mixed_abnormal_components_make_app_partially_abnormal |
| console.app-status.partial-abnormal-some-abnormal | 将 some_abnormal 组件识别为部分异常 | active | regression | console.services.topological_services.TopologicalService.get_app_status | console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_some_abnormal_component_makes_app_partially_abnormal |
| console.app-status.region-status-typeddict | 归一化集群应用状态返回（AppStatus TypedDict 落地） | active | regression | console.services.group_service.GroupService.get_app_status | console/tests/group_app_status_typeddict_test.py::GroupAppStatusTypedDictTest |
| console.app-status.vm-import-building-is-starting | VM import building components keep app starting | active | unit | console.services.topological_services.TopologicalService.get_app_status | console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_building_components_make_app_starting |
| console.app-status.vm-import-restoring-is-starting | VM import restoring components keep app starting | active | unit | console.services.topological_services.TopologicalService.get_app_status | console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_restoring_components_make_app_starting |
| console.app-status.waiting-is-starting | 将 waiting 组件识别为应用启动中 | active | regression | console.services.topological_services.TopologicalService.get_app_status | console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_waiting_components_make_app_starting |
| console.app-upgrade.changes | App Upgrade Changes | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.changes] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_upgrade_changes_returns_diff_payload |
| console.app-upgrade.create-record | App Upgrade Create Record | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.create-record] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_upgrade_record_calls_upgrade_service |
| console.app-upgrade.deploy-record | App Upgrade Deploy Record | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.deploy-record] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_deploy_app_upgrade_record_calls_deploy |
| console.app-upgrade.detail | App Upgrade Detail | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.detail] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_upgrade_detail_returns_record_and_versions |
| console.app-upgrade.execute-record | App Upgrade Execute Record | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.execute-record] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_execute_app_upgrade_record_calls_upgrade_service |
| console.app-upgrade.info | 查询应用升级信息 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_app_upgrade_info] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_upgrade_info_returns_upgrade_items |
| console.app-upgrade.last-record | App Upgrade Last Record | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.last-record] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_last_upgrade_record_returns_snapshot_metadata |
| console.app-upgrade.openapi-upgrade-group-id | OpenAPI 升级向记录创建传递 upgrade_group_id | active | regression | console.services.upgrade_services.UpgradeService.openapi_upgrade_app_models | console/tests/upgrade_services_test.py::OpenapiUpgradeGroupIdTests |
| console.app-upgrade.record | App Upgrade Record | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.record] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_upgrade_record_returns_record_detail |
| console.app-upgrade.record-status-summary | 应用升级记录状态汇总 | active | regression | console.services.upgrade_services.UpgradeService._update_app_record_status | console/tests/upgrade_services_test.py::UpgradeServiceRecordStatusTests |
| console.app-upgrade.records | App Upgrade Records | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.records] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_upgrade_records_returns_paginated_items |
| console.app-upgrade.rollback | App Upgrade Rollback | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.rollback] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_rollback_app_upgrade_record_calls_restore |
| console.app-upgrade.rollback-records | App Upgrade Rollback Records | active | regression | console.services.mcp_query_service.call_tool[console.app-upgrade.rollback-records] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_rollback_records_returns_items |
| console.app-version.component-diff-details | 生成应用版本组件差异明细 | active | regression | console.services.app_version_service._build_component_diff_details | console/tests/app_version_test.py::AppVersionServiceComponentDiffDetailTestCase.test_build_component_diff_details_tracks_added_removed_and_field_updates<br>console/tests/app_version_test.py::AppVersionServiceComponentDiffDetailTestCase.test_build_component_diff_details_tracks_connect_envs_and_other_changes |
| console.app-version.create-app-from-snapshot | App Version Create App From Snapshot | active | regression | console.services.mcp_query_service.call_tool[console.app-version.create-app-from-snapshot] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_from_snapshot_version_installs_hidden_template_into_new_app |
| console.app-version.create-app-from-snapshot-invalid-name | 从快照版本创建应用时拒绝非法目标应用名 | active | regression | console.services.mcp_query_service.call_tool[console.app-version.create-app-from-snapshot-invalid-name] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_from_snapshot_version_returns_structured_details_for_illegal_target_app_name |
| console.app-version.create-snapshot | 创建应用版本快照 | active | regression | console.views.app_version.AppVersionSnapshotListView.post | console/tests/app_version_test.py::AppVersionSnapshotListViewPostTestCase<br>console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_version_snapshot_calls_app_version_service |
| console.app-version.delete-rollback-record | 删除应用版本回滚记录 | active | regression | console.views.app_version.AppVersionRollbackRecordDetailView.delete | console/tests/app_version_test.py::AppVersionRollbackRecordViewTestCase.test_delete_removes_rollback_record |
| console.app-version.delete-snapshot | 删除应用版本快照 | active | regression | console.views.app_version.AppVersionSnapshotDetailView.delete | console/tests/app_version_test.py::AppVersionSnapshotDetailViewDeleteTestCase |
| console.app-version.delete-snapshot-endpoint | 通过接口删除应用版本快照 | active | regression | console.views.app_version.AppVersionSnapshotDetailView.delete | console/tests/app_version_test.py::AppVersionSnapshotDetailViewDeleteTestCase.test_delete_returns_success_response |
| console.app-version.diff-summary | 汇总应用版本差异 | active | regression | console.services.app_version_service._summarize_diff | console/tests/app_version_test.py::AppVersionServiceDiffSummaryTestCase.test_summarize_diff_keeps_real_component_changes |
| console.app-version.hidden-template-cleanup | 清理应用版本隐藏模板记录 | active | regression | console.services.market_app.market_app_service.delete_rainbond_app_all_info_by_id | console/tests/app_version_test.py::AppVersionTemplateDeleteTestCase.test_delete_rainbond_app_all_info_by_id_cleans_snapshot_relation |
| console.app-version.hidden-template-create | 创建应用版本隐藏模板 | active | regression | console.services.app_version_service.get_or_create_hidden_template | console/tests/app_version_test.py::AppVersionServiceHiddenTemplateTestCase |
| console.app-version.overview | 查看应用版本概览 | active | regression | console.services.app_version_service.get_overview | console/tests/app_version_test.py::AppVersionServiceOverviewTestCase.test_get_overview_promotes_latest_successful_rollback_target_to_current_version<br>console/tests/app_version_test.py::AppVersionServiceOverviewTestCase.test_get_overview_keeps_latest_snapshot_as_current_version_when_newer_than_rollback<br>console/tests/app_version_test.py::AppVersionServiceOverviewTestCase.test_get_overview_promotes_partial_rollback_target_to_current_version<br>console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_version_overview_returns_version_center_overview |
| console.app-version.restore-builds | 回滚后生成构建任务 | active | regression | console.services.market_app.market_app.MarketApp._generate_builds | console/tests/app_version_test.py::MarketAppBuildGenerationTestCase.test_generate_builds_allows_components_without_source_metadata |
| console.app-version.restore-component-without-source | 无来源信息时恢复组件 | active | regression | console.services.market_app.app_restore.AppRestore._create_component | console/tests/app_version_test.py::AppRestoreSnapshotCompatibilityTestCase.test_create_component_allows_snapshot_without_service_source |
| console.app-version.restore-k8s-attributes | 回滚时恢复组件 K8s 属性 | active | regression | console.services.market_app.new_app.NewApp._save_components | console/tests/app_version_test.py::NewAppSaveComponentsTestCase.test_save_components_overwrites_k8s_attributes_for_new_components |
| console.app-version.restore-legacy-action-type | 兼容旧快照中的操作类型 | active | regression | console.services.app_version_service.AppVersionRollbackRestore._create_component | console/tests/app_version_test.py::AppVersionRollbackRestoreActionTypeTestCase.test_create_component_keeps_snapshot_action_type_for_legacy_snapshot |
| console.app-version.restore-update-service-sources | 回滚时恢复组件来源信息 | active | regression | console.services.market_app.new_app.NewApp._update_components | console/tests/app_version_test.py::NewAppUpdateComponentsTestCase.test_update_components_overwrites_service_sources_when_snapshot_missing_source |
| console.app-version.rollback-create-new-app | 根据快照生成回滚目标应用 | active | regression | console.services.app_version_service.AppVersionRollbackRestore._create_new_app | console/tests/app_version_test.py::AppVersionRollbackRestoreSnapshotCoverageTestCase.test_create_new_app_restores_snapshot_components_missing_from_runtime<br>console/tests/app_version_test.py::AppVersionRollbackRestoreSnapshotCoverageTestCase.test_create_new_app_marks_changed_existing_components_for_update |
| console.app-version.rollback-plan | 生成回滚组件计划 | active | regression | console.services.app_version_service._build_rollback_component_plan | console/tests/app_version_test.py::AppVersionServiceRollbackPlanTestCase.test_build_rollback_component_plan_marks_changed_and_restored_components |
| console.app-version.rollback-record-detail | 查询应用版本回滚记录详情 | active | regression | console.views.app_version.AppVersionRollbackRecordDetailView.get | console/tests/app_version_test.py::AppVersionRollbackRecordViewTestCase.test_detail_returns_single_rollback_record |
| console.app-version.rollback-record-finished-delete | 删除已完成的回滚记录 | active | regression | console.services.app_version_service.delete_rollback_record | console/tests/app_version_test.py::AppVersionRollbackRecordServiceTestCase.test_delete_rollback_record_removes_finished_record |
| console.app-version.rollback-record-guard | 阻止删除进行中的回滚记录 | active | regression | console.services.app_version_service.delete_rollback_record | console/tests/app_version_test.py::AppVersionRollbackRecordServiceTestCase.test_delete_rollback_record_rejects_unfinished_record |
| console.app-version.rollback-record-list | 查询应用版本回滚记录列表 | active | regression | console.views.app_version.AppVersionRollbackRecordListView.get | console/tests/app_version_test.py::AppVersionRollbackRecordViewTestCase.test_list_returns_rollback_records |
| console.app-version.rollback-record-query | 查询应用版本回滚记录 | active | regression | console.services.app_version_service.list_rollback_records | console/tests/app_version_test.py::AppVersionRollbackRecordServiceTestCase.test_list_rollback_records_filters_app_version_records |
| console.app-version.rollback-record-sync | 查询前同步进行中的回滚记录 | active | regression | console.services.app_version_service.get_rollback_record | console/tests/app_version_test.py::AppVersionRollbackRecordServiceTestCase.test_get_rollback_record_detail_syncs_unfinished_record |
| console.app-version.rollback-record-update-ignore-missing | 回滚记录缺失时忽略状态更新 | active | regression | console.services.market_app.app_restore.AppRestore._update_rollback_record | console/tests/app_version_test.py::AppRestoreRollbackRecordTestCase.test_update_rollback_record_ignores_missing_record |
| console.app-version.rollback-restore-components | 应用版本回滚时恢复缺失组件 | active | regression | console.services.app_version_service.AppVersionRollbackRestore._create_new_app | console/tests/app_version_test.py::AppVersionRollbackRestoreSnapshotCoverageTestCase |
| console.app-version.rollback-snapshot | App Version Rollback Snapshot | active | regression | console.services.mcp_query_service.call_tool[console.app-version.rollback-snapshot] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_rollback_app_version_snapshot_returns_rollback_record |
| console.app-version.rollback-vm-snapshot-guard | 禁止回滚虚拟机应用版本快照 | active | regression | console.services.app_version_service.AppVersionService.rollback_snapshot | console/tests/app_version_test.py::AppVersionServiceRollbackVMSnapshotGuardTestCase |
| console.app-version.snapshot-delete-guard | 阻止删除最新应用版本快照 | active | regression | console.services.app_version_service.delete_snapshot | console/tests/app_version_test.py::AppVersionServiceDeleteSnapshotTestCase.test_delete_snapshot_rejects_latest_version |
| console.app-version.snapshot-delete-history | 删除历史应用版本快照 | active | regression | console.services.app_version_service.delete_snapshot | console/tests/app_version_test.py::AppVersionServiceDeleteSnapshotTestCase.test_delete_snapshot_removes_historical_version |
| console.app-version.snapshot-detail | 查看应用版本快照详情 | active | regression | console.services.app_version_service.get_snapshot_detail | console/tests/app_version_test.py::AppVersionServiceSnapshotDetailTestCase.test_get_snapshot_detail_includes_previous_version_and_field_diff |
| console.app-version.snapshot-no-change | 无变更时跳过创建快照 | active | regression | console.views.app_version.AppVersionSnapshotListView.post | console/tests/app_version_test.py::AppVersionSnapshotListViewPostTestCase.test_post_returns_no_change_message_when_snapshot_not_created |
| console.app-version.snapshot-share-image-fallback | App Version Snapshot Share Image Fallback | active | regression | console.services.app_version_service | console/tests/app_version_test.py::AppVersionServiceTemplateNormalizationTestCase.test_assemble_app_template_falls_back_to_image_when_share_image_missing |
| console.app-version.snapshots | App Version Snapshots | active | regression | console.services.mcp_query_service.call_tool[console.app-version.snapshots] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_list_app_version_snapshots_returns_versions |
| console.app-version.target-app-name-schema | create_app_from_snapshot_version 工具暴露目标应用名约束 | active | regression | console.services.mcp_query_service.list_tools[console.app-version.target-app-name-schema] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_create_app_from_snapshot_version_tool_exposes_target_app_name_constraints |
| console.app-version.view-diff | 查看应用版本差异详情 | active | regression | console.services.app_version_service._build_component_diff_details | console/tests/app_version_test.py::AppVersionServiceDiffSummaryTestCase<br>console/tests/app_version_test.py::AppVersionServiceComponentDiffDetailTestCase |
| console.app.batch-component-operation | 批量操作应用组件 | active | regression | console.services.mcp_query_service.call_tool[rainbond_operate_app] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_operate_app_calls_batch_operations |
| console.app.check-yaml | 校验 YAML 创建应用 | active | regression | console.services.mcp_query_service.call_tool[rainbond_check_yaml_app] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_check_yaml_app_returns_compose_check_info |
| console.app.close-all | 关闭团队下所有组件 | active | regression | console.services.mcp_query_service.call_tool[rainbond_close_apps] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_close_apps_calls_batch_action |
| console.app.copy | 复制应用组件到目标应用 | active | regression | console.services.mcp_query_service.call_tool[rainbond_copy_app] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_copy_app_returns_target_app_and_gateway_rules |
| console.app.copy-info | 获取应用复制信息 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_copy_app_info] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_copy_app_info_returns_services |
| console.app.copy-services-guard | 应用复制时拦截无效的 services 参数 | active | regression | console.services.mcp_query_service.copy_app | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_copy_app_rejects_non_list_services |
| console.app.create | 创建应用 | active | regression | console.services.mcp_query_service.call_tool[rainbond_create_app] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_calls_group_service |
| console.app.create-from-yaml | 从 YAML 创建应用 | active | regression | console.services.mcp_query_service.call_tool[rainbond_create_app_from_yaml] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_from_yaml_creates_compose_record |
| console.app.create-k8s-name-duplicate | App Create K8s Name Duplicate | active | regression | console.services.mcp_query_service.call_tool[console.app.create-k8s-name-duplicate] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_exposes_structured_k8s_app_duplicate_error |
| console.app.delete | 删除应用及隐藏快照模板 | active | regression | console.services.group_service._delete_app | console/tests/group_service_test.py::GroupServiceDeleteAppTestCase |
| console.app.delete-confirmation-guard | 阻止无效的应用删除确认 | active | regression | console.services.mcp_query_service.call_tool[rainbond_delete_app] | console/tests/mcp_query_service_test.py::MCPQueryServiceDeleteAppTests.test_delete_app_rejects_invalid_confirmation_token |
| console.app.delete-with-confirmation | 确认后删除应用 | active | regression | console.services.mcp_query_service.call_tool[rainbond_delete_app] | console/tests/mcp_query_service_test.py::MCPQueryServiceDeleteAppTests.test_delete_app_requires_confirmation_then_delete |
| console.app.detail | 查看应用详情 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_app_detail] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_detail_returns_status_and_counts |
| console.app.export-metadata | 生成应用导出元数据 | active | regression | console.services.app_import_and_export_service.AppExportService._AppExportService__get_app_metata | console/tests/app_import_and_export_service_test.py::AppExportServiceMetadataTestCase |
| console.app.get-yaml-check-result | 查看 YAML 应用校验结果 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_yaml_app_check_result] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_yaml_app_check_result_returns_services |
| console.app.install-from-market | 从市场安装应用 | active | regression | console.services.mcp_query_service.call_tool[rainbond_install_app_by_market] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_install_app_by_market_calls_market_service |
| console.app.list-team-apps | 查询团队应用列表 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_team_apps] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_team_apps_returns_app_list |
| console.app.monitor-range | 查询应用监控区间数据 | active | regression | console.services.mcp_query_service.call_tool[rainbond_query_app_monitor_range] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_monitor_range_returns_stringified_series |
| console.app.monitor-range-default-step | 监控区间查询默认步长为 60 秒 | active | regression | console.services.mcp_query_service.query_app_monitor_range | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_monitor_range_defaults_step_to_60 |
| console.app.monitor-summary | 查询应用监控概览 | active | regression | console.services.mcp_query_service.call_tool[rainbond_query_app_monitor] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_monitor_returns_monitor_items |
| console.app.monitor-summary-outer-only | 应用监控概览仅统计对外端口组件 | active | regression | console.services.mcp_query_service.query_app_monitor | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_monitor_filters_to_outer_services_when_requested |
| console.app.restart-component-operation | operate_app 重启映射到批量操作 | active | regression | console.services.mcp_query_service.call_tool[console.app.restart-component-operation] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_operate_app_restart_calls_batch_action |
| console.app.upgrade | 升级应用版本 | active | regression | console.services.mcp_query_service.call_tool[rainbond_upgrade_app] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_upgrade_app_calls_upgrade_service_and_returns_latest_items |
| console.auth.get-user-no-legacy-middleware | 解析会话用户时不访问已废弃的 MIDDLEWARE_CLASSES | active | regression | console.services.auth.get_user | console/tests/auth_get_user_test.py::GetUserNoLegacyMiddlewareTests.test_returns_user_without_touching_middleware_classes<br>console/tests/auth_get_user_test.py::GetUserNoLegacyMiddlewareTests.test_returns_anonymous_user_when_no_session |
| console.cache.capacity-guard | 内存缓存达到容量上限时拒绝或复用缓存槽位 | active | regression | console.utils.cache.Cache._memory_set | console/tests/utils/cache_test.py::CacheMemoryTests.test_memory_cache_refuses_new_key_when_full_without_expired_entries |
| console.cache.expired-eviction | 在访问时清理已过期的内存缓存项 | active | regression | console.utils.cache.Cache._memory_get | console/tests/utils/cache_test.py::CacheMemoryTests.test_memory_cache_evicts_expired_entry_on_get |
| console.cache.expired-eviction-count | 返回清理过期缓存时移除的条目数量 | active | regression | console.utils.cache.Cache._remove_expired_key | console/tests/utils/cache_test.py::CacheMemoryTests.test_remove_expired_key_returns_removed_count |
| console.cache.memory-store-and-expire | 在内存模式下于过期前返回缓存值 | active | regression | console.utils.cache.Cache.get | console/tests/utils/cache_test.py::CacheMemoryTests.test_memory_cache_returns_value_before_expiration |
| console.cache.redis-backend-read-write | 启用 redis 时将缓存读写委托给 redis 后端 | active | regression | console.utils.cache.Cache.get | console/tests/utils/cache_test.py::CacheMemoryTests.test_cache_delegates_get_and_set_to_redis_backend |
| console.cache.redis-client-config | 根据环境配置初始化 redis 缓存客户端 | active | regression | console.utils.cache.Cache.__init__ | console/tests/utils/cache_test.py::CacheMemoryTests.test_cache_initializes_redis_client_from_env |
| console.cache.redis-enabled-flag | 在存在 REDIS_HOST 时启用 redis 缓存模式 | active | regression | console.utils.cache.Cache.enable_redis | console/tests/utils/cache_test.py::CacheMemoryTests.test_enable_redis_follows_env |
| console.cache.redis-read-error | 吞掉 redis 读取异常并回落为空结果 | active | regression | console.utils.cache.Cache._redis_get | console/tests/utils/cache_test.py::CacheMemoryTests.test_redis_get_swallow_exception |
| console.cache.redis-write-error | 吞掉 redis 写入异常且不打断调用方 | active | regression | console.utils.cache.Cache._redis_set | console/tests/utils/cache_test.py::CacheMemoryTests.test_redis_set_swallow_exception |
| console.cache.update-existing-at-capacity | 即使内存缓存已满也允许更新已有缓存项 | active | regression | console.utils.cache.Cache._memory_set | console/tests/utils/cache_test.py::CacheMemoryTests.test_memory_cache_updates_existing_key_when_full |
| console.cert.expired-reject | 在证书有效性检查中拒绝已过期证书 | active | regression | console.utils.certutil.cert_is_effective | console/tests/utils/certutil_test.py::CertUtilTests.test_cert_is_effective_rejects_expired_cert |
| console.cert.invalid-private-key | 在证书校验中拒绝无效私钥 | active | regression | console.utils.certutil.cert_is_effective | console/tests/utils/certutil_test.py::CertUtilTests.test_cert_is_effective_rejects_invalid_private_key |
| console.cert.key-match | 校验证书与私钥是否匹配且有效 | active | regression | console.utils.certutil.cert_is_effective | console/tests/utils/certutil_test.py::CertUtilTests.test_cert_is_effective |
| console.cert.san-parse | 从扩展字符串中解析证书的 SAN 域名与 IP | active | regression | console.utils.certutil.parse_subject_alt_names | console/tests/utils/certutil_test.py::CertUtilTests.test_parse_subject_alt_names |
| console.cert.summary | 汇总证书 SAN、签发方与过期信息 | active | regression | console.utils.certutil.analyze_cert | console/tests/utils/certutil_test.py::CertUtilTests.test_analyze_cert |
| console.cert.utc-to-local | 将证书 UTC 时间戳转换为本地时间字符串 | active | regression | console.utils.certutil.utc2local | console/tests/utils/certutil_test.py::CertUtilTests.test_utc2local |
| console.cnb-build.auto-set-build-type | 根据构建参数自动设置 CNB 构建类型 | active | regression | console.utils.cnb_build.has_cnb_build_params | console/tests/cnb_build_test.py::BuildTypeAutoSetTestCase.test_auto_set_build_type_cnb_for_node_language |
| console.cnb-build.detect-build-params | 识别 CNB 构建参数 | active | regression | console.utils.cnb_build.has_cnb_build_params | console/tests/cnb_build_test.py::CNBParamsDetectionTestCase.test_node_language_detects_cnb_params<br>console/tests/cnb_build_test.py::CNBParamsDetectionTestCase.test_non_cnb_language_ignores_stale_cnb_params<br>console/tests/cnb_build_test.py::CNBParamsDetectionTestCase.test_empty_build_env_dict_has_no_cnb_params<br>console/tests/cnb_build_test.py::CNBParamsDetectionTestCase.test_each_supported_cnb_param_is_detected_for_node_language |
| console.cnb-build.detect-supported-language | 识别支持 CNB 的构建语言 | active | regression | console.utils.cnb_build.is_cnb_language | console/tests/cnb_build_test.py::CNBLanguageDetectionTestCase.test_nodejs_language_is_cnb<br>console/tests/cnb_build_test.py::CNBLanguageDetectionTestCase.test_static_language_is_cnb |
| console.cnb-build.framework-output-contract | 生成框架输出目录约定 | active | regression | console.utils.cnb_build.extract_cnb_envs_from_runtime_info | console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_extract_known_framework_output_dir_examples |
| console.cnb-build.generate-runtime-envs | 根据运行时识别结果生成 CNB 环境变量 | active | regression | console.utils.cnb_build.extract_cnb_envs_from_runtime_info | console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_extract_nodejs_cnb_envs_from_runtime_info<br>console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_extract_static_framework_contract |
| console.cnb-build.ignore-unsupported-runtime-info | 忽略不支持语言的 CNB 运行时信息 | active | regression | console.utils.cnb_build.extract_cnb_envs_from_runtime_info | console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_java_runtime_info_does_not_generate_cnb_envs<br>console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_static_runtime_info_without_framework_has_no_extra_cnb_envs |
| console.cnb-build.keep-non-cnb-build-type | 对不支持语言不自动设置 CNB 构建类型 | active | regression | console.utils.cnb_build.has_cnb_build_params | console/tests/cnb_build_test.py::BuildTypeAutoSetTestCase.test_do_not_auto_set_build_type_for_java_language |
| console.cnb-build.preserve-supported-envs | 保留支持语言的 CNB 环境变量 | active | regression | console.utils.cnb_build.sanitize_build_env_dict_for_language | console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_node_build_envs_preserve_cnb_markers<br>console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_static_build_envs_preserve_cnb_markers<br>console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_node_build_envs_preserve_common_mirror_fields<br>console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_node_build_envs_preserve_known_node_versions |
| console.cnb-build.reject-unsupported-language | 拒绝不支持 CNB 的构建语言 | active | regression | console.utils.cnb_build.is_cnb_language | console/tests/cnb_build_test.py::CNBLanguageDetectionTestCase.test_java_language_is_not_cnb<br>console/tests/cnb_build_test.py::CNBLanguageDetectionTestCase.test_dockerfile_node_language_is_not_cnb |
| console.cnb-build.sanitize-unsupported-envs | 清理非支持语言中的陈旧 CNB 环境变量 | active | regression | console.utils.cnb_build.sanitize_build_env_dict_for_language | console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_java_build_envs_strip_stale_cnb_markers<br>console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_java_build_envs_strip_runtime_aliases_used_by_builder<br>console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_non_cnb_languages_strip_stale_cnb_markers |
| console.component-type.daemonset | DaemonSet 组件类型支持 | active | regression | console.enum.component_enum.ComponentType | console/tests/app_manage_test.py::ComponentDaemonSetSupportTests.test_daemonset_component_type_is_supported<br>console/tests/app_manage_test.py::ComponentDaemonSetSupportTests.test_extend_method_name_supports_daemonset<br>console/tests/app_manage_test.py::ComponentDaemonSetSupportTests.test_change_service_type_blocks_daemonset_transition |
| console.component.autoscaler-invalid-metrics | manage_component_autoscaler 在调用服务前拒绝不完整指标 | active | regression | console.services.mcp_query_service.call_tool[console.component.autoscaler-invalid-metrics] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_autoscaler_create_rejects_incomplete_metric_before_service_call |
| console.component.autoscaler-summary | 查看组件伸缩概览 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_autoscaler] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_autoscaler_summary_returns_rules_and_records |
| console.component.build | 检测成功后构建组件 | active | regression | console.services.mcp_query_service.call_tool[rainbond_build_component] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_build_component_builds_checked_component |
| console.component.build-component-schema | Component Build Component Schema | active | regression | console.services.mcp_query_service.call_tool[console.component.build-component-schema] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_build_component_tool_schema_exposes_build_info_guidance |
| console.component.build-env-preserve-source-build-state | Component Build Env Preserve Source Build State | active | regression | console.services.mcp_query_service.call_tool[console.component.build-env-preserve-source-build-state] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_replace_build_envs_preserves_source_build_state |
| console.component.build-logs | Component Build Logs | active | regression | console.services.mcp_query_service.call_tool[console.component.build-logs] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_build_logs_returns_event_log_items |
| console.component.build-source-get | Component Build Source Get | active | regression | console.services.mcp_query_service.call_tool[console.component.build-source-get] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_build_source_returns_sanitized_summary |
| console.component.build-source-update | Component Build Source Update | active | regression | console.services.mcp_query_service.call_tool[console.component.build-source-update] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_build_source_updates_source_code_fields |
| console.component.build-source-update-image-cmd | 构建源更新保留/设置镜像启动命令 | active | regression | console.services.mcp_query_service.call_tool[console.component.build-source-update-image-cmd] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_build_source_keeps_cmd_when_omitted_on_image_update<br>console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_build_source_sets_cmd_and_syncs_docker_cmd |
| console.component.change-image | 修改组件镜像 | active | regression | console.services.mcp_query_service.call_tool[rainbond_change_component_image] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_change_component_image_updates_service_fields |
| console.component.check-result | 获取组件构建检测结果 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_component_check_result] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_check_result_saves_detection_result |
| console.component.check-start | 启动组件检测 | active | regression | console.services.mcp_query_service.call_tool[rainbond_check_component] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_check_component_starts_check_flow |
| console.component.connection-env-create | 创建组件连接环境变量 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_connection_envs#create] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_connection_envs_create_uses_outer_scope |
| console.component.connection-env-summary | 查看组件连接环境变量 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_connection_envs#summary] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_connection_envs_summary_returns_outer_envs |
| console.component.create-from-image | 从镜像创建组件 | active | regression | console.services.mcp_query_service.call_tool[rainbond_create_component] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_calls_console_services |
| console.component.create-from-image-direct | 通过镜像入口创建组件 | active | regression | console.services.mcp_query_service.create_component_from_image | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_image_uses_existing_image_flow |
| console.component.create-from-package | 从制品包创建组件 | active | regression | console.services.package_component_service.auto_create_component | console/tests/package_component_service_test.py::PackageComponentServiceTests |
| console.component.create-from-package-upload | 通过上传制品包创建组件 | active | regression | console.services.mcp_query_service.create_component_from_package | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_package_calls_aggregated_package_service |
| console.component.create-from-source | 从源码创建组件 | active | regression | console.services.source_component_service.auto_create_component | console/tests/source_component_service_test.py::SourceComponentServiceTests |
| console.component.create-from-source-generic-git | 通过通用 Git 源码创建组件 | active | regression | console.services.mcp_query_service.create_component_from_source | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_source_allows_generic_git_code_from |
| console.component.create-from-source-guided | 通过引导式源码配置创建组件 | active | regression | console.services.mcp_query_service.create_component_from_source | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_source_calls_aggregated_source_service |
| console.component.create-from-source-prefer-dockerfile | Component Create From Source Prefer Dockerfile | active | regression | console.services.mcp_query_service.call_tool[console.component.create-from-source-prefer-dockerfile] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_source_passes_prefer_dockerfile_flag |
| console.component.default-resource-spec | 组件创建工具暴露默认资源规格指引 | active | regression | console.services.mcp_query_service.list_tools[console.component.default-resource-spec] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_component_creation_tools_expose_default_resource_guidance |
| console.component.delete | 删除组件 | active | regression | console.services.mcp_query_service.call_tool[rainbond_delete_component] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_delete_component_calls_app_manage_delete |
| console.component.delete-dependency-conflict | 删除组件返回结构化依赖冲突原因 | active | regression | console.services.mcp_query_service.call_tool[rainbond_delete_component#conflict] | console/tests/mcp_query_error_contract_test.py::MCPComponentContextErrorTests.test_delete_component_dependency_conflict_returns_structured_reason<br>console/tests/mcp_query_error_contract_test.py::MCPComponentContextErrorTests.test_delete_component_running_conflict_is_non_retryable |
| console.component.dependency-add | 添加组件依赖 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency#add] | console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_add_single_dependency_success<br>console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_add_single_dependency_requires_open_inner |
| console.component.dependency-add-batch | 批量添加组件依赖 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency#add-batch] | console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_add_batch_dependencies_success |
| console.component.dependency-add-reverse | 添加反向组件依赖 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency#add_reverse] | console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_add_reverse_dependencies_success |
| console.component.dependency-delete | 删除组件依赖 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency#delete] | console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_delete_dependency_success |
| console.component.dependency-summary | 查看组件依赖概览 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_dependency_summary_returns_dependency_snapshot |
| console.component.detail | 查询组件详情 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_component_detail] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_detail_returns_status_and_access_infos |
| console.component.env-batch-guard | 批量保存组件环境变量时拦截无效参数 | active | regression | console.services.mcp_query_service.update_component_envs | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_envs_rejects_invalid_payload |
| console.component.env-batch-save | 批量保存组件环境变量 | active | regression | console.services.mcp_query_service.update_component_envs | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_envs_calls_env_service |
| console.component.env-create | 创建组件环境变量 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_envs#create] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_create_defaults_scope_to_inner |
| console.component.env-scope-default | 将环境变量作用域默认归一为内网 | active | regression | console.services.mcp_query_service._normalize_env_scope | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_normalize_env_scope_defaults_to_inner |
| console.component.env-summary | 查看组件环境变量概览 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_envs] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_summary_returns_env_snapshots |
| console.component.env-update | 批量更新组件环境变量 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_envs#upsert] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_upsert_only_uses_inner_envs |
| console.component.env-upsert-single-item | Component Env Upsert Single Item | active | regression | console.services.mcp_query_service.call_tool[console.component.env-upsert-single-item] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_upsert_accepts_single_item_shape |
| console.component.events | 查询组件事件 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_component_events] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_events_returns_paginated_events |
| console.component.extend-method-upsert | 按组件版本覆盖保存伸缩规则配置 | active | regression | console.repositories.app_config.ServiceExtendRepository | console/tests/app_config_test.py::ServiceExtendRepositoryTests.test_create_extend_method_replaces_existing_version_record<br>console/tests/app_config_test.py::ServiceExtendRepositoryTests.test_get_extend_method_by_service_uses_latest_record<br>console/tests/app_config_test.py::ServiceExtendRepositoryTests.test_bulk_create_or_update_replaces_existing_version_records_by_business_key |
| console.component.horizontal-scale | 水平伸缩组件 | active | regression | console.services.mcp_query_service.call_tool[rainbond_horizontal_scale_component] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_horizontal_scale_component_calls_app_manage_service |
| console.component.list | 查看应用组件列表 | active | regression | console.services.mcp_query_service.call_tool[rainbond_query_components] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_components_uses_existing_service_repo_method |
| console.component.logs | 查看组件日志 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_component_logs] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_returns_component_logs |
| console.component.logs-console-shape | 兼容控制台风格实例结构读取日志 | active | regression | console.services.mcp_query_service.get_component_logs console pod shape fallback | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_service_supports_console_style_pod_shape |
| console.component.logs-container | 按指定容器读取组件日志 | active | regression | console.services.mcp_query_service.get_component_logs[action=container] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_returns_container_logs |
| console.component.logs-fallback | 读取组件日志时自动回退到实例容器 | active | regression | console.services.mcp_query_service.get_component_logs fallback selection | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_service_falls_back_to_first_pod_container |
| console.component.logs-no-instance | 无运行实例时拒绝查询组件日志 | active | regression | console.services.mcp_query_service.get_component_logs | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_rejects_when_no_runtime_instance_found |
| console.component.logs-parse-sse | 解析组件日志 SSE 数据 | active | regression | console.services.mcp_query_service._parse_component_log_line | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_parse_component_log_line_handles_sse_prefix |
| console.component.operation-aliases | 规范化组件操作别名 | active | regression | console.services.mcp_query_service._normalize_component_operation | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_normalize_component_operation_aliases |
| console.component.pods | Component Pods | active | regression | console.services.mcp_query_service.call_tool[console.component.pods] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_pods_returns_normalized_runtime_instances |
| console.component.port-add-invalid-alias | Component Port Add Invalid Alias | active | regression | console.services.mcp_query_service.call_tool[console.component.port-add-invalid-alias] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_handle_component_ports_add_exposes_structured_alias_validation |
| console.component.port-batch-add | manage_component_ports 批量新增委托给批量服务 | active | regression | console.services.mcp_query_service.call_tool[console.component.port-batch-add] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_batch_add_delegates_to_batch_service |
| console.component.port-batch-enable-inner | manage_component_ports 批量开启内网端口只加载一次上下文 | active | regression | console.services.mcp_query_service.call_tool[console.component.port-batch-enable-inner] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_batch_enable_inner_loads_context_once |
| console.component.port-batch-enable-outer | manage_component_ports 批量开启外网端口接受整数项 | active | regression | console.services.mcp_query_service.call_tool[console.component.port-batch-enable-outer] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_batch_enable_outer_accepts_integer_items |
| console.component.port-batch-protocol | manage_component_ports 批量修改协议时归一化每一项 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#update_protocol] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_batch_update_protocol_passes_each_normalized_protocol |
| console.component.port-list | 查询组件端口列表 | active | regression | console.services.mcp_query_service.call_tool[rainbond_handle_component_ports#list] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_handle_component_ports_list_returns_ports |
| console.component.port-open-inner | 开放组件内网端口 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#enable_inner] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_enable_inner_maps_to_open_inner |
| console.component.port-open-outer-only | 仅开放组件公网端口 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#enable_outer_only] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_enable_outer_only_maps_to_only_open_outer |
| console.component.port-open-public | 打开组件公网端口 | active | regression | console.services.mcp_query_service.call_tool[rainbond_handle_component_ports] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_handle_component_ports_alias_action_maps_to_standard_action |
| console.component.port-protocol-normalize | 归一化组件端口协议参数 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#update_protocol] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_update_protocol_normalizes_protocol |
| console.component.port-protocol-validation | 调用服务前拦截非法组件端口协议 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#update_protocol] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_update_protocol_rejects_invalid_protocol_before_service_call |
| console.component.port-summary | 查看组件端口概览 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_ports] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_summary_delegates_to_port_handler |
| console.component.port-toggle-events | 记录组件端口开关事件 | active | regression | console.services.app_config.port_service.AppPortService.manage_port | console/tests/port_service_delete_test.py::PortServiceDeleteTests::test_open_outer_port_synchronizes_region_component_event<br>console/tests/port_service_delete_test.py::PortServiceDeleteTests::test_close_outer_port_synchronizes_region_component_event<br>console/tests/port_service_delete_test.py::PortServiceDeleteTests::test_inner_port_toggle_keeps_region_component_event_path |
| console.component.probe-summary | 查看组件探针概览 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_probe] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_probe_summary_returns_probe_snapshot |
| console.component.storage-create-mount | 创建组件共享存储挂载 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#create_mnt] | console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_create_mnt_batches_mounts |
| console.component.storage-create-volume | 创建组件存储卷 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#create_volume] | console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_create_volume_returns_created_and_volume<br>console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_create_volume_rejects_collision_with_existing_config_file_path |
| console.component.storage-custom-volume-filter | 过滤组件自定义卷列表中的内置卷类型 | active | regression | console.repositories.app_config.TenantServiceVolumnRepository.list_custom_volumes | console/tests/app_config_test.py::TenantServiceVolumnRepositoryTests.test_list_custom_volumes_treats_local_path_as_builtin_volume_type |
| console.component.storage-delete-mount | 删除组件共享存储挂载 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#delete_mnt] | console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_delete_mnt_removes_relation |
| console.component.storage-delete-volume | 删除组件存储卷 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#delete_volume] | console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_delete_volume_requires_force_branch<br>console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_delete_volume_success_branch |
| console.component.storage-summary | 查看组件存储概览 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_storage] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_storage_summary_returns_storage_snapshot<br>console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_summary_includes_config_file_volumes |
| console.component.storage-target-scope | 拒绝操作其他组件的存储卷 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#update_volume] | console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_update_volume_rejects_volume_id_from_another_component |
| console.component.storage-update-capacity | Component Storage Update Capacity | active | regression | console.views.app_config.app_volume.AppVolumeManageView.put | console/tests/app_volume_view_test.py::AppVolumeManageViewTestCase.test_put_allows_updating_volume_capacity_without_path_change |
| console.component.storage-update-volume | 按当前路径更新组件存储卷 | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#update_volume] | console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_update_volume_can_resolve_target_by_current_volume_path |
| console.component.storage-update-volume-capacity | Component Storage Update Volume Capacity | active | regression | console.services.mcp_query_service.call_tool[rainbond_manage_component_storage] | console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_update_volume_allows_capacity_change_without_path_change |
| console.component.summary | 查看组件概览 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_component_summary] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_summary_returns_aggregated_info |
| console.component.volume-delete-blocks-shared-mount | 被共享挂载时阻止删除组件存储卷 | active | regression | console.services.app_config.volume_service.AppVolumeService.delete_service_volume_by_id | console/tests/app_config_volume_delete_test.py::AppVolumeDeleteTests.test_delete_service_volume_rejects_shared_mount_even_when_forced |
| console.dependency.invalid-container-port | Dependency Invalid Container Port | active | regression | console.services.app_config.app_relation_service.AppServiceRelationService | console/tests/app_relation_service_test.py::AppRelationServiceTests.test_add_service_dependency_rejects_unknown_dep_service_port |
| console.deploy-diagnostics.source-check | 源码构建源检测失败诊断埋点 | active | regression | console.views.app_create.app_check.AppCheck.get | console/tests/app_check_view_test.py::AppCheckSourceDiagnosticTests.test_get_reports_source_check_failure_without_changing_response<br>console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_raises_on_check_failure<br>console/tests/enterprise_first_deploy_service_test.py::EnterpriseFirstDeployServiceTests.test_report_source_check_failure_sends_pre_deploy_diagnostic |
| console.deploy-diagnostics.v3 | 部署失败 v3 诊断埋点 | active | regression | console.services.enterprise_first_deploy_service.EnterpriseFirstDeployService | console/tests/enterprise_first_deploy_service_test.py<br>console/tests/app_build_first_deploy_test.py::AppBuildFirstDeployTrackingTests.test_app_build_tracks_source_image_and_package_deploy_types<br>console/tests/market_app_first_deploy_test.py::MarketAppFirstDeployTrackingTests.test_install_app_reports_first_deploy_tracking_for_market_install<br>console/tests/compose_check_first_deploy_test.py<br>console/tests/compose_build_first_deploy_test.py::ComposeBuildFirstDeployTrackingTests.test_compose_build_tracks_first_deploy_and_binds_all_component_events<br>console/tests/auto_create_first_deploy_tracking_test.py<br>console/tests/platform_plugin_first_deploy_test.py::PlatformPluginFirstDeployTrackingTests.test_install_platform_plugin_reports_first_deploy_tracking |
| console.endpoint-address.reject-invalid-format | 拒绝既不是 IP 也不是域名的非法端点地址 | active | regression | console.utils.validation.validate_endpoint_address | console/tests/utils/validation_test.py::EndpointValidationTests.test_validate_endpoint_address_rejects_invalid_format |
| console.endpoint-address.reject-special-ranges | 拒绝 unspecified 和 loopback 的端点地址 | active | regression | console.utils.validation.validate_endpoint_address | console/tests/utils/validation_test.py::EndpointValidationTests.test_validate_endpoint_address_rejects_special_ranges |
| console.endpoint-list.normalize-scheme-port | 在多端点校验前规范化协议和端口 | active | regression | console.utils.validation.validate_endpoints_info | console/tests/utils/validation_test.py::EndpointValidationTests.test_validate_endpoints_info_normalizes_scheme_and_port |
| console.endpoint-list.reject-duplicate | 在多实例端点列表中拒绝重复地址 | active | regression | console.utils.validation.validate_endpoints_info | console/tests/utils/validation_test.py::EndpointValidationTests.test_validate_endpoints_info_rejects_duplicate_addresses |
| console.enterprise-config.concurrent-initialization | 处理企业配置并发初始化 | active | regression | console.services.config_service.ConfigService.add_config | console/tests/config_service_test.py::EnterpriseConfigServiceTests.test_add_config_returns_existing_record_when_concurrent_create_wins |
| console.enterprise-config.custom-fields-disabled-bool | get_custom_fields 包含被禁用的布尔字段 | active | regression | console.services.config_service.EnterpriseConfigService.get_custom_fields | console/tests/config_service_test.py::EnterpriseConfigServiceTests.test_get_custom_fields_includes_disabled_bool_fields |
| console.enterprise-config.user-context | 解析企业配置服务用户上下文 | active | regression | console.services.config_service.EnterpriseConfigService.__init__ | console/tests/config_service_test.py::EnterpriseConfigServiceTests.test_enterprise_config_service_defaults_user_id_to_none<br>console/tests/config_service_test.py::EnterpriseConfigServiceTests.test_enterprise_config_service_keeps_explicit_user_id |
| console.enterprise.bind-market-token-decode | 解码云市绑定企业的认证信息 | active | regression | console.views.enterprise_active.BindMarketEnterpriseOptimizAccessTokenView.post | console/tests/bind_market_token_decode_test.py::BindMarketTokenDecodeTest.test_market_info_is_base64_decoded |
| console.enterprise.region-component-list | 查看集群控制面组件列表 | active | regression | console.services.mcp_query_service.call_tool[rainbond_query_region_rbd_components] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_region_rbd_components_returns_components_for_enterprise_admin |
| console.enterprise.region-create | 创建企业集群 | active | regression | console.services.mcp_query_service.call_tool[rainbond_create_region] | console/tests/mcp_query_service_test.py::MCPQueryServiceRegionMutationTests.test_create_region_executes_directly |
| console.enterprise.region-dashboard-not-found | 集群仪表盘目标缺失时返回 404 | active | regression | console.views.enterprise.EnterpriseRegionDashboard.dispatch | console/tests/enterprise_region_dashboard_notfound_test.py::EnterpriseRegionDashboardNotFoundTest.test_missing_region_returns_clean_404 |
| console.enterprise.region-delete | 删除企业集群 | active | regression | console.services.mcp_query_service.call_tool[rainbond_delete_region] | console/tests/mcp_query_service_test.py::MCPQueryServiceRegionMutationTests.test_delete_region_executes_directly |
| console.enterprise.region-detail | 查看企业集群详情 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_region_detail] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_returns_region_data |
| console.enterprise.region-detail-by-name | 按集群名称查看企业集群详情 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_region_detail] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_accepts_region_name |
| console.enterprise.region-detail-no-cross-fallback | 不同集群 ID 无效时不跨字段回退 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_region_detail] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_does_not_override_distinct_bad_region_id |
| console.enterprise.region-detail-region-name-fallback | 集群详情支持从集群 ID 回退到名称查询 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_region_detail] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_treats_missing_region_id_as_region_name |
| console.enterprise.region-detail-schema | 集群详情工具 schema 暴露集群名称参数 | active | regression | console.services.mcp_query_service._tool_get_region_detail | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_schema_accepts_region_name |
| console.enterprise.region-list | 查看企业集群列表 | active | regression | console.services.mcp_query_service.call_tool[rainbond_query_regions] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_requires_enterprise_admin<br>console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_returns_paginated_regions_for_enterprise_admin<br>console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_rejects_cross_enterprise_access_for_enterprise_admin |
| console.enterprise.region-list-authz | 校验企业集群列表访问权限 | active | regression | console.services.mcp_query_service.query_regions | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_requires_enterprise_admin<br>console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_rejects_cross_enterprise_access_for_enterprise_admin |
| console.enterprise.region-node-detail | 查看集群节点详情 | active | regression | console.services.mcp_query_service.call_tool[rainbond_get_region_node_detail] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_node_detail_returns_node_detail_for_enterprise_admin |
| console.enterprise.region-node-list | 查看集群节点列表 | active | regression | console.services.mcp_query_service.call_tool[rainbond_query_region_nodes] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_region_nodes_returns_nodes_for_enterprise_admin |
| console.enterprise.region-update | 更新企业集群 | active | regression | console.services.mcp_query_service.call_tool[rainbond_update_region] | console/tests/mcp_query_service_test.py::MCPQueryServiceRegionMutationTests.test_update_region_executes_directly_with_merged_full_payload |
| console.file-manage.region-request-timeout | 文件管理区域请求使用选定容器与更长超时 | active | regression | www.apiclient.regionapi.RegionInvokeApi.get_files | console/tests/file_manage_service_test.py::test_region_api_get_files_uses_container_name_and_longer_timeout |
| console.file-manage.selected-container-forwarding | 列出文件管理内容时透传用户选择的容器名 | active | regression | console.services.group_service.GroupService.get_file_and_dir | console/tests/file_manage_service_test.py::test_get_file_and_dir_forwards_selected_container_name |
| console.gateway.component-env-upsert-schema | Gateway Component Env Upsert Schema | active | regression | console.services.mcp_query_service.call_tool[console.gateway.component-env-upsert-schema] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_envs_schema_exposes_single_item_upsert_guidance |
| console.gateway.create-app-invalid-display-name | create_app 对非法应用名返回结构化错误详情 | active | regression | console.services.mcp_query_service.call_tool[console.gateway.create-app-invalid-display-name] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_returns_structured_details_for_illegal_app_name |
| console.gateway.create-app-k8s-name-schema | Gateway Create App K8s Name Schema | active | regression | console.services.mcp_query_service.call_tool[console.gateway.create-app-k8s-name-schema] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_create_app_tool_schema_exposes_k8s_app_constraints |
| console.gateway.create-http-rule | 创建 HTTP 网关规则 | active | regression | console.services.mcp_query_service.call_tool[rainbond_create_gateway_rules] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_returns_bound_rule |
| console.gateway.create-tcp-rule | 创建 TCP 网关规则 | active | regression | console.services.mcp_query_service.call_tool[rainbond_create_gateway_rules] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_tcp_returns_bound_rule |
| console.gateway.dependency-container-port-schema | Gateway Dependency Container Port Schema | active | regression | console.services.mcp_query_service.call_tool[console.gateway.dependency-container-port-schema] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_dependency_schema_exposes_container_port_guidance |
| console.gateway.http-port-not-open | 对外端口未开启时拦截 HTTP 网关创建 | active | regression | console.services.mcp_query_service.create_gateway_rules[http] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_rejects_when_outer_port_is_unavailable |
| console.gateway.http-port-open-failure | HTTP 网关开端口失败时拦截创建 | active | regression | console.services.mcp_query_service.create_gateway_rules[http] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_rejects_port_open_failure |
| console.gateway.http-required | 创建 HTTP 网关规则时必须提供 http 参数 | active | regression | console.services.mcp_query_service.create_gateway_rules[http] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_requires_http_payload |
| console.gateway.http-rule-guard | 拦截重复的 HTTP 网关规则 | active | regression | console.services.mcp_query_service.create_gateway_rules[http] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_rejects_duplicate_rule |
| console.gateway.http-third-party-guard | 第三方组件不支持 HTTP 网关策略时拦截创建 | active | regression | console.services.mcp_query_service.create_gateway_rules[http] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_rejects_invalid_third_party_component |
| console.gateway.operation-schema | 暴露组件端口管理操作枚举 | active | regression | console.services.mcp_query_service._tool_manage_component_ports | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_ports_tool_schema_exposes_operation_enum |
| console.gateway.port-action-schema | 暴露组件端口操作枚举 | active | regression | console.services.mcp_query_service._tool_handle_component_ports | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_handle_component_ports_tool_schema_exposes_action_enum |
| console.gateway.port-constraints-schema | Gateway Port Constraints Schema | active | regression | console.services.mcp_query_service.call_tool[console.gateway.port-constraints-schema] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_ports_tool_schema_exposes_port_constraints |
| console.gateway.port-protocol-schema | 暴露组件端口协议枚举 | active | regression | console.services.mcp_query_service._tool_manage_component_ports | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_ports_tool_schema_exposes_protocol_enum |
| console.gateway.protocol-guard | 拦截不支持的网关协议 | active | regression | console.services.mcp_query_service.create_gateway_rules | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_rejects_invalid_protocol |
| console.gateway.source-code-from-schema | Gateway Source Code From Schema | active | regression | console.services.mcp_query_service.call_tool[console.gateway.source-code-from-schema] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_create_component_from_source_schema_exposes_code_from_guidance |
| console.gateway.tcp-port-open-failure | TCP 网关开端口失败时拦截创建 | active | regression | console.services.mcp_query_service.create_gateway_rules[tcp] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_tcp_rejects_port_open_failure |
| console.gateway.tcp-required | 创建 TCP 网关规则时必须提供 tcp 参数 | active | regression | console.services.mcp_query_service.create_gateway_rules[tcp] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_requires_tcp_payload |
| console.gateway.tcp-third-party-guard | 第三方组件不支持 TCP 网关策略时拦截创建 | active | regression | console.services.mcp_query_service.create_gateway_rules[tcp] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_tcp_rejects_invalid_third_party_component |
| console.gray-release.update-route-query-params | Gray Release Update Route Query Params | active | regression | console.services.gray_release_service.GrayReleaseService.update_route | console/tests/gray_release_service_test.py::GrayReleaseRouteUpdateTests.test_update_apisix_route_weights_keeps_service_alias_and_port_in_query |
| console.gray-release.update-route-query-uses-original-port | Gray Release Update Route Query Uses Original Port | active | regression | console.services.gray_release_service.GrayReleaseService.update_route | console/tests/gray_release_service_light_test.py::GrayReleaseRouteUpdateLightTests.test_update_route_query_uses_original_service_port_when_ports_differ |
| console.groupcopy.package-build-guard | 上传软件包组件禁止快速复制 | active | regression | console.services.groupcopy_service.GroupAppCopyService.get_modify_group_metadata | console/tests/groupcopy_service_test.py::GroupAppCopyServiceTests.test_get_modify_group_metadata_rejects_package_build |
| console.helm-release.delete | 删除 Helm 发布并清理来源记录 | active | regression | console.views.team_resources.HelmReleaseDetailView.delete | console/tests/team_resources_test.py::HelmReleasesViewTestCase |
| console.helm-release.detail | 查看 Helm 发布详情 | active | regression | console.views.team_resources.HelmReleaseDetailView.get | console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_get_enriches_helm_release_detail_with_source_info |
| console.helm-release.history | 查看 Helm 发布历史 | active | regression | console.views.team_resources.HelmReleaseHistoryView.get | console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_get_uses_team_namespace_for_helm_release_history |
| console.helm-release.install | 安装 Helm 发布并保存来源记录 | active | regression | console.views.team_resources.HelmReleasesView.post | console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_persists_install_source_after_success |
| console.helm-release.list | 查看 Helm 发布列表 | active | regression | console.views.team_resources.HelmReleasesView.get | console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_get_enriches_helm_release_list_with_source_info |
| console.helm-release.resolve-store-source | 操作前解析 Helm 商店来源信息 | active | regression | console.views.team_resources.Resolve store-backed helm source metadata | console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_enriches_store_install_with_saved_repo_metadata |
| console.helm-release.rollback | 回滚 Helm 发布 | active | regression | console.views.team_resources.HelmReleaseRollbackView.post | console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_uses_team_namespace_for_helm_release_rollback |
| console.helm-release.source-tracking | 追踪 Helm 发布来源信息 | active | regression | console.views.team_resources.Helm release source persistence lifecycle | console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_persists_install_source_after_success<br>console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_put_persists_upgrade_source_after_success<br>console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_delete_cleans_up_saved_install_source_after_success |
| console.helm-release.team-namespace-ops | 在团队命名空间内执行 Helm 操作 | active | regression | console.views.team_resources.Helm release lifecycle uses tenant namespace | console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_uses_team_namespace_for_helm_install<br>console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_delete_uses_team_namespace_for_helm_release_uninstall<br>console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_put_uses_team_namespace_for_helm_release_upgrade<br>console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_uses_team_namespace_for_helm_release_rollback |
| console.helm-release.upgrade | 升级 Helm 发布并保存来源记录 | active | regression | console.views.team_resources.HelmReleaseDetailView.put | console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_put_persists_upgrade_source_after_success |
| console.helm.build | 构建 Helm 应用模板 | active | regression | console.services.mcp_query_service.call_tool[rainbond_build_helm_app] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_build_helm_app_generates_template |
| console.helm.check | 检查 Helm 应用 | active | regression | console.services.mcp_query_service.call_tool[rainbond_check_helm_app] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_check_helm_app_returns_check_result |
| console.helm.daemonset-template | Helm DaemonSet 资源映射为组件模板 | active | regression | console.services.helm_app_yaml.HelmAppService.generate_template | console/tests/app_manage_test.py::ComponentDaemonSetSupportTests.test_helm_template_maps_daemonset_resource_type |
| console.image-webhook.harbor-push-artifact | 解析 Harbor 镜像推送 Webhook | active | regression | console.views.webhook.parse_image_webhook_payload | console/tests/webhook_test.py::ImageWebhookPayloadTestCase |
| console.image.python36-websocket-client | Console 镜像 Python 3.6 websocket-client 兼容性 | active | regression | requirements.txt | console/tests/dependency_compat_test.py::ConsoleImageDependencyCompatibilityTests |
| console.image.runner-detect | 根据仓库前缀识别 runner 镜像 | active | regression | console.utils.runner_util.is_runner | console/tests/utils/image_classify_test.py::ImageClassifyTests.test_is_runner |
| console.image.slug-detect | 为非 docker 类语言识别基于 runner 的 slug 镜像 | active | regression | console.utils.slug_util.is_slug | console/tests/utils/image_classify_test.py::ImageClassifyTests.test_is_slug |
| console.init-cluster.prefer-latest-pending | 初始化时优先选择最新待处理集群 | active | regression | console.repositories.init_cluster.Cluster.get_rke_cluster_exclude_integrated | console/tests/init_cluster_test.py::ClusterRepositoryTests.test_get_rke_cluster_exclude_integrated_prefers_latest_pending_cluster |
| console.init-cluster.recycle-empty-interconnected | 回收空白联通集群用于重新初始化 | active | regression | console.repositories.init_cluster.Cluster.get_rke_cluster_exclude_integrated | console/tests/init_cluster_test.py::ClusterRepositoryTests.test_get_rke_cluster_exclude_integrated_recycles_blank_cluster |
| console.k8s-attribute.cmd-args-yaml | 将 cmd 和 args Kubernetes 属性规范化为 YAML 数组 | active | regression | console.services.k8s_attribute.ComponentK8sAttributeService.create_k8s_attribute | console/tests/k8s_attribute_service_test.py::ComponentK8sAttributeServiceTests |
| console.k8s-attribute.upsert-region-sync | Console 与 region 组件 K8s 属性幂等同步 | active | regression | console.services.k8s_attribute.ComponentK8sAttributeService | console/tests/k8s_attribute_service_test.py |
| console.k8s-namespace.normalize-user-prefix | 将用户名规范化为合法的 Kubernetes 命名空间名 | active | regression | console.utils.validation.normalize_name_for_k8s_namespace | console/tests/utils/validation_test.py::NamespaceNormalizationTests.test_normalize_name_for_k8s_namespace |
| console.kubeblocks.app-resource-statistics | KubeBlocks 集群请求携带 app id 以支持资源统计 | active | regression | console.services.kubeblocks_service.KubeBlocksService._build_cluster_request | console/tests/kubeblocks_cluster_validation_test.py::KubeBlocksCreateFlowTests.test_build_cluster_request_includes_app_id_for_resource_statistics |
| console.kubeblocks.backup-repo.ready-guard | 使用 KubeBlocks 备份仓库前校验就绪状态 | active | regression | console.services.kubeblocks_service.KubeBlocksService.ensure_backup_repo_ready_for_use | console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_ensure_backup_repo_ready_for_use_rejects_prechecking_repo<br>console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_ensure_backup_repo_ready_for_use_accepts_ready_repo<br>console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_ensure_backup_repo_ready_for_use_rejects_missing_live_repo<br>console/tests/kubeblocks_cluster_validation_test.py::KubeBlocksCreateFlowTests.test_create_cluster_returns_backup_repo_not_ready_message |
| console.kubeblocks.backup-repo.team-create | 创建团队 KubeBlocks 备份仓库 | active | regression | console.services.kubeblocks_service.KubeBlocksService.create_backup_repo | console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_create_backup_repo_prefixes_namespace_and_does_not_store_secret_values<br>console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_create_backup_repo_defaults_to_prechecking_when_region_phase_is_empty<br>console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_create_backup_repo_rejects_existing_region_repo_name_even_if_deleted |
| console.kubeblocks.backup-repo.team-delete | 删除团队 KubeBlocks 备份仓库 | active | regression | console.services.kubeblocks_service.KubeBlocksService.delete_backup_repo | console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_delete_backup_repo_shows_clear_message_when_in_use |
| console.kubeblocks.backup-repo.team-list | 列出团队 KubeBlocks 备份仓库并合并实时状态 | active | regression | console.services.kubeblocks_service.KubeBlocksService.get_team_backup_repos | console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_list_backup_repos_merges_live_status_from_region<br>console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_list_backup_repos_keeps_failed_live_status<br>console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_list_backup_repos_marks_missing_when_region_resource_disappears |
| console.kubeblocks.backup-repo.team-ownership | 校验 KubeBlocks 备份仓库团队归属 | active | regression | console.services.kubeblocks_service.KubeBlocksService.ensure_backup_repo_belongs_to_team | console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_ensure_backup_repo_belongs_to_team_rejects_other_team_repo |
| console.kubeblocks.cluster-resource-validation | 校验 KubeBlocks 集群资源请求 | active | regression | console.services.kubeblocks_service.KubeBlocksService.validate_cluster_params | console/tests/kubeblocks_cluster_validation_test.py::KubeBlocksClusterValidationTests |
| console.kubeblocks.create-credential-sync | 创建 KubeBlocks 组件时同步连接凭据 | active | regression | console.services.kubeblocks_service.KubeBlocksService.create_complete_kubeblocks_component | console/tests/kubeblocks_cluster_validation_test.py::KubeBlocksCreateFlowTests |
| console.lang-version.proxy-upload | 代理旧版语言包上传接口 | active | regression | console.views.enterprise.UploadLongVersion.post | console/tests/lang_version_proxy_test.py::UploadLongVersionProxyViewTests |
| console.logging.default-no-debug-noise | 默认控制台日志过滤调试噪音 | active | regression | goodrain_web.settings.LOGGING | console/tests/logging_config_test.py::LoggingConfigTests.test_default_logger_level_defaults_to_info<br>console/tests/logging_config_test.py::LoggingConfigTests.test_ip_formatter_uses_record_level_name |
| console.market-app.create-template-scope-name | 按发布范围和团队检查应用市场模板重名 | active | regression | console.services.market_app_service.MarketAppService.create_rainbond_app | console/tests/market_app_service_test.py::MarketAppServiceCreateRainbondAppTests |
| console.market-app.install-default-storage-class | 应用市场安装使用平台默认存储类 | active | regression | console.services.market_app.new_components.NewComponents._template_to_volumes | console/tests/market_app_storage_test.py::MarketAppDefaultStorageClassTests.test_resolve_market_default_volume_type_prefers_configured_storage_class<br>console/tests/market_app_storage_test.py::MarketAppDefaultStorageClassTests.test_template_to_volumes_uses_configured_default_storage_class |
| console.market-app.install-unlimited-resources | 市场发布和安装保留不限制资源 | active | regression | console.services.share_services.ShareService.query_share_service_info / console.services.market_app.new_components.NewComponents._template_to_component / console.services.market_app_service.MarketAppService.__init_component_from_market_app / console.services.app_import_and_export_service.AppImportService.__normalize_import_component_template | console/tests/service_share_test.py::ShareServiceQueryResourceLimitTestCase.test_query_share_service_info_preserves_unlimited_resource_limits<br>console/tests/market_app_update_components_test.py::MarketAppNewComponentsResourceLimitTests.test_template_to_component_preserves_explicit_unlimited_cpu_and_memory<br>console/tests/market_app_service_test.py::MarketAppServiceResourceLimitTests.test_init_component_from_market_app_preserves_explicit_unlimited_cpu_and_memory<br>console/tests/app_import_and_export_service_test.py::AppImportServiceMetadataTestCase.test_save_enterprise_import_info_preserves_explicit_unlimited_resources |
| console.market-app.restore-preserves-volume-capacity-on-storage-fallback | 市场恢复在存储类型回退时保留卷容量 | active | regression | console.services.market_app.new_components.NewComponents._template_to_volumes | console/tests/market_app_storage_test.py::MarketAppDefaultStorageClassTests.test_template_to_volumes_preserves_capacity_when_storage_type_changes |
| console.market-app.restore-volume-capacity-helper | resolve_market_restore_volume_settings 在存储类型变化时保留容量 | active | regression | console.services.app_config.volume_service.AppVolumeService.resolve_market_restore_volume_settings | console/tests/market_app_storage_test.py::MarketAppDefaultStorageClassTests.test_resolve_market_restore_volume_settings_preserves_capacity_when_storage_type_changes |
| console.market-app.upgrade-share-image-fallback | Market App Upgrade Share Image Fallback | active | regression | console.services.market_app.update_components | console/tests/market_app_update_components_test.py::MarketAppUpdateComponentsCompatibilityTests.test_create_update_components_falls_back_to_image_when_share_image_missing |
| console.market-app.vm-disk-imports-from-template | 市场应用安装从 VM 模板生成磁盘导入配置 | active | regression | console.services.market_app.new_components.NewComponents._template_to_k8s_attributes | console/tests/market_app_update_components_test.py::MarketAppNewComponentsVMK8sAttrsTests.test_template_to_k8s_attributes_backfills_vm_runtime_attrs_from_vm_block |
| console.market-app.vm-runtime-status-guard | 虚拟机平台异常时禁止安装虚拟机模板 | active | regression | console.services.market_app_service.MarketAppService.install_app | console/tests/market_app_service_test.py::MarketAppServiceVMGuardTests |
| console.market-client.auth-missing | 将 401 应用市场错误转换为缺少 token 的服务异常 | active | regression | console.utils.restful_client.apiException | console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_401 |
| console.market-client.bad-request | 将通用 4xx 应用市场错误转换为参数错误响应 | active | regression | console.utils.restful_client.apiException | console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_generic_4xx |
| console.market-client.default-host | 使用默认回退 host 创建应用市场客户端 | active | regression | console.utils.restful_client.get_market_client | console/tests/utils/restful_client_test.py::RestfulClientFactoryTests.test_get_market_client_uses_default_host |
| console.market-client.deserialize-error | 将应用市场客户端反序列化失败转换为服务异常 | active | regression | console.utils.restful_client.apiException | console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_value_error |
| console.market-client.host-config | 使用显式 host 和认证头创建应用市场客户端 | active | regression | console.utils.restful_client.get_market_client | console/tests/utils/restful_client_test.py::RestfulClientFactoryTests.test_get_market_client_uses_explicit_host |
| console.market-client.not-found | 将 404 应用市场错误转换为资源不存在异常 | active | regression | console.utils.restful_client.apiException | console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_404 |
| console.market-client.permission-denied | 将 403 应用市场错误转换为商店权限异常 | active | regression | console.utils.restful_client.apiException | console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_403 |
| console.market-client.server-error | 将通用 5xx 应用市场错误转换为兜底服务异常 | active | regression | console.utils.restful_client.apiException | console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_generic_5xx |
| console.market.app-model-versions-local | Market App Model Versions Local | active | regression | console.services.mcp_query_service.call_tool[console.market.app-model-versions-local] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_model_versions_for_local_returns_versions |
| console.market.cloud-app-models | Market Cloud App Models | active | regression | console.services.mcp_query_service.call_tool[console.market.cloud-app-models] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_cloud_app_models_returns_market_templates |
| console.market.cloud-markets | Market Cloud Markets | active | regression | console.services.mcp_query_service.call_tool[console.market.cloud-markets] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_cloud_markets_returns_market_list |
| console.market.install-app-model-cloud | Market Install App Model Cloud | active | regression | console.services.mcp_query_service.call_tool[console.market.install-app-model-cloud] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_install_app_model_for_cloud_calls_market_app_service |
| console.market.local-app-models | Market Local App Models | active | regression | console.services.mcp_query_service.call_tool[console.market.local-app-models] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_local_app_models_returns_paginated_templates |
| console.mcp.app-health-overview | MCP 应用健康总览工具 | active | unit | console.services.mcp_query_service.call_tool[console.mcp.app-health-overview] | console/tests/mcp_query_health_overview_test.py |
| console.mcp.env-conflicts | MCP 环境变量多源冲突检测工具 | active | unit | console.services.mcp_query_service.call_tool[console.mcp.env-conflicts] | console/tests/mcp_query_env_conflicts_test.py |
| console.mcp.http-delete-session | 通过 HTTP 关闭 MCP 会话 | active | regression | console.views.mcp_query.MCPQueryHTTPView.delete | console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_delete_accepts_valid_session_token |
| console.mcp.http-expired-jwt | MCP HTTP 接口对过期 JWT 返回 401 | active | regression | console.views.mcp_query.MCPQueryHTTPView.post | console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_post_returns_401_for_expired_jwt |
| console.mcp.http-initialize | 通过 HTTP 初始化 MCP 会话 | active | regression | console.views.mcp_query.MCPQueryHTTPView.post | console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_initialize_returns_json_and_session_header |
| console.mcp.http-tools-list-with-auth | Mcp Http Tools List With Auth | active | regression | console.views.mcp_query.MCPQueryHTTPView | console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_post_tools_list_allows_authenticated_request_without_session_header |
| console.mcp.http-tools-sse | 通过 HTTP 端点以 SSE 返回工具列表 | active | regression | console.views.mcp_query.MCPQueryHTTPView.post | console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_post_can_return_sse_message_response |
| console.mcp.input-validation-contract | MCP 工具对缺参/查无组件返回清晰原因 | active | regression | console.services.mcp_query_service.call_tool | console/tests/mcp_query_error_contract_test.py::MCPComponentContextErrorTests.test_missing_service_id_returns_invalid_input<br>console/tests/mcp_query_error_contract_test.py::MCPComponentContextErrorTests.test_unknown_component_returns_not_found |
| console.mcp.legacy-sse-endpoint | 打开兼容模式的 SSE MCP 端点 | active | regression | console.views.mcp_query.MCPQuerySSEView.get | console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_get_returns_endpoint_event_for_legacy_sse_clients |
| console.mcp.operation-event-ids | MCP operate_app/upgrade_app 返回操作事件 ID | active | unit | console.services.mcp_query_service.call_tool[console.mcp.operation-event-ids] | console/tests/mcp_query_operation_event_ids_test.py |
| console.mcp.operation-failure-classifier | MCP 操作失败分类器 | active | unit | console.services.mcp_failure_classifier.classify_failure | console/tests/mcp_failure_classifier_test.py |
| console.mcp.operation-failure-context | MCP 操作失败上下文工具 | active | unit | console.services.mcp_query_service.call_tool[console.mcp.operation-failure-context] | console/tests/mcp_query_failure_context_test.py |
| console.mcp.post-message | 向 SSE 会话投递 MCP 消息 | active | regression | console.views.mcp_query.MCPQueryMessageView.post | console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_post_message_enqueues_initialize_response_on_sse_stream |
| console.mcp.serialize-nested-sdk-models | MCP 响应中递归序列化嵌套 SDK 模型 | active | regression | console.services.mcp_query_service.MCPQueryService._serialize_model_item | console/tests/mcp_query_service_test.py::MCPQueryServiceSerializeModelItemTests.test_serialize_model_item_recurses_into_dict_values<br>console/tests/mcp_query_service_test.py::MCPQueryServiceSerializeModelItemTests.test_serialize_model_item_handles_object_with_nested_sdk_attribute |
| console.mcp.structured-tool-error | Mcp Structured Tool Error | active | regression | console.views.mcp_query.MCPQueryHTTPView | console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_tool_error_includes_structured_validation_details |
| console.mcp.tool-error-fallback | 任意 MCP 工具失败均返回可解析错误 | active | regression | console.views.mcp_query.MCPQueryRPCMixin._dispatch_rpc | console/tests/mcp_query_error_contract_test.py::MCPToolErrorDispatchTests.test_generic_tool_exception_is_returned_as_parseable_error<br>console/tests/mcp_query_error_contract_test.py::MCPToolErrorDispatchTests.test_region_style_exception_maps_status_and_extracts_message |
| console.mcp.wait-for-build-completion | MCP 构建/部署就绪等待工具 | active | unit | console.services.mcp_query_service.call_tool[console.mcp.wait-for-build-completion] | console/tests/mcp_query_wait_build_test.py |
| console.ns-resource.batch-create | Ns Resource Batch Create | active | regression | console.views.team_resources | console/tests/team_resources_test.py::NsResourceDetailViewTestCase.test_post_preserves_partial_success_status_and_payload |
| console.ns-resource.update | 通过 YAML 更新命名空间资源 | active | regression | console.views.team_resources.NsResourceDetailView.put | console/tests/team_resources_test.py::NsResourceDetailViewTestCase.test_put_accepts_yaml_media_type_and_forwards_raw_body<br>console/tests/team_resources_test.py::RegionInvokeApiNsResourceTestCase.test_put_tenant_ns_resource_preserves_custom_content_type |
| console.oauth.instance-create | 创建 OAuth helper 实例并绑定服务与用户上下文 | active | regression | console.utils.oauth.oauth_types.get_oauth_instance | console/tests/utils/oauth_types_test.py::OAuthTypeTests.test_get_oauth_instance |
| console.oauth.kind-flags | 返回基础与 git OAuth helper 的能力标记 | active | regression | console.utils.oauth.base.git_oauth.GitOAuth2Interface.is_git_oauth | console/tests/utils/oauth_base_test.py::OAuthBaseTests.test_oauth_kind_flags |
| console.oauth.session-retry | 创建带重试 HTTP 适配器的 OAuth 会话 | active | regression | console.utils.oauth.base.oauth.OAuth2Interface.set_session | console/tests/utils/oauth_base_test.py::OAuthBaseTests.test_set_session_builds_retrying_requests_session |
| console.oauth.supported-types | 列出支持的 OAuth 服务类型 | active | regression | console.utils.oauth.oauth_types.get_support_oauth_servers | console/tests/utils/oauth_types_test.py::OAuthTypeTests.test_get_support_oauth_servers |
| console.oauth.token-update | 将刷新的 OAuth access/refresh token 持久化到绑定用户 | active | regression | console.utils.oauth.base.oauth.OAuth2Interface.update_access_token | console/tests/utils/oauth_base_test.py::OAuthBaseTests.test_update_access_token_updates_bound_user |
| console.oauth.unsupported-type | 拒绝不支持的 OAuth 服务类型 | active | regression | console.utils.oauth.oauth_types.get_oauth_instance | console/tests/utils/oauth_types_test.py::OAuthTypeTests.test_get_oauth_instance_unsupported_type |
| console.oauth.user-binding | 将 OAuth 服务和用户对象绑定到 helper 实例 | active | regression | console.utils.oauth.base.oauth.OAuth2Interface.set_oauth_user | console/tests/utils/oauth_base_test.py::OAuthBaseTests.test_set_oauth_user_and_service |
| console.operator-managed.skip-kubeblocks-services | Skip KubeBlocks services during operator-managed component import | active | regression | console.services.group_service.GroupService.get_watch_managed_data | console/tests/group_service_test.py::GroupServiceOperatorManagedTests |
| console.package-component.auto-create-flow | 执行制品包组件自动创建全流程 | active | regression | console.services.package_component_service.auto_create_component | console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_runs_full_package_flow |
| console.package-component.check-request-failure | 制品包组件检测请求失败时拦截创建 | active | regression | console.services.package_component_service.auto_create_component | console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_rejects_check_request_failure |
| console.package-component.deploy-failure | 制品包组件部署失败时拦截创建 | active | regression | console.services.package_component_service.auto_create_component | console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_rejects_deploy_failure |
| console.package-component.duplicate-name-guard | 制品包组件创建时拦截重复英文名 | active | regression | console.services.package_component_service.auto_create_component | console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_rejects_duplicate_k8s_component_name |
| console.package-component.multi-service-guard | 单组件流程中拦截多组件制品包检测结果 | active | regression | console.services.package_component_service.auto_create_component | console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_rejects_multi_service_package |
| console.package-component.require-upload-record | 创建制品包组件前必须存在上传记录 | active | regression | console.services.package_component_service.auto_create_component | console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_requires_existing_upload_record |
| console.package-component.upload-missing | 制品包列表为空时拦截组件创建 | active | regression | console.services.package_component_service.auto_create_component | console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_requires_uploaded_package_list |
| console.package-upload.archive-reuse | Package Upload Archive Reuse | active | regression | console.services.package_upload_tool_service | console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_prepare_upload_archive_reuses_supported_package_file |
| console.package-upload.archive-zip-dir | Package Upload Archive Zip Dir | active | regression | console.services.package_upload_tool_service | console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_prepare_upload_archive_zips_directory |
| console.package-upload.delete | Package Upload Delete | active | regression | console.services.mcp_query_service.call_tool[console.package-upload.delete] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_delete_package_upload_delegates_to_upload_tool_service |
| console.package-upload.delete-flow | Package Upload Delete Flow | active | regression | console.services.package_upload_tool_service | console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_delete_upload_cleans_remote_dir_and_marks_record |
| console.package-upload.file | Package Upload File | active | regression | console.services.mcp_query_service.call_tool[console.package-upload.file] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_upload_package_file_delegates_to_upload_tool_service |
| console.package-upload.init | Package Upload Init | active | regression | console.services.mcp_query_service.call_tool[console.package-upload.init] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_init_package_upload_delegates_to_upload_tool_service |
| console.package-upload.init-flow | Package Upload Init Flow | active | regression | console.services.package_upload_tool_service | console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_init_upload_creates_remote_dir_and_record |
| console.package-upload.local-package | Package Upload Local Package | active | regression | console.services.mcp_query_service.call_tool[console.package-upload.local-package] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_local_package_calls_upload_tool_service |
| console.package-upload.local-package-flow | Package Upload Local Package Flow | active | regression | console.services.package_upload_tool_service | console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_auto_create_component_from_local_path_runs_full_flow |
| console.package-upload.local-path-create-schema | create_component_from_local_package 工具 schema 暴露服务端本地路径指引 | active | regression | console.services.mcp_query_service.list_tools[console.package-upload.local-path-create-schema] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_create_component_from_local_package_tool_schema_exposes_server_side_local_path_guidance |
| console.package-upload.local-path-missing-details | _normalize_local_path 在路径缺失时抛出结构化详情 | active | regression | console.services.package_upload_tool_service.PackageUploadToolService._normalize_local_path | console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_normalize_local_path_raises_structured_details_when_path_missing |
| console.package-upload.local-path-required-details | _normalize_local_path 在路径为空时抛出结构化详情 | active | regression | console.services.package_upload_tool_service.PackageUploadToolService._normalize_local_path | console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_normalize_local_path_raises_structured_details_when_path_empty |
| console.package-upload.local-path-schema | Package Upload Local Path Schema | active | regression | console.services.mcp_query_service.call_tool[console.package-upload.local-path-schema] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_upload_package_file_tool_schema_exposes_local_path_guidance |
| console.package-upload.status | Package Upload Status | active | regression | console.services.mcp_query_service.call_tool[console.package-upload.status] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_package_upload_status_delegates_to_upload_tool_service |
| console.package-upload.status-flow | Package Upload Status Flow | active | regression | console.services.package_upload_tool_service | console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_get_upload_status_reads_packages_and_updates_record |
| console.package-upload.upload-flow | Package Upload Upload Flow | active | regression | console.services.package_upload_tool_service | console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_upload_package_uploads_archive_and_returns_status |
| console.platform-plugin.vm-access-url-fallback | 从前端组件访问地址回填官方虚拟机插件访问前缀 | active | regression | console.services.plugin_service.RainbondPluginService.list_plugins | console/tests/rbd_plugin_service_test.py::RainbondPluginServiceTests.test_official_vm_plugin_uses_frontend_component_access_url_when_region_urls_missing |
| console.platform-plugin.vm-runtime-status-guard | 校验虚拟机平台插件运行状态 | active | regression | console.services.platform_plugin_service.PlatformPluginService.ensure_vm_plugin_running | console/tests/platform_plugin_service_test.py::PlatformPluginServiceTests.test_ensure_vm_plugin_running_rejects_non_running_status |
| console.plugin-build.infer-arch | Infer plugin build architecture from region chaos nodes | active | regression | console.services.plugin_build_arch.resolve_plugin_build_arch | console/tests/plugin_build_arch_test.py::PluginBuildArchTests |
| console.plugin.delete-by-sid | 按组件 ID 删除其全部插件关联 | active | regression | console.repositories.plugin.service_plugin_repo.AppPluginRelationRepo.delete_by_sid | console/tests/service_plugin_repo_delete_by_sid_test.py::DeleteBySidTest.test_delete_by_sid_deletes_matching_relations |
| console.plugin.downstream-port-config | 下游端口配置从 ORM 模型对象读取目标组件属性 | active | regression | console.services.plugin.app_plugin.AppPluginService.create_plugin_cfg_4marketsvc | console/tests/app_plugin_downstream_port_test.py::CreatePluginCfg4MarketsvcDownstreamPortTest.test_downstream_port_reads_dest_service_attributes |
| console.pod.detail | Pod Detail | active | regression | console.services.mcp_query_service.call_tool[console.pod.detail] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_pod_detail_returns_runtime_diagnostics |
| console.pod.detail-kubeblocks | Pod Detail Kubeblocks | active | regression | console.services.mcp_query_service.call_tool[console.pod.detail-kubeblocks] | console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_pod_detail_uses_kubeblocks_endpoint_for_kubeblocks_component |
| console.port-inner.env-sync-idempotent | Treat duplicate region env create as idempotent during inner port enable | active | regression | console.services.app_config.env_service.AppEnvVarService.add_service_env_var | console/tests/env_service_region_idempotency_test.py::EnvServiceRegionIdempotencyTests.test_add_service_env_var_updates_region_when_env_already_exists<br>console/tests/env_service_region_idempotency_test.py::EnvServiceRegionIdempotencyTests.test_add_service_env_var_retries_add_when_region_update_reports_record_not_found<br>console/tests/env_service_region_idempotency_test.py::EnvServiceRegionIdempotencyTests.test_add_service_env_var_treats_second_add_conflict_as_success |
| console.random.default-version | 生成默认随机版本标识 | active | regression | console.utils.randomutil.make_default_version | console/tests/utils/randomutil_test.py::RandomUtilTests.test_make_default_version |
| console.realtime-proxy.docker-console-subprotocol | Docker 控制台后端使用 webtty 子协议 | active | regression | console.utils.realtime_proxy._backend_websocket_subprotocols | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_docker_console_backend_uses_webtty_subprotocol |
| console.realtime-proxy.docker-console-user-activity | Docker 控制台活动跟踪在用户输入时刷新 | active | regression | console.utils.realtime_proxy.DockerConsoleActivityTracker | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_docker_console_activity_tracker_refreshes_on_user_input |
| console.realtime-proxy.docker-console-user-idle-timeout | Docker 控制台活动跟踪忽略 webtty 心跳 | active | regression | console.utils.realtime_proxy.DockerConsoleActivityTracker | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_docker_console_activity_tracker_ignores_webtty_ping |
| console.realtime-proxy.file-operate-raw-multipart-forward | 文件操作上传原始转发 multipart 请求 | active | regression | console.utils.realtime_proxy.proxy_http_request | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_file_operate_upload_forwards_raw_multipart_body |
| console.realtime-proxy.forward-client-subprotocols | 转发客户端请求的 websocket 子协议 | active | regression | console.utils.realtime_proxy._backend_websocket_subprotocols | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_websocket_proxy_keeps_client_requested_subprotocols |
| console.realtime-proxy.http-forward | 实时代理 HTTP 转发 | active | regression | console.utils.realtime_proxy.proxy_http_request | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_http_proxy_forwards_upload_request_to_region_websocket_service |
| console.realtime-proxy.internal-target-override | 实时代理内部目标覆盖 | active | regression | console.utils.realtime_proxy.build_region_realtime_proxy_url | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_region_proxy_target_prefers_internal_override_for_builtin_region |
| console.realtime-proxy.multipart-folder-upload-forward | 转发文件夹上传中的重复 multipart 文件字段 | active | regression | console.utils.realtime_proxy.build_multipart_payload | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_multipart_folder_upload_encodes_repeated_file_field |
| console.realtime-proxy.multipart-upload-forward | 实时代理重建分片上传请求 | active | regression | console.utils.realtime_proxy.build_multipart_payload | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_http_proxy_rebuilds_multipart_upload_for_app_import |
| console.realtime-proxy.non-terminal-no-user-idle-timeout | 非终端实时代理不触发用户空闲超时 | active | regression | console.utils.realtime_proxy.DockerConsoleActivityTracker | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_non_docker_console_activity_tracker_never_user_idle_expires |
| console.realtime-proxy.package-build-raw-multipart-forward | 组件构建包上传原始转发 multipart 请求 | active | regression | console.utils.realtime_proxy.proxy_http_request | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_package_build_upload_forwards_raw_multipart_body |
| console.realtime-proxy.region-target-url | 实时代理 Region 目标 URL | active | regression | console.utils.realtime_proxy.build_region_realtime_proxy_url | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_region_proxy_target_keeps_region_websocket_host_for_http |
| console.realtime-proxy.secure-websocket-url | 实时代理安全 WebSocket URL | active | regression | console.utils.realtime_proxy.build_console_realtime_proxy_url | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_console_proxy_url_uses_wss_when_request_is_https |
| console.realtime-proxy.upload-url | 实时代理上传 URL | active | regression | console.services.app_import_and_export_service.get_upload_package_url | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_upload_package_url_returns_console_proxy_path |
| console.realtime-proxy.websocket-idle-timeout | 后端 websocket 使用短读超时检测空闲 | active | regression | console.utils.realtime_proxy.open_backend_websocket | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_backend_websocket_uses_short_read_timeout_for_idle_checks |
| console.realtime-proxy.websocket-url | 实时代理 WebSocket URL | active | regression | console.services.app_actions.app_log.AppWebSocketService.get_event_log_ws | console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_websocket_service_returns_console_proxy_url_without_6060 |
| console.region-api.batch-create-error-bean | Region Api Batch Create Error Bean | active | regression | www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status | console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_preserves_batch_create_result_bean_for_coded_errors |
| console.region-api.domain-conflict-msg | 将上游域名冲突保留为可操作的 409 错误提示 | active | regression | www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status | console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_keeps_domain_conflict_as_conflict_error |
| console.region-api.helm-resource-conflict-msg | 将 Helm 资源归属冲突转换为可操作错误提示 | active | regression | www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status | console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_translates_helm_ownership_conflict_to_actionable_msg_show |
| console.region-api.proxy-error-pass-through | 对非 Helm 冲突保留原始上游错误信息 | active | regression | www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status | console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_keeps_original_message_for_non_helm_conflicts |
| console.region-api.vm-snapshot-feature-gate-msg | _check_status 将虚拟机快照功能门禁错误翻译为可操作提示 | active | regression | www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status | console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_translates_snapshot_feature_gate_error_to_actionable_msg_show |
| console.region.update-region-config | 依据配置项是否存在选择更新或新增数据中心配置 | active | regression | console.services.region_services.RegionService.update_region_config | console/tests/region_config_update_test.py::UpdateRegionConfigTest.test_update_when_config_exists_passes_dict_value<br>console/tests/region_config_update_test.py::UpdateRegionConfigTest.test_add_when_config_missing_passes_json_string_and_desc |
| console.request-args.bool-coercion | 将请求中的布尔参数从字符串或布尔值安全转换 | active | regression | console.utils.reqparse.bool_argument | console/tests/utils/reqparse_test.py::BoolArgumentTestCase |
| console.request-args.bool-default-false | 缺失布尔查询参数时返回 false 默认值 | active | regression | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_default_false_bool |
| console.request-args.bool-default-true | 为布尔查询参数使用 true 默认值 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_default_bool |
| console.request-args.bool-invalid | 拒绝非法布尔查询参数值 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_bool_error |
| console.request-args.bool-parse | 解析布尔查询参数 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_bool |
| console.request-args.data-parse | 解析请求 data 载荷并处理默认值与必填校验 | active | regression | console.utils.reqparse.parse_item | console/tests/utils/reqparse_test.py::ParseDateTestCase |
| console.request-args.default-type-error | 拒绝类型不匹配的默认请求参数 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_default_error |
| console.request-args.int-missing | 整型查询参数缺失时返回空值 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_not__return_int |
| console.request-args.int-parse | 解析整型查询参数 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_int |
| console.request-args.int-required | 要求提供整型查询参数 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_int_must |
| console.request-args.int-required-missing | 拒绝缺失的必填整型查询参数 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_not_parse_argument_return_int_must |
| console.request-args.list-default-fallback | 缺失多值查询参数时返回列表默认值 | active | regression | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_list_default |
| console.request-args.list-missing | 列表查询参数缺失时返回空值 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_not_get_argument_return_list |
| console.request-args.list-parse | 将重复查询参数解析为列表 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_list |
| console.request-args.list-required | 要求提供列表查询参数 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_list_must |
| console.request-args.list-required-missing | 拒绝缺失的必填列表查询参数 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_not_parse_argument_return_list_must |
| console.request-args.parse-args-keep-falsy | 解析查询参数映射时保留 falsy 值 | active | regression | console.utils.reqparse.parse_args | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_args_keep_falsy_values |
| console.request-args.parse-batch | 按配置批量解析查询参数 | active | unit | console.utils.reqparse.parse_args | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_args |
| console.request-args.query-parse | 将查询字符串参数解析为带类型的值 | active | regression | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase |
| console.request-args.string-parse | 解析字符串查询参数 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_str |
| console.request-args.type-error | 拒绝不支持的请求参数类型 | active | unit | console.utils.reqparse.parse_argument | console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_value_type_error |
| console.request-data.dict-parse | 从字典请求体中解析字段 | active | unit | console.utils.reqparse.parse_item | console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_dict_data |
| console.request-data.item-parse | 解析单个请求体字段 | active | unit | console.utils.reqparse.parse_item | console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_item |
| console.request-data.item-required | 要求提供单个请求体字段 | active | unit | console.utils.reqparse.parse_item | console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_item_must |
| console.request-data.item-required-missing | 拒绝缺失的必填请求体字段 | active | unit | console.utils.reqparse.parse_item | console/tests/utils/reqparse_test.py::ParseDateTestCase.test_not_parse_item_must |
| console.request-data.parse-batch | 批量解析请求体数据 | active | unit | console.utils.reqparse.parse_date | console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_data |
| console.request-data.parse-date-keep-falsy | 解析请求 data 映射时保留 falsy 值 | active | regression | console.utils.reqparse.parse_date | console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_date_keep_falsy_values |
| console.request-data.required-default-error | 缺失请求 data 时抛出默认必填字段错误 | active | regression | console.utils.reqparse.parse_item | console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_item_required_uses_default_error_message |
| console.resource-center.pod-logs | 查看资源中心 Pod 日志 | active | regression | console.views.team_resources.ResourceCenterPodLogsView.get | console/tests/team_resources_test.py::ResourceCenterPodLogsViewTestCase.test_get_sends_heartbeat_before_upstream_logs<br>console/tests/regionapi_sse_proxy_test.py::RegionApiSSEProxyTests.test_sse_proxy_passes_region_auth_headers<br>console/tests/regionapi_sse_proxy_test.py::RegionApiSSEProxyTests.test_sse_proxy_rewrites_console_tenant_name_to_region_tenant_name<br>console/tests/regionapi_sse_proxy_test.py::RegionApiSSEProxyTests.test_get_component_pod_log_uses_bounded_read_timeout |
| console.rke2.cluster-install-structured-helm-error | Rainbond 安装失败时返回结构化错误且不进入集成中状态 | active | regression | console.views.rke2.ClusterRKEInstallRB.post | console/tests/rke2_cluster_errors_test.py::ClusterRKEErrorTests.test_cluster_install_returns_structured_helm_error_without_saving_integrating |
| console.rke2.cluster-missing-metadata-404 | 请求的 RKE 集群元数据缺失时返回 404 | active | regression | console.views.rke2.ClusterRKE.get | console/tests/rke2_cluster_errors_test.py::ClusterRKEErrorTests.test_cluster_get_returns_structured_404_when_cluster_metadata_missing |
| console.rke2.helm-subprocess-error-sanitized | 清洗 Rainbond 安装中的 Helm 子进程失败信息 | active | regression | console.utils.k8s_cli.K8sClient.install_rainbond | console/tests/rke2_cluster_errors_test.py::ClusterRKEErrorTests.test_install_rainbond_returns_sanitized_subprocess_error |
| console.service-share.create-record | 创建组件共享记录 | active | regression | console.views.service_share.ServiceShareRecordView.post | console/tests/service_share_test.py::ServiceShareRecordViewTestCase |
| console.service-share.create-snapshot-record | 创建基于快照的服务分享记录 | active | regression | console.views.service_share.ServiceShareRecordView.post | console/tests/service_share_test.py::ServiceShareRecordViewTestCase.test_post_snapshot_mode_uses_hidden_template_app_id |
| console.service-share.error-response | 服务分享异常时返回错误响应 | active | regression | console.views.service_share.ServiceShareRecordView.post | console/tests/service_share_test.py::ServiceShareRecordViewTestCase.test_post_returns_500_response_for_unexpected_exception |
| console.service-share.local-app-versions | 列出团队本地可分享应用版本 | active | regression | console.services.share_services.ShareService.get_team_local_apps_versions | console/tests/service_share_test.py::ShareServicePreferredAppTestCase.test_get_team_local_apps_versions_keeps_team_apps_when_preferred_app_is_hidden_snapshot |
| console.service-share.resolve-last-shared-app | 解析最近一次分享的应用版本 | active | regression | console.services.share_services.ShareService.get_last_shared_app_and_app_list | console/tests/service_share_test.py::ShareServicePreferredAppTestCase.test_get_last_shared_app_ignores_missing_versions_for_preferred_local_app |
| console.service-share.stopped-component-publish | 允许已停止组件发布 | active | regression | console.services.share_services.ShareService.check_service_source | console/tests/service_share_test.py::ShareServiceCheckServiceSourceTestCase |
| console.service-share.view-info | 查看组件共享详情 | active | regression | console.views.service_share.ServiceShareInfoView.get | console/tests/service_share_test.py::ServiceShareInfoViewTestCase |
| console.service-share.view-snapshot-info | 查看分享快照详情 | active | regression | console.views.service_share.ServiceShareInfoView.get | console/tests/service_share_test.py::ServiceShareInfoViewTestCase.test_get_returns_snapshot_template_payload |
| console.service-share.vm-qcow2-publish | 将虚拟机系统盘发布为 qcow2 镜像源 | active | regression | console.services.share_services.ShareService.sync_event | console/tests/service_share_test.py::ShareRepoVMServiceSourceTestCase.test_get_service_list_keeps_vm_run_components_for_publish<br>console/tests/service_share_test.py::ShareServiceCreateSnapshotPublishTestCase.test_sync_event_passes_vm_image_source_for_vm_publish<br>console/tests/service_share_test.py::ShareServiceCreateSnapshotPublishTestCase.test_sync_event_passes_vm_export_token_for_live_vm_publish<br>console/tests/service_share_test.py::ShareServiceVMPublishMetadataTestCase |
| console.service-share.vm-shutdown-guard | 虚拟机发布关机限制 | active | regression | console.services.share_services.ShareService.check_service_source | console/tests/service_share_test.py::ShareServiceCheckServiceSourceTestCase |
| console.source-component.auto-create-flow | 执行源码组件自动创建全流程 | active | regression | console.services.source_component_service.auto_create_component | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_runs_full_source_flow |
| console.source-component.build-config-error | 应用默认源码构建配置失败时抛错 | active | regression | console.services.source_component_service.apply_default_build_config | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_apply_default_build_config_raises_when_save_fails |
| console.source-component.check-failure | 源码组件检测失败时中止创建 | active | regression | console.services.source_component_service.auto_create_component | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_raises_on_check_failure |
| console.source-component.check-poll-failure | 源码组件检测失败时返回首个错误 | active | regression | console.services.source_component_service._wait_for_check_result | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_wait_for_check_result_raises_with_first_error_info |
| console.source-component.check-poll-success | 源码组件检测轮询直到成功 | active | regression | console.services.source_component_service._wait_for_check_result | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_wait_for_check_result_retries_until_success |
| console.source-component.check-request-failure | 源码组件检测请求失败时拦截创建 | active | regression | console.services.source_component_service.auto_create_component | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_rejects_check_request_failure |
| console.source-component.check-timeout-pending | Source Component Check Timeout Pending | active | regression | console.services.source_component_service | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_returns_pending_result_when_check_times_out |
| console.source-component.deploy-failure | 源码组件部署失败时拦截创建 | active | regression | console.services.source_component_service.auto_create_component | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_rejects_deploy_failure |
| console.source-component.detect-server-type | 识别源码仓库服务类型 | active | regression | console.services.source_component_service.infer_server_type | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_infer_server_type_supports_git_svn_and_oss |
| console.source-component.duplicate-name-guard | 源码组件创建时拦截重复英文名 | active | regression | console.services.source_component_service.auto_create_component | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_rejects_duplicate_k8s_component_name |
| console.source-component.invalid-server-type | 拦截不支持的源码仓库服务类型 | active | regression | console.services.source_component_service.infer_server_type | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_infer_server_type_rejects_unknown_server_type |
| console.source-component.multi-service-guard | 单组件流程中拦截多组件源码检测结果 | active | regression | console.services.source_component_service.auto_create_component | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_rejects_multi_service_detection |
| console.source-component.normalize-code-source | 规范化源码来源类型 | active | regression | console.services.source_component_service.normalize_code_from | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_normalize_code_from_maps_generic_git_to_gitlab_manual |
| console.source-component.normalize-code-version | 按来源类型规范化源码版本 | active | regression | console.services.source_component_service.normalize_code_version | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_normalize_code_version_handles_tag_and_oss |
| console.source-component.normalize-git-url | 为 Git 地址追加一次子目录参数 | active | regression | console.services.source_component_service.normalize_git_url | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_normalize_git_url_appends_subdirectory_once |
| console.source-component.prefer-dockerfile | Source Component Prefer Dockerfile | active | regression | console.services.source_component_service | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_prefers_dockerfile_when_requested |
| console.source-component.prefer-dockerfile-from-dockerfiles-flag | Source Component Prefer Dockerfile From Dockerfiles Flag | active | regression | console.services.source_component_service | console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_prefers_dockerfile_when_dockerfiles_exist |
| console.team.create-invalid-namespace | 创建团队时拒绝非法命名空间 | active | regression | console.views.team.AddTeamView.post | console/tests/add_team_namespace_validation_test.py::AddTeamInvalidNamespaceTest.test_invalid_namespace_raises_qualified_name_error_not_typeerror |
| console.test-manifest.ignore-worktrees | 测试清单校验忽略嵌套 worktree 测试 | active | regression | scripts.validate_test_manifest.collect_marked_tests | scripts/validate_test_manifest_test.py::ValidateTestManifestTests |
| console.timeutil.current-date-str | 返回默认格式的当前日期字符串 | active | regression | console.utils.timeutil.current_time_to_str | console/tests/utils/timeutil_test.py::TimeUtilTests.test_current_time_to_str |
| console.timeutil.current-time | 返回当前 datetime 对象 | active | regression | console.utils.timeutil.current_time | console/tests/utils/timeutil_test.py::TimeUtilTests.test_current_time |
| console.timeutil.current-time-str | 返回格式化的当前时间字符串 | active | regression | console.utils.timeutil.current_time_str | console/tests/utils/timeutil_test.py::TimeUtilTests.test_current_time_str |
| console.timeutil.format | 将 datetime 对象格式化为指定字符串 | active | regression | console.utils.timeutil.time_to_str | console/tests/utils/timeutil_test.py::TimeUtilTests.test_time_to_str |
| console.timeutil.parse | 将格式化时间字符串解析为 datetime 对象 | active | regression | console.utils.timeutil.str_to_time | console/tests/utils/timeutil_test.py::TimeUtilTests.test_str_to_time |
| console.tool-visibility.enterprise-admin | 向企业管理员暴露管理工具集 | active | regression | console.services.mcp_query_service.list_tools[enterprise_admin] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_list_tools_for_enterprise_admin_includes_region_and_enterprise_tools |
| console.tool-visibility.standard-user | 向普通用户隐藏企业管理工具 | active | regression | console.services.mcp_query_service.list_tools[standard_user] | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_list_tools_for_non_enterprise_admin_hides_region_and_enterprise_tools |
| console.url.path-legal | 校验路径是否满足 URL 路径合法性规则 | active | regression | console.utils.urlutil.is_path_legal | console/tests/utils/urlutil_test.py::UrlUtilTests.test_is_path_legal |
| console.url.query-build | 根据基础路径和参数构建 GET URL | active | regression | console.utils.urlutil.set_get_url | console/tests/utils/urlutil_test.py::UrlUtilTests.test_set_get_url |
| console.url.query-empty | 即使没有查询参数也能构建 GET URL | active | regression | console.utils.urlutil.set_get_url | console/tests/utils/urlutil_test.py::UrlUtilTests.test_set_get_url_with_empty_params |
| console.user.access-token-delete-log | 删除访问令牌时记录令牌备注 | active | regression | console.views.user_accesstoken.UserAccessTokenRUDView.delete | console/tests/user_accesstoken_delete_log_test.py::UserAccessTokenDeleteLogTest.test_delete_logs_token_note_without_nameerror |
| console.user.current-profile | 查看当前用户身份信息 | active | regression | console.services.mcp_query_service.get_current_user | console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_current_user_returns_identity_and_enterprise_admin_flag |
| console.user.favorite-delete-log | 删除收藏视图时记录收藏名称 | active | regression | console.views.user_operation.UserFavoriteUDView.delete | console/tests/user_favorite_delete_log_test.py::UserFavoriteDeleteLogTest |
| console.user.get-users-by-ids | 通过用户仓储按用户 ID 列表批量查询用户 | active | regression | console.services.user_services.UserService.get_users_by_user_ids | console/tests/user_services_get_by_ids_test.py::GetUsersByUserIdsTest.test_delegates_to_repo_get_by_user_ids |
| console.validation.display-name | 校验用户展示名称的中英文数字与连接符规则 | active | regression | console.utils.validation.validate_name | console/tests/utils/validation_test.py::NamespaceNormalizationTests.test_validate_name |
| console.validation.k8s-qualified-name | 校验 Kubernetes 合法资源名称格式 | active | regression | console.utils.validation.is_qualified_name | console/tests/utils/validation_test.py::NamespaceNormalizationTests.test_is_qualified_name |
| console.version.compare | 比较语义化风格的版本字符串 | active | regression | console.utils.version.compare_version | console/tests/utils/version_test.py::VersionUtilsTests.test_compare_version |
| console.version.newer-filter | 筛选出高于当前版本的新版本 | active | regression | console.utils.version.get_new_versions | console/tests/utils/version_test.py::VersionUtilsTests.test_get_new_versions |
| console.version.sort-desc | 按降序排列版本字符串 | active | regression | console.utils.version.sorted_versions | console/tests/utils/version_test.py::VersionUtilsTests.test_sorted_versions |
| console.virtual-machine.platform-runtime-guard | 虚拟机平台运行状态校验委托到平台插件守卫 | active | regression | console.services.virtual_machine.VirtualMachineService.ensure_vm_platform_running | console/tests/vm_create_flow_regression_test.py::VMCreateFlowRegressionTests.test_ensure_vm_platform_running_delegates_to_platform_plugin_guard |
| console.virtual-machine.registry-root-disk | 使用 registry 导入的系统盘创建虚拟机 | active | regression | console.services.virtual_machine.VirtualMachineService.create_vm | console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests |
| console.vm-asset.delete-active-reference-guard | 仅当活跃虚拟机仍引用时阻止删除镜像资产 | active | regression | console.services.virtual_machine.VirtualMachineService.delete_vm_image | console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_ignores_orphan_vm_asset_attrs<br>console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_blocks_active_vm_asset_reference<br>console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_ignores_incomplete_vm_service_reference |
| console.vm-asset.delete-internal-registry-manifest | Delete internal VM registry manifest before removing local VM asset | active | regression | console.services.virtual_machine.VirtualMachineService.delete_vm_image | console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_deletes_unique_internal_registry_manifest<br>console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_skips_registry_manifest_when_image_url_is_shared<br>console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_skips_registry_manifest_for_external_registry_asset |
| console.vm-asset.incomplete-service-cleanup-preserves-ready-assets | 删除未完成虚拟机组件时保留已就绪镜像资产 | active | regression | console.services.app_actions.app_manage.AppManageService._truncate_service | console/tests/app_manage_test.py::AppManageIncompleteVMCleanupTests.test_truncate_service_keeps_ready_uploaded_vm_asset |
| console.vm-asset.reference-components | 虚拟机镜像资产引用组件列表 | active | regression | console.services.virtual_machine.VirtualMachineService.serialize_vm_image | console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_get_vm_asset_includes_explicit_reference_components<br>console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_get_vm_asset_includes_legacy_image_reference_components |
| console.vm-overview.vnc-url-plugin-fallback | 在缺少查询参数时从插件回填虚拟机概览 VNC 地址 | active | regression | console.views.app_overview.AppDetailView.get | console/tests/vm_detail_view_test.py::AppVMDetailViewTests.test_get_builds_vm_vnc_url_from_plugin_fallback_when_query_param_missing |
| console.vm-profile.template-root-disk-fallback | VM profile falls back to template root disk metadata | active | regression | console.services.virtual_machine.VirtualMachineService.get_vm_profile | console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_get_vm_profile_falls_back_to_template_root_disk_metadata_when_asset_missing |
| console.vm-root-disk-selected-storage-type | update_check_app 为新建虚拟机根盘使用所选存储类型 | active | regression | console.services.app.AppService.update_check_app | console/tests/vm_live_migration_storage_test.py::VMLiveMigrationStorageTests.test_update_check_app_uses_selected_storage_type_for_new_vm_root_disk |
| console.vm-run.platform-runtime-guard | 虚拟机平台异常时禁止创建虚拟机组件 | active | regression | console.views.app_create.vm_run.VMRunCreateView.post | console/tests/vm_asset_instantiation_test.py::VMAssetInstantiationTests.test_vm_run_create_rejects_when_vm_plugin_not_running |
| console.vm-storage-any-access-mode | 允许虚拟机使用任意访问模式的存储 | active | regression | console.services.app_config.volume_service.AppVolumeService.build_vm_live_migration_volume_settings | console/tests/vm_live_migration_storage_test.py::VMLiveMigrationStorageTests |
| console.vm-template-import.delete-abnormal-vm | delete 允许异常状态虚拟机跳过运行中校验 | active | regression | console.services.app_actions.app_manage.AppManageService.delete | console/tests/app_manage_test.py::AppManageVMRestoreDeleteTests.test_delete_allows_abnormal_vm_to_skip_running_guard |
| console.vm-template-import.delete-restoring-vm | Allow deleting restoring VM components | active | regression | console.services.app_actions.app_manage.AppManageService.delete | console/tests/app_manage_test.py::AppManageVMRestoreDeleteTests |
| console.vm-template-import.restore-operation-record | VM template import restore operation record exposes progress | active | unit | console.services.app_actions.app_log.AppEventService.build_vm_restore_event | console/tests/vm_profile_runtime_status_test.py::VMRestoreEventTests.test_build_vm_restore_event_exposes_progress_and_importer_logs<br>console/tests/vm_profile_runtime_status_test.py::VMRestoreEventTests.test_build_vm_restore_event_marks_success_after_import_finishes |
| openapi.app-service.team-not-found | 应用关联的团队不存在时返回404错误 | active | regression | openapi.services.app_service.AppService.get_app_services_and_status | console/tests/openapi_app_service_team_not_found_test.py::AppServiceTeamNotFoundTest |
| openapi.app.create-third-component-deploy-key | OpenAPI 创建第三方 api 组件时生成密钥 | active | regression | openapi.views.apps.apps.CreateThirdComponentView.post | console/tests/openapi_third_component_deploy_repo_test.py::ThirdComponentDeployRepoTest.test_deploy_repo_is_the_singleton_not_the_module |
| openapi.app.team-apps-close | OpenAPI 关闭团队全部应用 | active | regression | openapi.views.apps.apps.TeamAppsCloseView.post | console/tests/openapi_team_apps_close_test.py::TeamAppsCloseTest.test_post_unpacks_three_return_values_from_batch_action |
| openapi.base.team-not-initialized-in-region | 团队未在该集群中初始化时返回409错误 | active | regression | openapi.views.base.TeamAPIView.initial | console/tests/openapi_base_team_region_init_test.py::TeamAPIViewRegionInitTest |
| openapi.enterprise.service-overview | OpenAPI 企业组件状态总览 | active | regression | openapi.views.enterprise_view.ServiceOverview.get | console/tests/openapi_service_overview_import_test.py::ServiceOverviewImportTest.test_service_overview_singleton_is_resolvable |
| openapi.service-config.domain-set-headers-service-default | HTTP 策略高级配置服务层默认缺失 set_headers | active | regression | console.services.app_config.domain_service.DomainService.update_http_rule_config | console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_http_rule_config_defaults_missing_set_headers_in_service |
| openapi.service-config.env-note-optional | OpenAPI 组件环境变量备注可省略 | active | regression | console.services.app_config.env_service.AppEnvVarService.update_or_create_envs | console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_update_or_create_envs_defaults_missing_note |
| openapi.service-config.http-set-headers-optional | OpenAPI HTTP 网关 set_headers 可省略 | active | regression | openapi.serializer.gateway_serializer.HTTPConfiguration | console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_http_configuration_defaults_missing_set_headers |
| openapi.service-config.port-alias-blank | OpenAPI 组件端口别名可留空自动生成 | active | regression | openapi.serializer.app_serializer.ComponentPortReqSerializers | console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_component_port_serializer_allows_blank_alias_for_auto_generation |
| openapi.service-config.port-open-outer-app-context | OpenAPI 开启组件外部端口时解析应用上下文 | active | regression | console.services.app_config.port_service.AppPortService.manage_port | console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_manage_port_resolves_app_when_opening_outer_port |
| openapi.service-config.validation-error-shape | OpenAPI 参数校验错误不返回 traceback | active | regression | console.views.base.custom_exception_handler | console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_validation_error_response_does_not_expose_traceback |
| openapi.team.delete-error-propagation | OpenAPI 删除团队时正确透出业务异常 | active | regression | openapi.views.team_view.TeamInfo.delete | console/tests/openapi_team_delete_except_test.py::TeamDeleteExceptTest.test_service_error_propagates_instead_of_typeerror |
| rainbond-console.vm-disks.container-disk-cdrom | VM disk layout accepts container disk CD-ROM media | active | regression | console.services.virtual_machine.VirtualMachineService.validate_vm_disk_layout | console/tests/vm_create_flow_regression_test.py::VMCreateFlowRegressionUnitTests.test_validate_vm_disk_layout_accepts_container_disk_cdrom<br>console/tests/vm_create_flow_regression_test.py::VMCreateFlowRegressionUnitTests.test_validate_vm_disk_layout_rejects_container_disk_without_image |
| rainbond-console.vm-disks.iso-installer-compat | 当 VM 运行时提示不完整时仍为 ISO 虚拟机磁盘列表补出安装光盘 | active | regression | console.services.virtual_machine.VirtualMachineService.list_vm_disks | console/tests/vm_disk_installer_compat_test.py::VMInstallerMediaCompatUnitTests.test_get_vm_runtime_config_includes_boot_source_format<br>console/tests/vm_disk_installer_compat_test.py::VMInstallerMediaCompatUnitTests.test_list_vm_disks_falls_back_to_asset_format_for_legacy_iso_vm_without_runtime_hint |
| rainbond-console.vm-export.asset-ready-storage-status | 虚拟机资产就绪需要 ready 状态与镜像地址 | active | regression | console.services.virtual_machine.VirtualMachineService.is_vm_asset_ready | console/tests/vm_create_flow_regression_test.py |
| rainbond-console.vm-live-migration-unique-disk-path | resolve_vm_volume_path 为虚拟机热迁移分配唯一磁盘路径 | active | regression | console.services.app_config.volume_service.AppVolumeService.resolve_vm_volume_path | console/tests/vm_live_migration_storage_test.py::VMLiveMigrationStorageTests.test_resolve_vm_volume_path_allocates_unique_disk_suffix_for_duplicate_vm_device_path<br>console/tests/vm_live_migration_storage_test.py::VMLiveMigrationStorageTests.test_resolve_vm_volume_path_keeps_existing_path_when_editing_same_vm_device_type |
| rainbond-console.vm-run.disk-asset-create | 从现有磁盘资产创建虚拟机时复用已就绪运行时镜像 | active | regression | console.views.app_create.vm_run.VMRunCreateView.post | console/tests/vm_asset_instantiation_test.py::VMAssetInstantiationTests::test_vm_run_create_from_existing_disk_asset_reuses_ready_runtime_image<br>console/tests/vm_asset_instantiation_test.py::VMAssetInstantiationTests::test_vm_run_create_uses_requested_format_for_suffixless_existing_disk_asset_import |
| rainbond-console.vm-run.vm-export-ignore-stale-boot-mode | resolve_vm_boot_mode 对 Windows ISO 忽略过期资产启动模式 | active | regression | console.services.virtual_machine.VirtualMachineService.resolve_vm_boot_mode | console/tests/vm_create_flow_regression_test.py |
| rainbond-console.vm-run.vm-export-multi-disk-create | 虚拟机运行创建支持多磁盘资产实例化 | active | regression | console.views.app_create.vm_run.VMRunCreateView.post | console/tests/vm_asset_instantiation_test.py |

## 详情

### 创建应用备份

- Capability ID: `console.app-backup.create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`, `console/services/backup_service.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_starts_group_backup`

### 组件使用自定义存储时阻止备份

- Capability ID: `console.app-backup.custom-volume-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_rejects_custom_volume_usage`

### 删除应用备份

- Capability ID: `console.app-backup.delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.delete`
- 代码路径: `console/views/center_pool/groupapp_backup.py`, `console/services/backup_service.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_delete_removes_group_backup`

### 删除应用备份前必须提供备份 ID

- Capability ID: `console.app-backup.delete-id-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.delete`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_delete_requires_backup_id`

### 备份进行中时阻止删除该备份记录

- Capability ID: `console.app-backup.delete-in-progress`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.backup_service.GroupAppBackupService.delete_group_backup_by_backup_id`
- 代码路径: `console/services/backup_service.py`
- 测试路径: `console/tests/backup_service_test.py::GroupAppBackupServiceDeleteInProgressTests`

### 删除备份时状态查询失败返回错误

- Capability ID: `console.app-backup.delete-status-lookup-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.delete`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_delete_returns_error_when_status_lookup_fails`

### 导出应用备份

- Capability ID: `console.app-backup.export`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`, `console/services/backup_service.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_returns_attachment_response`

### 应用备份导出失败时返回错误

- Capability ID: `console.app-backup.export-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_returns_error_when_service_fails`

### 导出备份时拦截不存在的应用组

- Capability ID: `console.app-backup.export-group-missing`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_rejects_missing_group`

### 导出应用备份前必须提供组 ID

- Capability ID: `console.app-backup.export-group-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_requires_group_id`

### 导出备份前必须提供备份 ID

- Capability ID: `console.app-backup.export-id-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_requires_backup_id`

### 导出备份时拦截不存在的团队

- Capability ID: `console.app-backup.export-team-missing`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_rejects_missing_team`

### 导出应用备份前必须提供团队名

- Capability ID: `console.app-backup.export-teamname-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupExportView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_export_requires_team_name`

### 强制备份时跳过前置校验

- Capability ID: `console.app-backup.force-bypass-guards`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_force_bypasses_backup_guards`

### 创建应用备份前必须提供组 ID

- Capability ID: `console.app-backup.group-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_requires_group_id`

### 导入应用备份

- Capability ID: `console.app-backup.import`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`, `console/services/backup_service.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_creates_restore_record`

### 应用备份导入失败时返回错误

- Capability ID: `console.app-backup.import-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_returns_error_when_service_fails`

### 导入备份前必须上传备份文件

- Capability ID: `console.app-backup.import-file-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_requires_file`

### 拦截超大备份导入文件

- Capability ID: `console.app-backup.import-file-size-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_rejects_file_larger_than_limit`

### 导入应用备份前必须提供组 ID

- Capability ID: `console.app-backup.import-group-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupImportView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupTransferWorkflowTests.test_import_requires_group_id`

### 查询团队全部备份列表

- Capability ID: `console.app-backup.list-all`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_backup.AllTeamGroupAppsBackupView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`, `console/services/backup_service.py`
- 测试路径: `console/tests/groupapp_backup_listing_test.py::GroupAppsBackupListingTests.test_all_team_group_apps_backup_view_marks_deleted_groups`

### 查询单个应用备份列表

- Capability ID: `console.app-backup.list-by-app`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_backup.TeamGroupAppsBackupView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`, `console/services/backup_service.py`
- 测试路径: `console/tests/groupapp_backup_listing_test.py::GroupAppsBackupListingTests.test_team_group_apps_backup_view_returns_backup_list`

### 查询应用备份列表时必须提供组 ID

- Capability ID: `console.app-backup.list-by-app-group-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.TeamGroupAppsBackupView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_listing_test.py::GroupAppsBackupListingTests.test_team_group_apps_backup_view_requires_group_id`

### 查询应用备份状态列表

- Capability ID: `console.app-backup.list-status`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`, `console/services/backup_service.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewTests.test_get_returns_backup_status_list_without_internal_server_info`

### 备份状态列表不存在时返回成功空结果

- Capability ID: `console.app-backup.list-status-empty`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewTests.test_get_returns_success_when_status_not_found`

### 备份状态列表查询失败时返回错误

- Capability ID: `console.app-backup.list-status-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewTests.test_get_returns_error_when_status_query_fails`

### 查询备份状态列表时必须提供组 ID

- Capability ID: `console.app-backup.list-status-group-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewTests.test_get_requires_group_id`

### 创建应用备份前必须选择模式

- Capability ID: `console.app-backup.mode-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_requires_backup_mode`

### 创建应用备份前必须填写说明

- Capability ID: `console.app-backup.note-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_requires_backup_note`

### 对象存储未配置时标记备份列表状态

- Capability ID: `console.app-backup.object-storage-unconfigured`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.TeamGroupAppsBackupView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_listing_test.py::GroupAppsBackupListingTests.test_team_group_apps_backup_view_marks_object_storage_unconfigured`

### 查询应用备份状态

- Capability ID: `console.app-backup.query-status`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`, `console/services/backup_service.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_get_returns_group_backup_status`

### 查询单个备份状态失败时返回错误

- Capability ID: `console.app-backup.query-status-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_get_returns_error_when_status_query_fails`

### 查询备份状态时必须提供备份 ID

- Capability ID: `console.app-backup.query-status-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_get_requires_backup_id`

### 按当前 region 应用范围限制备份组件

- Capability ID: `console.app-backup.region-app-scope`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.backup_service.GroupAppBackupService._get_effective_group_services`
- 代码路径: `console/services/backup_service.py`
- 测试路径: `console/tests/backup_service_test.py::GroupAppBackupServiceScopeTests`

### 有状态组件未关闭时阻止备份

- Capability ID: `console.app-backup.state-service-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupView.post`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupViewWorkflowTests.test_post_rejects_running_stateful_services`

### 隐藏备份状态中的内部服务端信息

- Capability ID: `console.app-backup.status-sanitize`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_backup.GroupAppsBackupStatusView.get`
- 代码路径: `console/views/center_pool/groupapp_backup.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsBackupStatusViewWorkflowTests.test_get_returns_backup_status_list_without_internal_server_info`

### 备份版本与平台版本不一致时阻止恢复

- Capability ID: `console.app-backup.version-check`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.backup_data_service.PlatformDataBackupServices.version_than`
- 代码路径: `console/services/backup_data_service.py`
- 测试路径: `console/tests/backup_data_service_version_than_test.py::VersionThanTests`

### 将检测出的组件 cmd 和 args 持久化为 YAML 数组

- Capability ID: `console.app-check.cmd-args-yaml`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_check_service.AppCheckService.save_service_info`
- 代码路径: `console/services/app_check_service.py`
- 测试路径: `console/tests/app_check_k8s_attribute_test.py::AppCheckK8sAttributeTests`

### 创建应用配置组

- Capability ID: `console.app-config-group.create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_config_group.AppConfigGroupService.create_config_group`
- 代码路径: `console/services/app_config_group.py`, `console/views/app_config_group.py`
- 测试路径: `console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_create_config_group_creates_remote_and_local_records`

### 删除应用配置组

- Capability ID: `console.app-config-group.delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_config_group.AppConfigGroupService.delete_config_group`
- 代码路径: `console/services/app_config_group.py`, `console/views/app_config_group.py`
- 测试路径: `console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_delete_config_group_deletes_remote_and_local_records`

### 查看应用配置组详情

- Capability ID: `console.app-config-group.get`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_config_group.AppConfigGroupService.get_config_group`
- 代码路径: `console/services/app_config_group.py`, `console/views/app_config_group.py`
- 测试路径: `console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_get_config_group_returns_built_response`

### 查询应用配置组列表

- Capability ID: `console.app-config-group.list`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_config_group.AppConfigGroupService.list_config_groups`
- 代码路径: `console/services/app_config_group.py`, `console/views/app_config_group.py`
- 测试路径: `console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_list_config_groups_returns_items_and_total`

### 更新应用配置组

- Capability ID: `console.app-config-group.update`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_config_group.AppConfigGroupService.update_config_group`
- 代码路径: `console/services/app_config_group.py`, `console/views/app_config_group.py`
- 测试路径: `console/tests/app_config_group_service_test.py::AppConfigGroupServiceWorkflowTests.test_update_config_group_updates_remote_and_local_records`

### 应用配置存储服务模块导出

- Capability ID: `console.app-config.volume-service-module-export`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.services.app_config.volume_service.volume_service`
- 代码路径: `console/services/app_config/volume_service.py`, `console/services/app_config/__init__.py`
- 测试路径: `console/tests/app_config_volume_service_import_test.py::AppConfigVolumeServiceImportTests.test_volume_service_module_exports_package_singleton`

### App creator full permissions

- Capability ID: `console.app-creator.full-permissions`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.perm_services.UserKindPermService.get_user_perms`
- 代码路径: `console/services/perm_services.py`
- 测试路径: `console/tests/perm_services_test.py`

### 查询应用导出状态

- Capability ID: `console.app-export.query-status`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_import_and_export_service.AppExportService.get_export_status`
- 代码路径: `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::AppExportServiceMetadataTestCase.test_get_export_status_updates_exporting_record_and_wraps_download_url`

### 放弃应用导入

- Capability ID: `console.app-import.abandon`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.app_import.CenterAppImportView.delete`
- 代码路径: `console/views/center_pool/app_import.py`, `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::CenterAppImportViewWorkflowTestCase.test_delete_abandons_import`

### 创建导入目录

- Capability ID: `console.app-import.create-dir`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.app_import.CenterAppTarballDirView.post`
- 代码路径: `console/views/center_pool/app_import.py`, `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::AppImportPreparationWorkflowTestCase.test_tarball_dir_post_creates_import_dir`

### 删除导入目录

- Capability ID: `console.app-import.delete-dir`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.app_import.CenterAppTarballDirView.delete`
- 代码路径: `console/views/center_pool/app_import.py`, `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::AppImportPreparationWorkflowTestCase.test_tarball_dir_delete_removes_import_dir`

### 处理导入应用模板身份冲突

- Capability ID: `console.app-import.identity-collision`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_import_and_export_service.AppImportService.__save_enterprise_import_info`
- 代码路径: `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::AppImportServiceMetadataTestCase.test_save_enterprise_import_info_splits_same_key_when_name_differs`, `console/tests/app_import_and_export_service_test.py::AppImportServiceMetadataTestCase.test_save_enterprise_import_info_keeps_same_key_and_name_as_multiple_versions`, `console/tests/app_import_and_export_service_test.py::AppImportServiceMetadataTestCase.test_save_enterprise_import_info_splits_same_key_name_version_when_content_differs`

### 初始化应用导入

- Capability ID: `console.app-import.init`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.app_import.EnterpriseAppImportInitView.post`
- 代码路径: `console/views/center_pool/app_import.py`, `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::AppImportPreparationWorkflowTestCase.test_enterprise_import_init_creates_record_when_none_exists`

### 查询导入目录中的应用包

- Capability ID: `console.app-import.list-dir`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.app_import.CenterAppTarballDirView.get`
- 代码路径: `console/views/center_pool/app_import.py`, `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::AppImportPreparationWorkflowTestCase.test_tarball_dir_get_lists_imported_packages`

### 查询 OpenAPI 应用导入状态

- Capability ID: `console.app-import.openapi-query-status`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_import_and_export_service.AppImportService.openapi_deploy_app_get_import_by_event_id`
- 代码路径: `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::AppImportStatusUpdateTestCase.test_openapi_deploy_app_get_import_by_event_id_skips_unchanged_status_save`

### 查询应用导入状态

- Capability ID: `console.app-import.query-status`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.app_import.CenterAppImportView.get`
- 代码路径: `console/views/center_pool/app_import.py`, `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::CenterAppImportViewWorkflowTestCase.test_get_returns_import_status`, `console/tests/app_import_and_export_service_test.py::CenterAppImportViewWorkflowTestCase.test_get_preserves_database_error_when_transaction_is_broken`, `console/tests/app_import_and_export_service_test.py::AppImportStatusUpdateTestCase.test_get_and_update_import_by_event_id_skips_unchanged_running_status_save`, `console/tests/app_import_and_export_service_test.py::AppImportStatusUpdateTestCase.test_get_and_update_import_by_event_id_saves_partial_success_once`

### 开始应用导入

- Capability ID: `console.app-import.start`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.app_import.CenterAppImportView.post`
- 代码路径: `console/views/center_pool/app_import.py`, `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::CenterAppImportViewWorkflowTestCase.test_post_starts_app_import`

### 端口绑定失败时记录并返回，且不跳过后续端口

- Capability ID: `console.app-migrate.port-bind-failure-visible`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.groupapp_recovery.groupapps_migrate.GroupappsMigrateService.__save_port`
- 代码路径: `console/services/groupapp_recovery/groupapps_migrate.py`
- 测试路径: `console/tests/groupapps_migrate_save_port_test.py::SavePortHttpFailureVisibleTest.test_first_port_failure_does_not_skip_second_and_is_reported`

### 清理旧应用时拦截已删除的原组

- Capability ID: `console.app-migration.cleanup-group-missing`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsView.delete`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_rejects_missing_original_group`

### 清理旧应用前必须提供原组 ID

- Capability ID: `console.app-migration.cleanup-group-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsView.delete`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_requires_group_id`

### 清理旧应用前必须提供恢复后的组 ID

- Capability ID: `console.app-migration.cleanup-new-group-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsView.delete`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_requires_new_group_id`

### 恢复后清理旧应用数据

- Capability ID: `console.app-migration.cleanup-old-app`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsView.delete`
- 代码路径: `console/views/center_pool/groupapp_migration.py`, `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_cleans_old_group_after_restore`

### 恢复到当前组时跳过清理

- Capability ID: `console.app-migration.cleanup-same-group-noop`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsView.delete`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_skips_cleanup_when_restored_to_same_group`

### 清理旧应用时拦截不存在的新组

- Capability ID: `console.app-migration.cleanup-target-group-missing`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsView.delete`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationCleanupTests.test_delete_rejects_missing_restored_group`

### 查询应用迁移状态

- Capability ID: `console.app-migration.query-status`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsMigrateView.get`
- 代码路径: `console/views/center_pool/groupapp_migration.py`, `console/services/groupapp_recovery/groupapps_migrate.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_get_returns_migration_status`

### 迁移记录不存在时返回未找到

- Capability ID: `console.app-migration.record-missing`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsMigrateView.get`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_get_returns_not_found_when_record_missing`

### 查询迁移状态时必须提供恢复 ID

- Capability ID: `console.app-migration.restore-id-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsMigrateView.get`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_get_requires_restore_id`

### 启动应用迁移

- Capability ID: `console.app-migration.start`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post`
- 代码路径: `console/views/center_pool/groupapp_migration.py`, `console/services/groupapp_recovery/groupapps_migrate.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_starts_group_migration`

### 拦截团队无权限的迁移目标集群

- Capability ID: `console.app-migration.target-region-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_rejects_region_without_team_access`

### 拦截不存在的迁移目标团队

- Capability ID: `console.app-migration.target-team-missing`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_rejects_missing_target_team`

### 启动应用迁移前必须指定目标团队

- Capability ID: `console.app-migration.team-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_requires_target_team`

### 查询未完成的应用迁移记录

- Capability ID: `console.app-migration.unfinished-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.center_pool.groupapp_migration.MigrateRecordView.get`
- 代码路径: `console/views/center_pool/groupapp_migration.py`, `console/repositories/migration_repo.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrateRecordViewTests.test_get_returns_unfinished_migration_record`

### 无未完成迁移记录时返回已完成状态

- Capability ID: `console.app-migration.unfinished-record-empty`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.MigrateRecordView.get`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrateRecordViewTests.test_get_returns_finished_when_no_unfinished_record`

### 查询未完成迁移记录时必须提供 group_uuid

- Capability ID: `console.app-migration.unfinished-record-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.MigrateRecordView.get`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrateRecordViewTests.test_get_requires_group_uuid`

### 目标团队无可用集群时阻止迁移

- Capability ID: `console.app-migration.usable-region-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.center_pool.groupapp_migration.GroupAppsMigrateView.post`
- 代码路径: `console/views/center_pool/groupapp_migration.py`
- 测试路径: `console/tests/groupapp_backup_migration_test.py::GroupAppsMigrationViewWorkflowTests.test_post_rejects_when_target_team_has_no_usable_regions`

### App Publish Candidates

- Capability ID: `console.app-publish.candidates`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-publish.candidates]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_publish_candidates_returns_models`

### 垂直伸缩未传 GPU 时保留组件当前值

- Capability ID: `console.app-scale.vertical-gpu-default`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_actions.app_manage.AppManageService.vertical_upgrade`
- 代码路径: `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/vertical_upgrade_gpu_test.py::VerticalUpgradeGPUTests.test_omitted_gpu_keeps_current_value_instead_of_null`, `console/tests/vertical_upgrade_gpu_test.py::VerticalUpgradeGPUTests.test_omitted_gpu_defaults_to_zero_when_current_is_none`, `console/tests/vertical_upgrade_gpu_test.py::VerticalUpgradeGPUTests.test_explicit_gpu_is_applied_and_sent_to_region`

### App Share Complete

- Capability ID: `console.app-share.complete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-share.complete]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_complete_app_share_calls_share_service_complete`

### App Share Create Record

- Capability ID: `console.app-share.create-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-share.create-record]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_share_record_supports_snapshot_mode`

### App Share Events

- Capability ID: `console.app-share.events`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-share.events]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_list_app_share_events_returns_service_and_plugin_events`

### App Share Get Event

- Capability ID: `console.app-share.get-event`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-share.get-event]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_share_event_returns_event_status`

### App Share Giveup

- Capability ID: `console.app-share.giveup`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-share.giveup]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_giveup_app_share_deletes_draft_record`

### App Share Info

- Capability ID: `console.app-share.info`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-share.info]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_share_info_returns_snapshot_payload`

### App Share Start Event

- Capability ID: `console.app-share.start-event`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-share.start-event]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_start_app_share_event_calls_sync_event`

### App Share Submit Info

- Capability ID: `console.app-share.submit-info`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-share.submit-info]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_submit_app_share_info_calls_share_service`

### 根据组件状态聚合 Rainbond 应用状态

- Capability ID: `console.app-status.aggregate-rainbond-components`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.group_service.GroupService.get_app_status`
- 代码路径: `console/services/group_service.py`, `console/services/topological_services.py`
- 测试路径: `console/tests/group_service_test.py::GroupServiceAppStatusAggregationTests.test_get_app_status_uses_component_aggregation_for_rainbond_apps`

### 将关闭与未部署组件组合识别为应用已关闭

- Capability ID: `console.app-status.closed-with-undeploy-components`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.topological_services.TopologicalService.get_app_status`
- 代码路径: `console/services/topological_services.py`
- 测试路径: `console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_closed_and_undeploy_components_make_app_closed`

### 当组件为关闭或未部署时将列表应用状态聚合为关闭

- Capability ID: `console.app-status.list-closed-with-undeploy-components`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.group_service.GroupService._add_component_status_to_apps`
- 代码路径: `console/services/group_service.py`, `console/services/topological_services.py`
- 测试路径: `console/tests/group_service_test.py::GroupServiceAppStatusAggregationTests.test_add_component_status_to_apps_marks_closed_when_components_are_closed_or_undeploy`

### 将运行中与异常混合组件识别为部分异常

- Capability ID: `console.app-status.partial-abnormal-mixed-components`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.topological_services.TopologicalService.get_app_status`
- 代码路径: `console/services/topological_services.py`
- 测试路径: `console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_mixed_abnormal_components_make_app_partially_abnormal`

### 将 some_abnormal 组件识别为部分异常

- Capability ID: `console.app-status.partial-abnormal-some-abnormal`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.topological_services.TopologicalService.get_app_status`
- 代码路径: `console/services/topological_services.py`
- 测试路径: `console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_some_abnormal_component_makes_app_partially_abnormal`

### 归一化集群应用状态返回（AppStatus TypedDict 落地）

- Capability ID: `console.app-status.region-status-typeddict`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.group_service.GroupService.get_app_status`
- 代码路径: `console/services/group_service.py`, `www/apiclient/regionapi.py`, `www/apiclient/region_types.py`
- 测试路径: `console/tests/group_app_status_typeddict_test.py::GroupAppStatusTypedDictTest`

### VM import building components keep app starting

- Capability ID: `console.app-status.vm-import-building-is-starting`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `service_method`
- 业务入口: `console.services.topological_services.TopologicalService.get_app_status`
- 代码路径: `console/services/topological_services.py`
- 测试路径: `console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_building_components_make_app_starting`

### VM import restoring components keep app starting

- Capability ID: `console.app-status.vm-import-restoring-is-starting`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `service_method`
- 业务入口: `console.services.topological_services.TopologicalService.get_app_status`
- 代码路径: `console/services/topological_services.py`
- 测试路径: `console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_restoring_components_make_app_starting`

### 将 waiting 组件识别为应用启动中

- Capability ID: `console.app-status.waiting-is-starting`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.topological_services.TopologicalService.get_app_status`
- 代码路径: `console/services/topological_services.py`
- 测试路径: `console/tests/topological_service_test.py::TopologicalServiceAppStatusTests.test_waiting_components_make_app_starting`

### App Upgrade Changes

- Capability ID: `console.app-upgrade.changes`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.changes]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_upgrade_changes_returns_diff_payload`

### App Upgrade Create Record

- Capability ID: `console.app-upgrade.create-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.create-record]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_upgrade_record_calls_upgrade_service`

### App Upgrade Deploy Record

- Capability ID: `console.app-upgrade.deploy-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.deploy-record]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_deploy_app_upgrade_record_calls_deploy`

### App Upgrade Detail

- Capability ID: `console.app-upgrade.detail`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.detail]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_upgrade_detail_returns_record_and_versions`

### App Upgrade Execute Record

- Capability ID: `console.app-upgrade.execute-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.execute-record]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_execute_app_upgrade_record_calls_upgrade_service`

### 查询应用升级信息

- Capability ID: `console.app-upgrade.info`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_app_upgrade_info]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/market_app_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_upgrade_info_returns_upgrade_items`

### App Upgrade Last Record

- Capability ID: `console.app-upgrade.last-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.last-record]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_last_upgrade_record_returns_snapshot_metadata`

### OpenAPI 升级向记录创建传递 upgrade_group_id

- Capability ID: `console.app-upgrade.openapi-upgrade-group-id`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.upgrade_services.UpgradeService.openapi_upgrade_app_models`
- 代码路径: `console/services/upgrade_services.py`
- 测试路径: `console/tests/upgrade_services_test.py::OpenapiUpgradeGroupIdTests`

### App Upgrade Record

- Capability ID: `console.app-upgrade.record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.record]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_upgrade_record_returns_record_detail`

### 应用升级记录状态汇总

- Capability ID: `console.app-upgrade.record-status-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.upgrade_services.UpgradeService._update_app_record_status`
- 代码路径: `console/services/upgrade_services.py`
- 测试路径: `console/tests/upgrade_services_test.py::UpgradeServiceRecordStatusTests`

### App Upgrade Records

- Capability ID: `console.app-upgrade.records`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.records]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_upgrade_records_returns_paginated_items`

### App Upgrade Rollback

- Capability ID: `console.app-upgrade.rollback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.rollback]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_rollback_app_upgrade_record_calls_restore`

### App Upgrade Rollback Records

- Capability ID: `console.app-upgrade.rollback-records`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-upgrade.rollback-records]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_rollback_records_returns_items`

### 生成应用版本组件差异明细

- Capability ID: `console.app-version.component-diff-details`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service._build_component_diff_details`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceComponentDiffDetailTestCase.test_build_component_diff_details_tracks_added_removed_and_field_updates`, `console/tests/app_version_test.py::AppVersionServiceComponentDiffDetailTestCase.test_build_component_diff_details_tracks_connect_envs_and_other_changes`

### App Version Create App From Snapshot

- Capability ID: `console.app-version.create-app-from-snapshot`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-version.create-app-from-snapshot]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_from_snapshot_version_installs_hidden_template_into_new_app`

### 从快照版本创建应用时拒绝非法目标应用名

- Capability ID: `console.app-version.create-app-from-snapshot-invalid-name`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-version.create-app-from-snapshot-invalid-name]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_from_snapshot_version_returns_structured_details_for_illegal_target_app_name`

### 创建应用版本快照

- Capability ID: `console.app-version.create-snapshot`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_version.AppVersionSnapshotListView.post`
- 代码路径: `console/views/app_version.py`, `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionSnapshotListViewPostTestCase`, `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_version_snapshot_calls_app_version_service`

### 删除应用版本回滚记录

- Capability ID: `console.app-version.delete-rollback-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_version.AppVersionRollbackRecordDetailView.delete`
- 代码路径: `console/views/app_version.py`, `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRecordViewTestCase.test_delete_removes_rollback_record`

### 删除应用版本快照

- Capability ID: `console.app-version.delete-snapshot`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_version.AppVersionSnapshotDetailView.delete`
- 代码路径: `console/views/app_version.py`, `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionSnapshotDetailViewDeleteTestCase`

### 通过接口删除应用版本快照

- Capability ID: `console.app-version.delete-snapshot-endpoint`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_version.AppVersionSnapshotDetailView.delete`
- 代码路径: `console/views/app_version.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionSnapshotDetailViewDeleteTestCase.test_delete_returns_success_response`

### 汇总应用版本差异

- Capability ID: `console.app-version.diff-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service._summarize_diff`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceDiffSummaryTestCase.test_summarize_diff_keeps_real_component_changes`

### 清理应用版本隐藏模板记录

- Capability ID: `console.app-version.hidden-template-cleanup`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.market_app.market_app_service.delete_rainbond_app_all_info_by_id`
- 代码路径: `console/services/market_app/market_app.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionTemplateDeleteTestCase.test_delete_rainbond_app_all_info_by_id_cleans_snapshot_relation`

### 创建应用版本隐藏模板

- Capability ID: `console.app-version.hidden-template-create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.get_or_create_hidden_template`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceHiddenTemplateTestCase`

### 查看应用版本概览

- Capability ID: `console.app-version.overview`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.get_overview`
- 代码路径: `console/services/app_version_service.py`, `console/views/app_version.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceOverviewTestCase.test_get_overview_promotes_latest_successful_rollback_target_to_current_version`, `console/tests/app_version_test.py::AppVersionServiceOverviewTestCase.test_get_overview_keeps_latest_snapshot_as_current_version_when_newer_than_rollback`, `console/tests/app_version_test.py::AppVersionServiceOverviewTestCase.test_get_overview_promotes_partial_rollback_target_to_current_version`, `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_version_overview_returns_version_center_overview`

### 回滚后生成构建任务

- Capability ID: `console.app-version.restore-builds`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.market_app.market_app.MarketApp._generate_builds`
- 代码路径: `console/services/market_app/market_app.py`
- 测试路径: `console/tests/app_version_test.py::MarketAppBuildGenerationTestCase.test_generate_builds_allows_components_without_source_metadata`

### 无来源信息时恢复组件

- Capability ID: `console.app-version.restore-component-without-source`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.market_app.app_restore.AppRestore._create_component`
- 代码路径: `console/services/market_app/app_restore.py`
- 测试路径: `console/tests/app_version_test.py::AppRestoreSnapshotCompatibilityTestCase.test_create_component_allows_snapshot_without_service_source`

### 回滚时恢复组件 K8s 属性

- Capability ID: `console.app-version.restore-k8s-attributes`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.market_app.new_app.NewApp._save_components`
- 代码路径: `console/services/market_app/new_app.py`
- 测试路径: `console/tests/app_version_test.py::NewAppSaveComponentsTestCase.test_save_components_overwrites_k8s_attributes_for_new_components`

### 兼容旧快照中的操作类型

- Capability ID: `console.app-version.restore-legacy-action-type`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.AppVersionRollbackRestore._create_component`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRestoreActionTypeTestCase.test_create_component_keeps_snapshot_action_type_for_legacy_snapshot`

### 回滚时恢复组件来源信息

- Capability ID: `console.app-version.restore-update-service-sources`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.market_app.new_app.NewApp._update_components`
- 代码路径: `console/services/market_app/new_app.py`
- 测试路径: `console/tests/app_version_test.py::NewAppUpdateComponentsTestCase.test_update_components_overwrites_service_sources_when_snapshot_missing_source`

### 根据快照生成回滚目标应用

- Capability ID: `console.app-version.rollback-create-new-app`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.AppVersionRollbackRestore._create_new_app`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRestoreSnapshotCoverageTestCase.test_create_new_app_restores_snapshot_components_missing_from_runtime`, `console/tests/app_version_test.py::AppVersionRollbackRestoreSnapshotCoverageTestCase.test_create_new_app_marks_changed_existing_components_for_update`

### 生成回滚组件计划

- Capability ID: `console.app-version.rollback-plan`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service._build_rollback_component_plan`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceRollbackPlanTestCase.test_build_rollback_component_plan_marks_changed_and_restored_components`

### 查询应用版本回滚记录详情

- Capability ID: `console.app-version.rollback-record-detail`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_version.AppVersionRollbackRecordDetailView.get`
- 代码路径: `console/views/app_version.py`, `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRecordViewTestCase.test_detail_returns_single_rollback_record`

### 删除已完成的回滚记录

- Capability ID: `console.app-version.rollback-record-finished-delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.delete_rollback_record`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRecordServiceTestCase.test_delete_rollback_record_removes_finished_record`

### 阻止删除进行中的回滚记录

- Capability ID: `console.app-version.rollback-record-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.delete_rollback_record`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRecordServiceTestCase.test_delete_rollback_record_rejects_unfinished_record`

### 查询应用版本回滚记录列表

- Capability ID: `console.app-version.rollback-record-list`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_version.AppVersionRollbackRecordListView.get`
- 代码路径: `console/views/app_version.py`, `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRecordViewTestCase.test_list_returns_rollback_records`

### 查询应用版本回滚记录

- Capability ID: `console.app-version.rollback-record-query`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.list_rollback_records`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRecordServiceTestCase.test_list_rollback_records_filters_app_version_records`

### 查询前同步进行中的回滚记录

- Capability ID: `console.app-version.rollback-record-sync`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.get_rollback_record`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRecordServiceTestCase.test_get_rollback_record_detail_syncs_unfinished_record`

### 回滚记录缺失时忽略状态更新

- Capability ID: `console.app-version.rollback-record-update-ignore-missing`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.market_app.app_restore.AppRestore._update_rollback_record`
- 代码路径: `console/services/market_app/app_restore.py`
- 测试路径: `console/tests/app_version_test.py::AppRestoreRollbackRecordTestCase.test_update_rollback_record_ignores_missing_record`

### 应用版本回滚时恢复缺失组件

- Capability ID: `console.app-version.rollback-restore-components`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.AppVersionRollbackRestore._create_new_app`
- 代码路径: `console/services/app_version_service.py`, `console/services/market_app/app_restore.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionRollbackRestoreSnapshotCoverageTestCase`

### App Version Rollback Snapshot

- Capability ID: `console.app-version.rollback-snapshot`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-version.rollback-snapshot]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_rollback_app_version_snapshot_returns_rollback_record`

### 禁止回滚虚拟机应用版本快照

- Capability ID: `console.app-version.rollback-vm-snapshot-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_version_service.AppVersionService.rollback_snapshot`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceRollbackVMSnapshotGuardTestCase`

### 阻止删除最新应用版本快照

- Capability ID: `console.app-version.snapshot-delete-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.delete_snapshot`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceDeleteSnapshotTestCase.test_delete_snapshot_rejects_latest_version`

### 删除历史应用版本快照

- Capability ID: `console.app-version.snapshot-delete-history`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.delete_snapshot`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceDeleteSnapshotTestCase.test_delete_snapshot_removes_historical_version`

### 查看应用版本快照详情

- Capability ID: `console.app-version.snapshot-detail`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service.get_snapshot_detail`
- 代码路径: `console/services/app_version_service.py`, `console/views/app_version.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceSnapshotDetailTestCase.test_get_snapshot_detail_includes_previous_version_and_field_diff`

### 无变更时跳过创建快照

- Capability ID: `console.app-version.snapshot-no-change`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_version.AppVersionSnapshotListView.post`
- 代码路径: `console/views/app_version.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionSnapshotListViewPostTestCase.test_post_returns_no_change_message_when_snapshot_not_created`

### App Version Snapshot Share Image Fallback

- Capability ID: `console.app-version.snapshot-share-image-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_version_service`
- 代码路径: `console/services/app_version_service.py`, `console/views/app_version.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceTemplateNormalizationTestCase.test_assemble_app_template_falls_back_to_image_when_share_image_missing`

### App Version Snapshots

- Capability ID: `console.app-version.snapshots`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app-version.snapshots]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_list_app_version_snapshots_returns_versions`

### create_app_from_snapshot_version 工具暴露目标应用名约束

- Capability ID: `console.app-version.target-app-name-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.list_tools[console.app-version.target-app-name-schema]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_create_app_from_snapshot_version_tool_exposes_target_app_name_constraints`

### 查看应用版本差异详情

- Capability ID: `console.app-version.view-diff`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_version_service._build_component_diff_details`
- 代码路径: `console/services/app_version_service.py`
- 测试路径: `console/tests/app_version_test.py::AppVersionServiceDiffSummaryTestCase`, `console/tests/app_version_test.py::AppVersionServiceComponentDiffDetailTestCase`

### 批量操作应用组件

- Capability ID: `console.app.batch-component-operation`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_operate_app]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_operate_app_calls_batch_operations`

### 校验 YAML 创建应用

- Capability ID: `console.app.check-yaml`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_check_yaml_app]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/compose_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_check_yaml_app_returns_compose_check_info`

### 关闭团队下所有组件

- Capability ID: `console.app.close-all`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_close_apps]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_close_apps_calls_batch_action`

### 复制应用组件到目标应用

- Capability ID: `console.app.copy`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_copy_app]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_copy_app_returns_target_app_and_gateway_rules`

### 获取应用复制信息

- Capability ID: `console.app.copy-info`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_copy_app_info]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/groupcopy_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_copy_app_info_returns_services`

### 应用复制时拦截无效的 services 参数

- Capability ID: `console.app.copy-services-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.copy_app`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_copy_app_rejects_non_list_services`

### 创建应用

- Capability ID: `console.app.create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_create_app]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/group_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_calls_group_service`

### 从 YAML 创建应用

- Capability ID: `console.app.create-from-yaml`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_create_app_from_yaml]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/compose_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_from_yaml_creates_compose_record`

### App Create K8s Name Duplicate

- Capability ID: `console.app.create-k8s-name-duplicate`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app.create-k8s-name-duplicate]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_exposes_structured_k8s_app_duplicate_error`

### 删除应用及隐藏快照模板

- Capability ID: `console.app.delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.group_service._delete_app`
- 代码路径: `console/services/group_service.py`, `console/services/app_version_service.py`
- 测试路径: `console/tests/group_service_test.py::GroupServiceDeleteAppTestCase`

### 阻止无效的应用删除确认

- Capability ID: `console.app.delete-confirmation-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_delete_app]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceDeleteAppTests.test_delete_app_rejects_invalid_confirmation_token`

### 确认后删除应用

- Capability ID: `console.app.delete-with-confirmation`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_delete_app]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/group_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceDeleteAppTests.test_delete_app_requires_confirmation_then_delete`

### 查看应用详情

- Capability ID: `console.app.detail`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_app_detail]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_app_detail_returns_status_and_counts`

### 生成应用导出元数据

- Capability ID: `console.app.export-metadata`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_import_and_export_service.AppExportService._AppExportService__get_app_metata`
- 代码路径: `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/app_import_and_export_service_test.py::AppExportServiceMetadataTestCase`

### 查看 YAML 应用校验结果

- Capability ID: `console.app.get-yaml-check-result`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_yaml_app_check_result]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/compose_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_yaml_app_check_result_returns_services`

### 从市场安装应用

- Capability ID: `console.app.install-from-market`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_install_app_by_market]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/market_app_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_install_app_by_market_calls_market_service`

### 查询团队应用列表

- Capability ID: `console.app.list-team-apps`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_team_apps]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/group_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_team_apps_returns_app_list`

### 查询应用监控区间数据

- Capability ID: `console.app.monitor-range`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_query_app_monitor_range]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_monitor_range_returns_stringified_series`

### 监控区间查询默认步长为 60 秒

- Capability ID: `console.app.monitor-range-default-step`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.query_app_monitor_range`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_monitor_range_defaults_step_to_60`

### 查询应用监控概览

- Capability ID: `console.app.monitor-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_query_app_monitor]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_monitor_returns_monitor_items`

### 应用监控概览仅统计对外端口组件

- Capability ID: `console.app.monitor-summary-outer-only`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.query_app_monitor`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_monitor_filters_to_outer_services_when_requested`

### operate_app 重启映射到批量操作

- Capability ID: `console.app.restart-component-operation`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.app.restart-component-operation]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_operate_app_restart_calls_batch_action`

### 升级应用版本

- Capability ID: `console.app.upgrade`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_upgrade_app]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/upgrade_services.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_upgrade_app_calls_upgrade_service_and_returns_latest_items`

### 解析会话用户时不访问已废弃的 MIDDLEWARE_CLASSES

- Capability ID: `console.auth.get-user-no-legacy-middleware`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.auth.get_user`
- 代码路径: `console/services/auth/__init__.py`
- 测试路径: `console/tests/auth_get_user_test.py::GetUserNoLegacyMiddlewareTests.test_returns_user_without_touching_middleware_classes`, `console/tests/auth_get_user_test.py::GetUserNoLegacyMiddlewareTests.test_returns_anonymous_user_when_no_session`

### 内存缓存达到容量上限时拒绝或复用缓存槽位

- Capability ID: `console.cache.capacity-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache._memory_set`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_memory_cache_refuses_new_key_when_full_without_expired_entries`

### 在访问时清理已过期的内存缓存项

- Capability ID: `console.cache.expired-eviction`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache._memory_get`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_memory_cache_evicts_expired_entry_on_get`

### 返回清理过期缓存时移除的条目数量

- Capability ID: `console.cache.expired-eviction-count`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache._remove_expired_key`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_remove_expired_key_returns_removed_count`

### 在内存模式下于过期前返回缓存值

- Capability ID: `console.cache.memory-store-and-expire`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache.get`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_memory_cache_returns_value_before_expiration`

### 启用 redis 时将缓存读写委托给 redis 后端

- Capability ID: `console.cache.redis-backend-read-write`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache.get`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_cache_delegates_get_and_set_to_redis_backend`

### 根据环境配置初始化 redis 缓存客户端

- Capability ID: `console.cache.redis-client-config`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache.__init__`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_cache_initializes_redis_client_from_env`

### 在存在 REDIS_HOST 时启用 redis 缓存模式

- Capability ID: `console.cache.redis-enabled-flag`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache.enable_redis`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_enable_redis_follows_env`

### 吞掉 redis 读取异常并回落为空结果

- Capability ID: `console.cache.redis-read-error`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache._redis_get`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_redis_get_swallow_exception`

### 吞掉 redis 写入异常且不打断调用方

- Capability ID: `console.cache.redis-write-error`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache._redis_set`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_redis_set_swallow_exception`

### 即使内存缓存已满也允许更新已有缓存项

- Capability ID: `console.cache.update-existing-at-capacity`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cache.Cache._memory_set`
- 代码路径: `console/utils/cache.py`
- 测试路径: `console/tests/utils/cache_test.py::CacheMemoryTests.test_memory_cache_updates_existing_key_when_full`

### 在证书有效性检查中拒绝已过期证书

- Capability ID: `console.cert.expired-reject`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.certutil.cert_is_effective`
- 代码路径: `console/utils/certutil.py`
- 测试路径: `console/tests/utils/certutil_test.py::CertUtilTests.test_cert_is_effective_rejects_expired_cert`

### 在证书校验中拒绝无效私钥

- Capability ID: `console.cert.invalid-private-key`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.certutil.cert_is_effective`
- 代码路径: `console/utils/certutil.py`
- 测试路径: `console/tests/utils/certutil_test.py::CertUtilTests.test_cert_is_effective_rejects_invalid_private_key`

### 校验证书与私钥是否匹配且有效

- Capability ID: `console.cert.key-match`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.certutil.cert_is_effective`
- 代码路径: `console/utils/certutil.py`
- 测试路径: `console/tests/utils/certutil_test.py::CertUtilTests.test_cert_is_effective`

### 从扩展字符串中解析证书的 SAN 域名与 IP

- Capability ID: `console.cert.san-parse`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.certutil.parse_subject_alt_names`
- 代码路径: `console/utils/certutil.py`
- 测试路径: `console/tests/utils/certutil_test.py::CertUtilTests.test_parse_subject_alt_names`

### 汇总证书 SAN、签发方与过期信息

- Capability ID: `console.cert.summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.certutil.analyze_cert`
- 代码路径: `console/utils/certutil.py`
- 测试路径: `console/tests/utils/certutil_test.py::CertUtilTests.test_analyze_cert`

### 将证书 UTC 时间戳转换为本地时间字符串

- Capability ID: `console.cert.utc-to-local`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.certutil.utc2local`
- 代码路径: `console/utils/certutil.py`
- 测试路径: `console/tests/utils/certutil_test.py::CertUtilTests.test_utc2local`

### 根据构建参数自动设置 CNB 构建类型

- Capability ID: `console.cnb-build.auto-set-build-type`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.has_cnb_build_params`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::BuildTypeAutoSetTestCase.test_auto_set_build_type_cnb_for_node_language`

### 识别 CNB 构建参数

- Capability ID: `console.cnb-build.detect-build-params`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.has_cnb_build_params`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::CNBParamsDetectionTestCase.test_node_language_detects_cnb_params`, `console/tests/cnb_build_test.py::CNBParamsDetectionTestCase.test_non_cnb_language_ignores_stale_cnb_params`, `console/tests/cnb_build_test.py::CNBParamsDetectionTestCase.test_empty_build_env_dict_has_no_cnb_params`, `console/tests/cnb_build_test.py::CNBParamsDetectionTestCase.test_each_supported_cnb_param_is_detected_for_node_language`

### 识别支持 CNB 的构建语言

- Capability ID: `console.cnb-build.detect-supported-language`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.is_cnb_language`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::CNBLanguageDetectionTestCase.test_nodejs_language_is_cnb`, `console/tests/cnb_build_test.py::CNBLanguageDetectionTestCase.test_static_language_is_cnb`

### 生成框架输出目录约定

- Capability ID: `console.cnb-build.framework-output-contract`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.extract_cnb_envs_from_runtime_info`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_extract_known_framework_output_dir_examples`

### 根据运行时识别结果生成 CNB 环境变量

- Capability ID: `console.cnb-build.generate-runtime-envs`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.extract_cnb_envs_from_runtime_info`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_extract_nodejs_cnb_envs_from_runtime_info`, `console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_extract_static_framework_contract`

### 忽略不支持语言的 CNB 运行时信息

- Capability ID: `console.cnb-build.ignore-unsupported-runtime-info`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.extract_cnb_envs_from_runtime_info`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_java_runtime_info_does_not_generate_cnb_envs`, `console/tests/cnb_build_test.py::RuntimeInfoExtractTestCase.test_static_runtime_info_without_framework_has_no_extra_cnb_envs`

### 对不支持语言不自动设置 CNB 构建类型

- Capability ID: `console.cnb-build.keep-non-cnb-build-type`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.has_cnb_build_params`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::BuildTypeAutoSetTestCase.test_do_not_auto_set_build_type_for_java_language`

### 保留支持语言的 CNB 环境变量

- Capability ID: `console.cnb-build.preserve-supported-envs`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.sanitize_build_env_dict_for_language`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_node_build_envs_preserve_cnb_markers`, `console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_static_build_envs_preserve_cnb_markers`, `console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_node_build_envs_preserve_common_mirror_fields`, `console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_node_build_envs_preserve_known_node_versions`

### 拒绝不支持 CNB 的构建语言

- Capability ID: `console.cnb-build.reject-unsupported-language`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.is_cnb_language`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::CNBLanguageDetectionTestCase.test_java_language_is_not_cnb`, `console/tests/cnb_build_test.py::CNBLanguageDetectionTestCase.test_dockerfile_node_language_is_not_cnb`

### 清理非支持语言中的陈旧 CNB 环境变量

- Capability ID: `console.cnb-build.sanitize-unsupported-envs`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.cnb_build.sanitize_build_env_dict_for_language`
- 代码路径: `console/utils/cnb_build.py`
- 测试路径: `console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_java_build_envs_strip_stale_cnb_markers`, `console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_java_build_envs_strip_runtime_aliases_used_by_builder`, `console/tests/cnb_build_test.py::BuildEnvSanitizeTestCase.test_non_cnb_languages_strip_stale_cnb_markers`

### DaemonSet 组件类型支持

- Capability ID: `console.component-type.daemonset`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.enum.component_enum.ComponentType`
- 代码路径: `console/enum/component_enum.py`, `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/app_manage_test.py::ComponentDaemonSetSupportTests.test_daemonset_component_type_is_supported`, `console/tests/app_manage_test.py::ComponentDaemonSetSupportTests.test_extend_method_name_supports_daemonset`, `console/tests/app_manage_test.py::ComponentDaemonSetSupportTests.test_change_service_type_blocks_daemonset_transition`

### manage_component_autoscaler 在调用服务前拒绝不完整指标

- Capability ID: `console.component.autoscaler-invalid-metrics`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.autoscaler-invalid-metrics]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_autoscaler_create_rejects_incomplete_metric_before_service_call`

### 查看组件伸缩概览

- Capability ID: `console.component.autoscaler-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_autoscaler]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/autoscaler_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_autoscaler_summary_returns_rules_and_records`

### 检测成功后构建组件

- Capability ID: `console.component.build`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_build_component]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_build_component_builds_checked_component`

### Component Build Component Schema

- Capability ID: `console.component.build-component-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.build-component-schema]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_build_component_tool_schema_exposes_build_info_guidance`

### Component Build Env Preserve Source Build State

- Capability ID: `console.component.build-env-preserve-source-build-state`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.build-env-preserve-source-build-state]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_replace_build_envs_preserves_source_build_state`

### Component Build Logs

- Capability ID: `console.component.build-logs`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.build-logs]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_build_logs_returns_event_log_items`

### Component Build Source Get

- Capability ID: `console.component.build-source-get`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.build-source-get]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_build_source_returns_sanitized_summary`

### Component Build Source Update

- Capability ID: `console.component.build-source-update`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.build-source-update]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_build_source_updates_source_code_fields`

### 构建源更新保留/设置镜像启动命令

- Capability ID: `console.component.build-source-update-image-cmd`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.build-source-update-image-cmd]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_build_source_keeps_cmd_when_omitted_on_image_update`, `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_build_source_sets_cmd_and_syncs_docker_cmd`

### 修改组件镜像

- Capability ID: `console.component.change-image`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_change_component_image]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_change_component_image_updates_service_fields`

### 获取组件构建检测结果

- Capability ID: `console.component.check-result`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_component_check_result]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_check_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_check_result_saves_detection_result`

### 启动组件检测

- Capability ID: `console.component.check-start`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_check_component]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_check_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_check_component_starts_check_flow`

### 创建组件连接环境变量

- Capability ID: `console.component.connection-env-create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_connection_envs#create]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/env_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_connection_envs_create_uses_outer_scope`

### 查看组件连接环境变量

- Capability ID: `console.component.connection-env-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_connection_envs#summary]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/env_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_connection_envs_summary_returns_outer_envs`

### 从镜像创建组件

- Capability ID: `console.component.create-from-image`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_create_component]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_calls_console_services`

### 通过镜像入口创建组件

- Capability ID: `console.component.create-from-image-direct`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_component_from_image`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_image_uses_existing_image_flow`

### 从制品包创建组件

- Capability ID: `console.component.create-from-package`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_component_service.auto_create_component`
- 代码路径: `console/services/package_component_service.py`
- 测试路径: `console/tests/package_component_service_test.py::PackageComponentServiceTests`

### 通过上传制品包创建组件

- Capability ID: `console.component.create-from-package-upload`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_component_from_package`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_package_calls_aggregated_package_service`

### 从源码创建组件

- Capability ID: `console.component.create-from-source`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.auto_create_component`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests`

### 通过通用 Git 源码创建组件

- Capability ID: `console.component.create-from-source-generic-git`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_component_from_source`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_source_allows_generic_git_code_from`

### 通过引导式源码配置创建组件

- Capability ID: `console.component.create-from-source-guided`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_component_from_source`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_source_calls_aggregated_source_service`

### Component Create From Source Prefer Dockerfile

- Capability ID: `console.component.create-from-source-prefer-dockerfile`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.create-from-source-prefer-dockerfile]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_source_passes_prefer_dockerfile_flag`

### 组件创建工具暴露默认资源规格指引

- Capability ID: `console.component.default-resource-spec`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.list_tools[console.component.default-resource-spec]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_component_creation_tools_expose_default_resource_guidance`

### 删除组件

- Capability ID: `console.component.delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_delete_component]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_delete_component_calls_app_manage_delete`

### 删除组件返回结构化依赖冲突原因

- Capability ID: `console.component.delete-dependency-conflict`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_delete_component#conflict]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/mcp_query_error_contract_test.py::MCPComponentContextErrorTests.test_delete_component_dependency_conflict_returns_structured_reason`, `console/tests/mcp_query_error_contract_test.py::MCPComponentContextErrorTests.test_delete_component_running_conflict_is_non_retryable`

### 添加组件依赖

- Capability ID: `console.component.dependency-add`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency#add]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/app_relation_service.py`
- 测试路径: `console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_add_single_dependency_success`, `console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_add_single_dependency_requires_open_inner`

### 批量添加组件依赖

- Capability ID: `console.component.dependency-add-batch`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency#add-batch]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/app_relation_service.py`
- 测试路径: `console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_add_batch_dependencies_success`

### 添加反向组件依赖

- Capability ID: `console.component.dependency-add-reverse`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency#add_reverse]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/app_relation_service.py`
- 测试路径: `console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_add_reverse_dependencies_success`

### 删除组件依赖

- Capability ID: `console.component.dependency-delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency#delete]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/app_relation_service.py`
- 测试路径: `console/tests/mcp_query_dependency_ops_test.py::MCPQueryDependencyOpsTests.test_delete_dependency_success`

### 查看组件依赖概览

- Capability ID: `console.component.dependency-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_dependency]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/app_relation_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_dependency_summary_returns_dependency_snapshot`

### 查询组件详情

- Capability ID: `console.component.detail`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_component_detail]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_detail_returns_status_and_access_infos`

### 批量保存组件环境变量时拦截无效参数

- Capability ID: `console.component.env-batch-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.update_component_envs`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_envs_rejects_invalid_payload`

### 批量保存组件环境变量

- Capability ID: `console.component.env-batch-save`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.update_component_envs`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_update_component_envs_calls_env_service`

### 创建组件环境变量

- Capability ID: `console.component.env-create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_envs#create]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/env_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_create_defaults_scope_to_inner`

### 将环境变量作用域默认归一为内网

- Capability ID: `console.component.env-scope-default`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service._normalize_env_scope`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_normalize_env_scope_defaults_to_inner`

### 查看组件环境变量概览

- Capability ID: `console.component.env-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_envs]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/env_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_summary_returns_env_snapshots`

### 批量更新组件环境变量

- Capability ID: `console.component.env-update`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_envs#upsert]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/env_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_upsert_only_uses_inner_envs`

### Component Env Upsert Single Item

- Capability ID: `console.component.env-upsert-single-item`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.env-upsert-single-item]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_envs_upsert_accepts_single_item_shape`

### 查询组件事件

- Capability ID: `console.component.events`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_component_events]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_actions/app_log.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_events_returns_paginated_events`

### 按组件版本覆盖保存伸缩规则配置

- Capability ID: `console.component.extend-method-upsert`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.repositories.app_config.ServiceExtendRepository`
- 代码路径: `console/repositories/app_config.py`
- 测试路径: `console/tests/app_config_test.py::ServiceExtendRepositoryTests.test_create_extend_method_replaces_existing_version_record`, `console/tests/app_config_test.py::ServiceExtendRepositoryTests.test_get_extend_method_by_service_uses_latest_record`, `console/tests/app_config_test.py::ServiceExtendRepositoryTests.test_bulk_create_or_update_replaces_existing_version_records_by_business_key`

### 水平伸缩组件

- Capability ID: `console.component.horizontal-scale`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_horizontal_scale_component]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_horizontal_scale_component_calls_app_manage_service`

### 查看应用组件列表

- Capability ID: `console.component.list`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_query_components]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_components_uses_existing_service_repo_method`

### 查看组件日志

- Capability ID: `console.component.logs`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_component_logs]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_returns_component_logs`

### 兼容控制台风格实例结构读取日志

- Capability ID: `console.component.logs-console-shape`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.get_component_logs console pod shape fallback`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_service_supports_console_style_pod_shape`

### 按指定容器读取组件日志

- Capability ID: `console.component.logs-container`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.get_component_logs[action=container]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_returns_container_logs`

### 读取组件日志时自动回退到实例容器

- Capability ID: `console.component.logs-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.get_component_logs fallback selection`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_service_falls_back_to_first_pod_container`

### 无运行实例时拒绝查询组件日志

- Capability ID: `console.component.logs-no-instance`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.get_component_logs`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_logs_rejects_when_no_runtime_instance_found`

### 解析组件日志 SSE 数据

- Capability ID: `console.component.logs-parse-sse`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service._parse_component_log_line`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_parse_component_log_line_handles_sse_prefix`

### 规范化组件操作别名

- Capability ID: `console.component.operation-aliases`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service._normalize_component_operation`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_normalize_component_operation_aliases`

### Component Pods

- Capability ID: `console.component.pods`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.pods]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_pods_returns_normalized_runtime_instances`

### Component Port Add Invalid Alias

- Capability ID: `console.component.port-add-invalid-alias`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.port-add-invalid-alias]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_handle_component_ports_add_exposes_structured_alias_validation`

### manage_component_ports 批量新增委托给批量服务

- Capability ID: `console.component.port-batch-add`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.port-batch-add]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_batch_add_delegates_to_batch_service`

### manage_component_ports 批量开启内网端口只加载一次上下文

- Capability ID: `console.component.port-batch-enable-inner`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.port-batch-enable-inner]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_batch_enable_inner_loads_context_once`

### manage_component_ports 批量开启外网端口接受整数项

- Capability ID: `console.component.port-batch-enable-outer`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.component.port-batch-enable-outer]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_batch_enable_outer_accepts_integer_items`

### manage_component_ports 批量修改协议时归一化每一项

- Capability ID: `console.component.port-batch-protocol`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#update_protocol]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_batch_update_protocol_passes_each_normalized_protocol`

### 查询组件端口列表

- Capability ID: `console.component.port-list`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_handle_component_ports#list]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/port_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_handle_component_ports_list_returns_ports`

### 开放组件内网端口

- Capability ID: `console.component.port-open-inner`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#enable_inner]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_enable_inner_maps_to_open_inner`

### 仅开放组件公网端口

- Capability ID: `console.component.port-open-outer-only`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#enable_outer_only]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_enable_outer_only_maps_to_only_open_outer`

### 打开组件公网端口

- Capability ID: `console.component.port-open-public`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_handle_component_ports]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/port_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_handle_component_ports_alias_action_maps_to_standard_action`

### 归一化组件端口协议参数

- Capability ID: `console.component.port-protocol-normalize`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#update_protocol]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_update_protocol_normalizes_protocol`

### 调用服务前拦截非法组件端口协议

- Capability ID: `console.component.port-protocol-validation`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_ports#update_protocol]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_update_protocol_rejects_invalid_protocol_before_service_call`

### 查看组件端口概览

- Capability ID: `console.component.port-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_ports]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_ports_summary_delegates_to_port_handler`

### 记录组件端口开关事件

- Capability ID: `console.component.port-toggle-events`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.port_service.AppPortService.manage_port`
- 代码路径: `console/services/app_config/port_service.py`
- 测试路径: `console/tests/port_service_delete_test.py::PortServiceDeleteTests::test_open_outer_port_synchronizes_region_component_event`, `console/tests/port_service_delete_test.py::PortServiceDeleteTests::test_close_outer_port_synchronizes_region_component_event`, `console/tests/port_service_delete_test.py::PortServiceDeleteTests::test_inner_port_toggle_keeps_region_component_event_path`

### 查看组件探针概览

- Capability ID: `console.component.probe-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_probe]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/probe_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_probe_summary_returns_probe_snapshot`

### 创建组件共享存储挂载

- Capability ID: `console.component.storage-create-mount`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#create_mnt]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/mnt_service.py`
- 测试路径: `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_create_mnt_batches_mounts`

### 创建组件存储卷

- Capability ID: `console.component.storage-create-volume`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#create_volume]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_create_volume_returns_created_and_volume`, `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_create_volume_rejects_collision_with_existing_config_file_path`

### 过滤组件自定义卷列表中的内置卷类型

- Capability ID: `console.component.storage-custom-volume-filter`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.repositories.app_config.TenantServiceVolumnRepository.list_custom_volumes`
- 代码路径: `console/repositories/app_config.py`
- 测试路径: `console/tests/app_config_test.py::TenantServiceVolumnRepositoryTests.test_list_custom_volumes_treats_local_path_as_builtin_volume_type`

### 删除组件共享存储挂载

- Capability ID: `console.component.storage-delete-mount`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#delete_mnt]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/mnt_service.py`
- 测试路径: `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_delete_mnt_removes_relation`

### 删除组件存储卷

- Capability ID: `console.component.storage-delete-volume`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#delete_volume]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_delete_volume_requires_force_branch`, `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_delete_volume_success_branch`

### 查看组件存储概览

- Capability ID: `console.component.storage-summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_storage]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/volume_service.py`, `console/services/app_config/mnt_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_manage_component_storage_summary_returns_storage_snapshot`, `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_summary_includes_config_file_volumes`

### 拒绝操作其他组件的存储卷

- Capability ID: `console.component.storage-target-scope`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#update_volume]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_update_volume_rejects_volume_id_from_another_component`

### Component Storage Update Capacity

- Capability ID: `console.component.storage-update-capacity`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_config.app_volume.AppVolumeManageView.put`
- 代码路径: `console/views/app_config/app_volume.py`
- 测试路径: `console/tests/app_volume_view_test.py::AppVolumeManageViewTestCase.test_put_allows_updating_volume_capacity_without_path_change`

### 按当前路径更新组件存储卷

- Capability ID: `console.component.storage-update-volume`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_storage#update_volume]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_update_volume_can_resolve_target_by_current_volume_path`

### Component Storage Update Volume Capacity

- Capability ID: `console.component.storage-update-volume-capacity`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_manage_component_storage]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/mcp_query_storage_ops_test.py::ManageComponentStorageTests.test_update_volume_allows_capacity_change_without_path_change`

### 查看组件概览

- Capability ID: `console.component.summary`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_component_summary]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_component_summary_returns_aggregated_info`

### 被共享挂载时阻止删除组件存储卷

- Capability ID: `console.component.volume-delete-blocks-shared-mount`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.volume_service.AppVolumeService.delete_service_volume_by_id`
- 代码路径: `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/app_config_volume_delete_test.py::AppVolumeDeleteTests.test_delete_service_volume_rejects_shared_mount_even_when_forced`

### Dependency Invalid Container Port

- Capability ID: `console.dependency.invalid-container-port`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.app_relation_service.AppServiceRelationService`
- 代码路径: `console/services/app_config/app_relation_service.py`
- 测试路径: `console/tests/app_relation_service_test.py::AppRelationServiceTests.test_add_service_dependency_rejects_unknown_dep_service_port`

### 源码构建源检测失败诊断埋点

- Capability ID: `console.deploy-diagnostics.source-check`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.app_create.app_check.AppCheck.get`
- 代码路径: `console/views/app_create/app_check.py`, `console/services/source_component_service.py`, `console/services/enterprise_first_deploy_service.py`
- 测试路径: `console/tests/app_check_view_test.py::AppCheckSourceDiagnosticTests.test_get_reports_source_check_failure_without_changing_response`, `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_raises_on_check_failure`, `console/tests/enterprise_first_deploy_service_test.py::EnterpriseFirstDeployServiceTests.test_report_source_check_failure_sends_pre_deploy_diagnostic`

### 部署失败 v3 诊断埋点

- Capability ID: `console.deploy-diagnostics.v3`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.enterprise_first_deploy_service.EnterpriseFirstDeployService`
- 代码路径: `console/services/enterprise_first_deploy_service.py`, `console/repositories/first_deploy_repo.py`, `console/views/app_create/app_build.py`, `console/views/app_manage.py`, `console/services/market_app_service.py`, `console/services/platform_plugin_service.py`, `console/services/source_component_service.py`, `console/services/package_component_service.py`
- 测试路径: `console/tests/enterprise_first_deploy_service_test.py`, `console/tests/app_build_first_deploy_test.py::AppBuildFirstDeployTrackingTests.test_app_build_tracks_source_image_and_package_deploy_types`, `console/tests/market_app_first_deploy_test.py::MarketAppFirstDeployTrackingTests.test_install_app_reports_first_deploy_tracking_for_market_install`, `console/tests/compose_check_first_deploy_test.py`, `console/tests/compose_build_first_deploy_test.py::ComposeBuildFirstDeployTrackingTests.test_compose_build_tracks_first_deploy_and_binds_all_component_events`, `console/tests/auto_create_first_deploy_tracking_test.py`, `console/tests/platform_plugin_first_deploy_test.py::PlatformPluginFirstDeployTrackingTests.test_install_platform_plugin_reports_first_deploy_tracking`

### 拒绝既不是 IP 也不是域名的非法端点地址

- Capability ID: `console.endpoint-address.reject-invalid-format`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.validation.validate_endpoint_address`
- 代码路径: `console/utils/validation.py`
- 测试路径: `console/tests/utils/validation_test.py::EndpointValidationTests.test_validate_endpoint_address_rejects_invalid_format`

### 拒绝 unspecified 和 loopback 的端点地址

- Capability ID: `console.endpoint-address.reject-special-ranges`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.validation.validate_endpoint_address`
- 代码路径: `console/utils/validation.py`
- 测试路径: `console/tests/utils/validation_test.py::EndpointValidationTests.test_validate_endpoint_address_rejects_special_ranges`

### 在多端点校验前规范化协议和端口

- Capability ID: `console.endpoint-list.normalize-scheme-port`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.validation.validate_endpoints_info`
- 代码路径: `console/utils/validation.py`
- 测试路径: `console/tests/utils/validation_test.py::EndpointValidationTests.test_validate_endpoints_info_normalizes_scheme_and_port`

### 在多实例端点列表中拒绝重复地址

- Capability ID: `console.endpoint-list.reject-duplicate`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.validation.validate_endpoints_info`
- 代码路径: `console/utils/validation.py`
- 测试路径: `console/tests/utils/validation_test.py::EndpointValidationTests.test_validate_endpoints_info_rejects_duplicate_addresses`

### 处理企业配置并发初始化

- Capability ID: `console.enterprise-config.concurrent-initialization`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.config_service.ConfigService.add_config`
- 代码路径: `console/services/config_service.py`
- 测试路径: `console/tests/config_service_test.py::EnterpriseConfigServiceTests.test_add_config_returns_existing_record_when_concurrent_create_wins`

### get_custom_fields 包含被禁用的布尔字段

- Capability ID: `console.enterprise-config.custom-fields-disabled-bool`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.config_service.EnterpriseConfigService.get_custom_fields`
- 代码路径: `console/services/config_service.py`
- 测试路径: `console/tests/config_service_test.py::EnterpriseConfigServiceTests.test_get_custom_fields_includes_disabled_bool_fields`

### 解析企业配置服务用户上下文

- Capability ID: `console.enterprise-config.user-context`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.config_service.EnterpriseConfigService.__init__`
- 代码路径: `console/services/config_service.py`
- 测试路径: `console/tests/config_service_test.py::EnterpriseConfigServiceTests.test_enterprise_config_service_defaults_user_id_to_none`, `console/tests/config_service_test.py::EnterpriseConfigServiceTests.test_enterprise_config_service_keeps_explicit_user_id`

### 解码云市绑定企业的认证信息

- Capability ID: `console.enterprise.bind-market-token-decode`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.enterprise_active.BindMarketEnterpriseOptimizAccessTokenView.post`
- 代码路径: `console/views/enterprise_active.py`
- 测试路径: `console/tests/bind_market_token_decode_test.py::BindMarketTokenDecodeTest.test_market_info_is_base64_decoded`

### 查看集群控制面组件列表

- Capability ID: `console.enterprise.region-component-list`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_query_region_rbd_components]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_region_rbd_components_returns_components_for_enterprise_admin`

### 创建企业集群

- Capability ID: `console.enterprise.region-create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_create_region]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceRegionMutationTests.test_create_region_executes_directly`

### 集群仪表盘目标缺失时返回 404

- Capability ID: `console.enterprise.region-dashboard-not-found`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.enterprise.EnterpriseRegionDashboard.dispatch`
- 代码路径: `console/views/enterprise.py`
- 测试路径: `console/tests/enterprise_region_dashboard_notfound_test.py::EnterpriseRegionDashboardNotFoundTest.test_missing_region_returns_clean_404`

### 删除企业集群

- Capability ID: `console.enterprise.region-delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_delete_region]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceRegionMutationTests.test_delete_region_executes_directly`

### 查看企业集群详情

- Capability ID: `console.enterprise.region-detail`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_region_detail]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_returns_region_data`

### 按集群名称查看企业集群详情

- Capability ID: `console.enterprise.region-detail-by-name`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_region_detail]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_accepts_region_name`

### 不同集群 ID 无效时不跨字段回退

- Capability ID: `console.enterprise.region-detail-no-cross-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_region_detail]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_does_not_override_distinct_bad_region_id`

### 集群详情支持从集群 ID 回退到名称查询

- Capability ID: `console.enterprise.region-detail-region-name-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_region_detail]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_treats_missing_region_id_as_region_name`

### 集群详情工具 schema 暴露集群名称参数

- Capability ID: `console.enterprise.region-detail-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service._tool_get_region_detail`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_detail_schema_accepts_region_name`

### 查看企业集群列表

- Capability ID: `console.enterprise.region-list`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_query_regions]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_requires_enterprise_admin`, `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_returns_paginated_regions_for_enterprise_admin`, `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_rejects_cross_enterprise_access_for_enterprise_admin`

### 校验企业集群列表访问权限

- Capability ID: `console.enterprise.region-list-authz`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.query_regions`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_requires_enterprise_admin`, `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_regions_rejects_cross_enterprise_access_for_enterprise_admin`

### 查看集群节点详情

- Capability ID: `console.enterprise.region-node-detail`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_get_region_node_detail]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_region_node_detail_returns_node_detail_for_enterprise_admin`

### 查看集群节点列表

- Capability ID: `console.enterprise.region-node-list`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_query_region_nodes]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_query_region_nodes_returns_nodes_for_enterprise_admin`

### 更新企业集群

- Capability ID: `console.enterprise.region-update`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_update_region]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceRegionMutationTests.test_update_region_executes_directly_with_merged_full_payload`

### 文件管理区域请求使用选定容器与更长超时

- Capability ID: `console.file-manage.region-request-timeout`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `www.apiclient.regionapi.RegionInvokeApi.get_files`
- 代码路径: `www/apiclient/regionapi.py`
- 测试路径: `console/tests/file_manage_service_test.py::test_region_api_get_files_uses_container_name_and_longer_timeout`

### 列出文件管理内容时透传用户选择的容器名

- Capability ID: `console.file-manage.selected-container-forwarding`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.group_service.GroupService.get_file_and_dir`
- 代码路径: `console/services/group_service.py`, `console/views/app_overview.py`
- 测试路径: `console/tests/file_manage_service_test.py::test_get_file_and_dir_forwards_selected_container_name`

### Gateway Component Env Upsert Schema

- Capability ID: `console.gateway.component-env-upsert-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.gateway.component-env-upsert-schema]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_envs_schema_exposes_single_item_upsert_guidance`

### create_app 对非法应用名返回结构化错误详情

- Capability ID: `console.gateway.create-app-invalid-display-name`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.gateway.create-app-invalid-display-name]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_app_returns_structured_details_for_illegal_app_name`

### Gateway Create App K8s Name Schema

- Capability ID: `console.gateway.create-app-k8s-name-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.gateway.create-app-k8s-name-schema]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_create_app_tool_schema_exposes_k8s_app_constraints`

### 创建 HTTP 网关规则

- Capability ID: `console.gateway.create-http-rule`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_create_gateway_rules]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/domain_service.py`, `console/services/app_config/port_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_returns_bound_rule`

### 创建 TCP 网关规则

- Capability ID: `console.gateway.create-tcp-rule`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_create_gateway_rules]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/app_config/domain_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_tcp_returns_bound_rule`

### Gateway Dependency Container Port Schema

- Capability ID: `console.gateway.dependency-container-port-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.gateway.dependency-container-port-schema]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_dependency_schema_exposes_container_port_guidance`

### 对外端口未开启时拦截 HTTP 网关创建

- Capability ID: `console.gateway.http-port-not-open`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_gateway_rules[http]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_rejects_when_outer_port_is_unavailable`

### HTTP 网关开端口失败时拦截创建

- Capability ID: `console.gateway.http-port-open-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_gateway_rules[http]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_rejects_port_open_failure`

### 创建 HTTP 网关规则时必须提供 http 参数

- Capability ID: `console.gateway.http-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_gateway_rules[http]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_requires_http_payload`

### 拦截重复的 HTTP 网关规则

- Capability ID: `console.gateway.http-rule-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_gateway_rules[http]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_rejects_duplicate_rule`

### 第三方组件不支持 HTTP 网关策略时拦截创建

- Capability ID: `console.gateway.http-third-party-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_gateway_rules[http]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_http_rejects_invalid_third_party_component`

### 暴露组件端口管理操作枚举

- Capability ID: `console.gateway.operation-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service._tool_manage_component_ports`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_ports_tool_schema_exposes_operation_enum`

### 暴露组件端口操作枚举

- Capability ID: `console.gateway.port-action-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service._tool_handle_component_ports`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_handle_component_ports_tool_schema_exposes_action_enum`

### Gateway Port Constraints Schema

- Capability ID: `console.gateway.port-constraints-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.gateway.port-constraints-schema]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_ports_tool_schema_exposes_port_constraints`

### 暴露组件端口协议枚举

- Capability ID: `console.gateway.port-protocol-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service._tool_manage_component_ports`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_manage_component_ports_tool_schema_exposes_protocol_enum`

### 拦截不支持的网关协议

- Capability ID: `console.gateway.protocol-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_gateway_rules`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_rejects_invalid_protocol`

### Gateway Source Code From Schema

- Capability ID: `console.gateway.source-code-from-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.gateway.source-code-from-schema]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_create_component_from_source_schema_exposes_code_from_guidance`

### TCP 网关开端口失败时拦截创建

- Capability ID: `console.gateway.tcp-port-open-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_gateway_rules[tcp]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_tcp_rejects_port_open_failure`

### 创建 TCP 网关规则时必须提供 tcp 参数

- Capability ID: `console.gateway.tcp-required`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_gateway_rules[tcp]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_requires_tcp_payload`

### 第三方组件不支持 TCP 网关策略时拦截创建

- Capability ID: `console.gateway.tcp-third-party-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.create_gateway_rules[tcp]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_gateway_rules_tcp_rejects_invalid_third_party_component`

### Gray Release Update Route Query Params

- Capability ID: `console.gray-release.update-route-query-params`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.gray_release_service.GrayReleaseService.update_route`
- 代码路径: `console/services/gray_release_service.py`
- 测试路径: `console/tests/gray_release_service_test.py::GrayReleaseRouteUpdateTests.test_update_apisix_route_weights_keeps_service_alias_and_port_in_query`

### Gray Release Update Route Query Uses Original Port

- Capability ID: `console.gray-release.update-route-query-uses-original-port`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.gray_release_service.GrayReleaseService.update_route`
- 代码路径: `console/services/gray_release_service.py`
- 测试路径: `console/tests/gray_release_service_light_test.py::GrayReleaseRouteUpdateLightTests.test_update_route_query_uses_original_service_port_when_ports_differ`

### 上传软件包组件禁止快速复制

- Capability ID: `console.groupcopy.package-build-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.groupcopy_service.GroupAppCopyService.get_modify_group_metadata`
- 代码路径: `console/services/groupcopy_service.py`
- 测试路径: `console/tests/groupcopy_service_test.py::GroupAppCopyServiceTests.test_get_modify_group_metadata_rejects_package_build`

### 删除 Helm 发布并清理来源记录

- Capability ID: `console.helm-release.delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources.HelmReleaseDetailView.delete`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase`

### 查看 Helm 发布详情

- Capability ID: `console.helm-release.detail`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources.HelmReleaseDetailView.get`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_get_enriches_helm_release_detail_with_source_info`

### 查看 Helm 发布历史

- Capability ID: `console.helm-release.history`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources.HelmReleaseHistoryView.get`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_get_uses_team_namespace_for_helm_release_history`

### 安装 Helm 发布并保存来源记录

- Capability ID: `console.helm-release.install`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources.HelmReleasesView.post`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_persists_install_source_after_success`

### 查看 Helm 发布列表

- Capability ID: `console.helm-release.list`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources.HelmReleasesView.get`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_get_enriches_helm_release_list_with_source_info`

### 操作前解析 Helm 商店来源信息

- Capability ID: `console.helm-release.resolve-store-source`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.team_resources.Resolve store-backed helm source metadata`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_enriches_store_install_with_saved_repo_metadata`

### 回滚 Helm 发布

- Capability ID: `console.helm-release.rollback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources.HelmReleaseRollbackView.post`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_uses_team_namespace_for_helm_release_rollback`

### 追踪 Helm 发布来源信息

- Capability ID: `console.helm-release.source-tracking`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.team_resources.Helm release source persistence lifecycle`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_persists_install_source_after_success`, `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_put_persists_upgrade_source_after_success`, `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_delete_cleans_up_saved_install_source_after_success`

### 在团队命名空间内执行 Helm 操作

- Capability ID: `console.helm-release.team-namespace-ops`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.views.team_resources.Helm release lifecycle uses tenant namespace`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_uses_team_namespace_for_helm_install`, `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_delete_uses_team_namespace_for_helm_release_uninstall`, `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_put_uses_team_namespace_for_helm_release_upgrade`, `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_post_uses_team_namespace_for_helm_release_rollback`

### 升级 Helm 发布并保存来源记录

- Capability ID: `console.helm-release.upgrade`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources.HelmReleaseDetailView.put`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::HelmReleasesViewTestCase.test_put_persists_upgrade_source_after_success`

### 构建 Helm 应用模板

- Capability ID: `console.helm.build`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_build_helm_app]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/helm_app.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_build_helm_app_generates_template`

### 检查 Helm 应用

- Capability ID: `console.helm.check`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[rainbond_check_helm_app]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/helm_app.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_check_helm_app_returns_check_result`

### Helm DaemonSet 资源映射为组件模板

- Capability ID: `console.helm.daemonset-template`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.helm_app_yaml.HelmAppService.generate_template`
- 代码路径: `console/services/helm_app_yaml.py`
- 测试路径: `console/tests/app_manage_test.py::ComponentDaemonSetSupportTests.test_helm_template_maps_daemonset_resource_type`

### 解析 Harbor 镜像推送 Webhook

- Capability ID: `console.image-webhook.harbor-push-artifact`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.webhook.parse_image_webhook_payload`
- 代码路径: `console/views/webhook.py`
- 测试路径: `console/tests/webhook_test.py::ImageWebhookPayloadTestCase`

### Console 镜像 Python 3.6 websocket-client 兼容性

- Capability ID: `console.image.python36-websocket-client`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `other`
- 业务入口: `requirements.txt`
- 代码路径: `Dockerfile`, `requirements.txt`
- 测试路径: `console/tests/dependency_compat_test.py::ConsoleImageDependencyCompatibilityTests`

### 根据仓库前缀识别 runner 镜像

- Capability ID: `console.image.runner-detect`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.runner_util.is_runner`
- 代码路径: `console/utils/runner_util.py`
- 测试路径: `console/tests/utils/image_classify_test.py::ImageClassifyTests.test_is_runner`

### 为非 docker 类语言识别基于 runner 的 slug 镜像

- Capability ID: `console.image.slug-detect`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.slug_util.is_slug`
- 代码路径: `console/utils/slug_util.py`
- 测试路径: `console/tests/utils/image_classify_test.py::ImageClassifyTests.test_is_slug`

### 初始化时优先选择最新待处理集群

- Capability ID: `console.init-cluster.prefer-latest-pending`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.repositories.init_cluster.Cluster.get_rke_cluster_exclude_integrated`
- 代码路径: `console/repositories/init_cluster.py`
- 测试路径: `console/tests/init_cluster_test.py::ClusterRepositoryTests.test_get_rke_cluster_exclude_integrated_prefers_latest_pending_cluster`

### 回收空白联通集群用于重新初始化

- Capability ID: `console.init-cluster.recycle-empty-interconnected`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.repositories.init_cluster.Cluster.get_rke_cluster_exclude_integrated`
- 代码路径: `console/repositories/init_cluster.py`
- 测试路径: `console/tests/init_cluster_test.py::ClusterRepositoryTests.test_get_rke_cluster_exclude_integrated_recycles_blank_cluster`

### 将 cmd 和 args Kubernetes 属性规范化为 YAML 数组

- Capability ID: `console.k8s-attribute.cmd-args-yaml`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.k8s_attribute.ComponentK8sAttributeService.create_k8s_attribute`
- 代码路径: `console/services/k8s_attribute.py`
- 测试路径: `console/tests/k8s_attribute_service_test.py::ComponentK8sAttributeServiceTests`

### Console 与 region 组件 K8s 属性幂等同步

- Capability ID: `console.k8s-attribute.upsert-region-sync`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.k8s_attribute.ComponentK8sAttributeService`
- 代码路径: `console/services/k8s_attribute.py`
- 测试路径: `console/tests/k8s_attribute_service_test.py`

### 将用户名规范化为合法的 Kubernetes 命名空间名

- Capability ID: `console.k8s-namespace.normalize-user-prefix`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.validation.normalize_name_for_k8s_namespace`
- 代码路径: `console/utils/validation.py`
- 测试路径: `console/tests/utils/validation_test.py::NamespaceNormalizationTests.test_normalize_name_for_k8s_namespace`

### KubeBlocks 集群请求携带 app id 以支持资源统计

- Capability ID: `console.kubeblocks.app-resource-statistics`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.kubeblocks_service.KubeBlocksService._build_cluster_request`
- 代码路径: `console/services/kubeblocks_service.py`
- 测试路径: `console/tests/kubeblocks_cluster_validation_test.py::KubeBlocksCreateFlowTests.test_build_cluster_request_includes_app_id_for_resource_statistics`

### 使用 KubeBlocks 备份仓库前校验就绪状态

- Capability ID: `console.kubeblocks.backup-repo.ready-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.kubeblocks_service.KubeBlocksService.ensure_backup_repo_ready_for_use`
- 代码路径: `console/services/kubeblocks_service.py`
- 测试路径: `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_ensure_backup_repo_ready_for_use_rejects_prechecking_repo`, `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_ensure_backup_repo_ready_for_use_accepts_ready_repo`, `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_ensure_backup_repo_ready_for_use_rejects_missing_live_repo`, `console/tests/kubeblocks_cluster_validation_test.py::KubeBlocksCreateFlowTests.test_create_cluster_returns_backup_repo_not_ready_message`

### 创建团队 KubeBlocks 备份仓库

- Capability ID: `console.kubeblocks.backup-repo.team-create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.kubeblocks_service.KubeBlocksService.create_backup_repo`
- 代码路径: `console/services/kubeblocks_service.py`
- 测试路径: `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_create_backup_repo_prefixes_namespace_and_does_not_store_secret_values`, `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_create_backup_repo_defaults_to_prechecking_when_region_phase_is_empty`, `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_create_backup_repo_rejects_existing_region_repo_name_even_if_deleted`

### 删除团队 KubeBlocks 备份仓库

- Capability ID: `console.kubeblocks.backup-repo.team-delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.kubeblocks_service.KubeBlocksService.delete_backup_repo`
- 代码路径: `console/services/kubeblocks_service.py`
- 测试路径: `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_delete_backup_repo_shows_clear_message_when_in_use`

### 列出团队 KubeBlocks 备份仓库并合并实时状态

- Capability ID: `console.kubeblocks.backup-repo.team-list`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.kubeblocks_service.KubeBlocksService.get_team_backup_repos`
- 代码路径: `console/services/kubeblocks_service.py`
- 测试路径: `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_list_backup_repos_merges_live_status_from_region`, `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_list_backup_repos_keeps_failed_live_status`, `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_list_backup_repos_marks_missing_when_region_resource_disappears`

### 校验 KubeBlocks 备份仓库团队归属

- Capability ID: `console.kubeblocks.backup-repo.team-ownership`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.kubeblocks_service.KubeBlocksService.ensure_backup_repo_belongs_to_team`
- 代码路径: `console/services/kubeblocks_service.py`
- 测试路径: `console/tests/kubeblocks_backup_repo_test.py::KubeBlocksBackupRepoServiceTests.test_ensure_backup_repo_belongs_to_team_rejects_other_team_repo`

### 校验 KubeBlocks 集群资源请求

- Capability ID: `console.kubeblocks.cluster-resource-validation`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.kubeblocks_service.KubeBlocksService.validate_cluster_params`
- 代码路径: `console/services/kubeblocks_service.py`
- 测试路径: `console/tests/kubeblocks_cluster_validation_test.py::KubeBlocksClusterValidationTests`

### 创建 KubeBlocks 组件时同步连接凭据

- Capability ID: `console.kubeblocks.create-credential-sync`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.kubeblocks_service.KubeBlocksService.create_complete_kubeblocks_component`
- 代码路径: `console/services/kubeblocks_service.py`
- 测试路径: `console/tests/kubeblocks_cluster_validation_test.py::KubeBlocksCreateFlowTests`

### 代理旧版语言包上传接口

- Capability ID: `console.lang-version.proxy-upload`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.enterprise.UploadLongVersion.post`
- 代码路径: `console/views/enterprise.py`, `console/urls/__init__.py`
- 测试路径: `console/tests/lang_version_proxy_test.py::UploadLongVersionProxyViewTests`

### 默认控制台日志过滤调试噪音

- Capability ID: `console.logging.default-no-debug-noise`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `other`
- 业务入口: `goodrain_web.settings.LOGGING`
- 代码路径: `goodrain_web/settings.py`, `goodrain_web/log_formatter.py`
- 测试路径: `console/tests/logging_config_test.py::LoggingConfigTests.test_default_logger_level_defaults_to_info`, `console/tests/logging_config_test.py::LoggingConfigTests.test_ip_formatter_uses_record_level_name`

### 按发布范围和团队检查应用市场模板重名

- Capability ID: `console.market-app.create-template-scope-name`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.market_app_service.MarketAppService.create_rainbond_app`
- 代码路径: `console/services/market_app_service.py`
- 测试路径: `console/tests/market_app_service_test.py::MarketAppServiceCreateRainbondAppTests`

### 应用市场安装使用平台默认存储类

- Capability ID: `console.market-app.install-default-storage-class`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.market_app.new_components.NewComponents._template_to_volumes`
- 代码路径: `console/services/app_config/volume_service.py`, `console/services/market_app/new_components.py`, `console/services/market_app_service.py`
- 测试路径: `console/tests/market_app_storage_test.py::MarketAppDefaultStorageClassTests.test_resolve_market_default_volume_type_prefers_configured_storage_class`, `console/tests/market_app_storage_test.py::MarketAppDefaultStorageClassTests.test_template_to_volumes_uses_configured_default_storage_class`

### 市场发布和安装保留不限制资源

- Capability ID: `console.market-app.install-unlimited-resources`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.share_services.ShareService.query_share_service_info / console.services.market_app.new_components.NewComponents._template_to_component / console.services.market_app_service.MarketAppService.__init_component_from_market_app / console.services.app_import_and_export_service.AppImportService.__normalize_import_component_template`
- 代码路径: `console/services/share_services.py`, `console/services/market_app/new_components.py`, `console/services/market_app_service.py`, `console/services/app_import_and_export_service.py`
- 测试路径: `console/tests/service_share_test.py::ShareServiceQueryResourceLimitTestCase.test_query_share_service_info_preserves_unlimited_resource_limits`, `console/tests/market_app_update_components_test.py::MarketAppNewComponentsResourceLimitTests.test_template_to_component_preserves_explicit_unlimited_cpu_and_memory`, `console/tests/market_app_service_test.py::MarketAppServiceResourceLimitTests.test_init_component_from_market_app_preserves_explicit_unlimited_cpu_and_memory`, `console/tests/app_import_and_export_service_test.py::AppImportServiceMetadataTestCase.test_save_enterprise_import_info_preserves_explicit_unlimited_resources`

### 市场恢复在存储类型回退时保留卷容量

- Capability ID: `console.market-app.restore-preserves-volume-capacity-on-storage-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.market_app.new_components.NewComponents._template_to_volumes`
- 代码路径: `console/services/market_app/new_components.py`, `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/market_app_storage_test.py::MarketAppDefaultStorageClassTests.test_template_to_volumes_preserves_capacity_when_storage_type_changes`

### resolve_market_restore_volume_settings 在存储类型变化时保留容量

- Capability ID: `console.market-app.restore-volume-capacity-helper`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.volume_service.AppVolumeService.resolve_market_restore_volume_settings`
- 代码路径: `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/market_app_storage_test.py::MarketAppDefaultStorageClassTests.test_resolve_market_restore_volume_settings_preserves_capacity_when_storage_type_changes`

### Market App Upgrade Share Image Fallback

- Capability ID: `console.market-app.upgrade-share-image-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.market_app.update_components`
- 代码路径: `console/services/market_app/update_components.py`
- 测试路径: `console/tests/market_app_update_components_test.py::MarketAppUpdateComponentsCompatibilityTests.test_create_update_components_falls_back_to_image_when_share_image_missing`

### 市场应用安装从 VM 模板生成磁盘导入配置

- Capability ID: `console.market-app.vm-disk-imports-from-template`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.market_app.new_components.NewComponents._template_to_k8s_attributes`
- 代码路径: `console/services/market_app/new_components.py`
- 测试路径: `console/tests/market_app_update_components_test.py::MarketAppNewComponentsVMK8sAttrsTests.test_template_to_k8s_attributes_backfills_vm_runtime_attrs_from_vm_block`

### 虚拟机平台异常时禁止安装虚拟机模板

- Capability ID: `console.market-app.vm-runtime-status-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.market_app_service.MarketAppService.install_app`
- 代码路径: `console/services/market_app_service.py`, `console/services/app_version_service.py`
- 测试路径: `console/tests/market_app_service_test.py::MarketAppServiceVMGuardTests`

### 将 401 应用市场错误转换为缺少 token 的服务异常

- Capability ID: `console.market-client.auth-missing`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.restful_client.apiException`
- 代码路径: `console/utils/restful_client.py`
- 测试路径: `console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_401`

### 将通用 4xx 应用市场错误转换为参数错误响应

- Capability ID: `console.market-client.bad-request`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.restful_client.apiException`
- 代码路径: `console/utils/restful_client.py`
- 测试路径: `console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_generic_4xx`

### 使用默认回退 host 创建应用市场客户端

- Capability ID: `console.market-client.default-host`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.restful_client.get_market_client`
- 代码路径: `console/utils/restful_client.py`
- 测试路径: `console/tests/utils/restful_client_test.py::RestfulClientFactoryTests.test_get_market_client_uses_default_host`

### 将应用市场客户端反序列化失败转换为服务异常

- Capability ID: `console.market-client.deserialize-error`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.restful_client.apiException`
- 代码路径: `console/utils/restful_client.py`
- 测试路径: `console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_value_error`

### 使用显式 host 和认证头创建应用市场客户端

- Capability ID: `console.market-client.host-config`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.restful_client.get_market_client`
- 代码路径: `console/utils/restful_client.py`
- 测试路径: `console/tests/utils/restful_client_test.py::RestfulClientFactoryTests.test_get_market_client_uses_explicit_host`

### 将 404 应用市场错误转换为资源不存在异常

- Capability ID: `console.market-client.not-found`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.restful_client.apiException`
- 代码路径: `console/utils/restful_client.py`
- 测试路径: `console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_404`

### 将 403 应用市场错误转换为商店权限异常

- Capability ID: `console.market-client.permission-denied`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.restful_client.apiException`
- 代码路径: `console/utils/restful_client.py`
- 测试路径: `console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_403`

### 将通用 5xx 应用市场错误转换为兜底服务异常

- Capability ID: `console.market-client.server-error`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.restful_client.apiException`
- 代码路径: `console/utils/restful_client.py`
- 测试路径: `console/tests/utils/restful_client_test.py::RestfulClientApiExceptionTests.test_api_exception_generic_5xx`

### Market App Model Versions Local

- Capability ID: `console.market.app-model-versions-local`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.market.app-model-versions-local]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_app_model_versions_for_local_returns_versions`

### Market Cloud App Models

- Capability ID: `console.market.cloud-app-models`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.market.cloud-app-models]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_cloud_app_models_returns_market_templates`

### Market Cloud Markets

- Capability ID: `console.market.cloud-markets`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.market.cloud-markets]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_cloud_markets_returns_market_list`

### Market Install App Model Cloud

- Capability ID: `console.market.install-app-model-cloud`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.market.install-app-model-cloud]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_install_app_model_for_cloud_calls_market_app_service`

### Market Local App Models

- Capability ID: `console.market.local-app-models`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.market.local-app-models]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_query_local_app_models_returns_paginated_templates`

### MCP 应用健康总览工具

- Capability ID: `console.mcp.app-health-overview`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.mcp.app-health-overview]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_health_overview_test.py`

### MCP 环境变量多源冲突检测工具

- Capability ID: `console.mcp.env-conflicts`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.mcp.env-conflicts]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_env_conflicts_test.py`

### 通过 HTTP 关闭 MCP 会话

- Capability ID: `console.mcp.http-delete-session`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.mcp_query.MCPQueryHTTPView.delete`
- 代码路径: `console/views/mcp_query.py`
- 测试路径: `console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_delete_accepts_valid_session_token`

### MCP HTTP 接口对过期 JWT 返回 401

- Capability ID: `console.mcp.http-expired-jwt`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.mcp_query.MCPQueryHTTPView.post`
- 代码路径: `console/views/mcp_query.py`
- 测试路径: `console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_post_returns_401_for_expired_jwt`

### 通过 HTTP 初始化 MCP 会话

- Capability ID: `console.mcp.http-initialize`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.mcp_query.MCPQueryHTTPView.post`
- 代码路径: `console/views/mcp_query.py`
- 测试路径: `console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_initialize_returns_json_and_session_header`

### Mcp Http Tools List With Auth

- Capability ID: `console.mcp.http-tools-list-with-auth`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.mcp_query.MCPQueryHTTPView`
- 代码路径: `console/views/mcp_query.py`
- 测试路径: `console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_post_tools_list_allows_authenticated_request_without_session_header`

### 通过 HTTP 端点以 SSE 返回工具列表

- Capability ID: `console.mcp.http-tools-sse`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.mcp_query.MCPQueryHTTPView.post`
- 代码路径: `console/views/mcp_query.py`
- 测试路径: `console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_post_can_return_sse_message_response`

### MCP 工具对缺参/查无组件返回清晰原因

- Capability ID: `console.mcp.input-validation-contract`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.mcp_query_service.call_tool`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_error_contract_test.py::MCPComponentContextErrorTests.test_missing_service_id_returns_invalid_input`, `console/tests/mcp_query_error_contract_test.py::MCPComponentContextErrorTests.test_unknown_component_returns_not_found`

### 打开兼容模式的 SSE MCP 端点

- Capability ID: `console.mcp.legacy-sse-endpoint`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.mcp_query.MCPQuerySSEView.get`
- 代码路径: `console/views/mcp_query.py`
- 测试路径: `console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_get_returns_endpoint_event_for_legacy_sse_clients`

### MCP operate_app/upgrade_app 返回操作事件 ID

- Capability ID: `console.mcp.operation-event-ids`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.mcp.operation-event-ids]`
- 代码路径: `console/services/mcp_query_service.py`, `console/services/upgrade_services.py`
- 测试路径: `console/tests/mcp_query_operation_event_ids_test.py`

### MCP 操作失败分类器

- Capability ID: `console.mcp.operation-failure-classifier`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `package_function`
- 业务入口: `console.services.mcp_failure_classifier.classify_failure`
- 代码路径: `console/services/mcp_failure_classifier.py`
- 测试路径: `console/tests/mcp_failure_classifier_test.py`

### MCP 操作失败上下文工具

- Capability ID: `console.mcp.operation-failure-context`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.mcp.operation-failure-context]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_failure_context_test.py`

### 向 SSE 会话投递 MCP 消息

- Capability ID: `console.mcp.post-message`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.mcp_query.MCPQueryMessageView.post`
- 代码路径: `console/views/mcp_query.py`
- 测试路径: `console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_post_message_enqueues_initialize_response_on_sse_stream`

### MCP 响应中递归序列化嵌套 SDK 模型

- Capability ID: `console.mcp.serialize-nested-sdk-models`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `other`
- 业务入口: `console.services.mcp_query_service.MCPQueryService._serialize_model_item`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceSerializeModelItemTests.test_serialize_model_item_recurses_into_dict_values`, `console/tests/mcp_query_service_test.py::MCPQueryServiceSerializeModelItemTests.test_serialize_model_item_handles_object_with_nested_sdk_attribute`

### Mcp Structured Tool Error

- Capability ID: `console.mcp.structured-tool-error`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.mcp_query.MCPQueryHTTPView`
- 代码路径: `console/views/mcp_query.py`
- 测试路径: `console/tests/mcp_query_view_test.py::MCPQuerySSEViewTests.test_http_tool_error_includes_structured_validation_details`

### 任意 MCP 工具失败均返回可解析错误

- Capability ID: `console.mcp.tool-error-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.mcp_query.MCPQueryRPCMixin._dispatch_rpc`
- 代码路径: `console/views/mcp_query.py`
- 测试路径: `console/tests/mcp_query_error_contract_test.py::MCPToolErrorDispatchTests.test_generic_tool_exception_is_returned_as_parseable_error`, `console/tests/mcp_query_error_contract_test.py::MCPToolErrorDispatchTests.test_region_style_exception_maps_status_and_extracts_message`

### MCP 构建/部署就绪等待工具

- Capability ID: `console.mcp.wait-for-build-completion`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.mcp.wait-for-build-completion]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_wait_build_test.py`

### Ns Resource Batch Create

- Capability ID: `console.ns-resource.batch-create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources`
- 代码路径: `console/views/team_resources.py`
- 测试路径: `console/tests/team_resources_test.py::NsResourceDetailViewTestCase.test_post_preserves_partial_success_status_and_payload`

### 通过 YAML 更新命名空间资源

- Capability ID: `console.ns-resource.update`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources.NsResourceDetailView.put`
- 代码路径: `console/views/team_resources.py`, `www/apiclient/regionapi.py`
- 测试路径: `console/tests/team_resources_test.py::NsResourceDetailViewTestCase.test_put_accepts_yaml_media_type_and_forwards_raw_body`, `console/tests/team_resources_test.py::RegionInvokeApiNsResourceTestCase.test_put_tenant_ns_resource_preserves_custom_content_type`

### 创建 OAuth helper 实例并绑定服务与用户上下文

- Capability ID: `console.oauth.instance-create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.oauth.oauth_types.get_oauth_instance`
- 代码路径: `console/utils/oauth/oauth_types.py`
- 测试路径: `console/tests/utils/oauth_types_test.py::OAuthTypeTests.test_get_oauth_instance`

### 返回基础与 git OAuth helper 的能力标记

- Capability ID: `console.oauth.kind-flags`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.oauth.base.git_oauth.GitOAuth2Interface.is_git_oauth`
- 代码路径: `console/utils/oauth/base/git_oauth.py`
- 测试路径: `console/tests/utils/oauth_base_test.py::OAuthBaseTests.test_oauth_kind_flags`

### 创建带重试 HTTP 适配器的 OAuth 会话

- Capability ID: `console.oauth.session-retry`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.oauth.base.oauth.OAuth2Interface.set_session`
- 代码路径: `console/utils/oauth/base/oauth.py`
- 测试路径: `console/tests/utils/oauth_base_test.py::OAuthBaseTests.test_set_session_builds_retrying_requests_session`

### 列出支持的 OAuth 服务类型

- Capability ID: `console.oauth.supported-types`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.oauth.oauth_types.get_support_oauth_servers`
- 代码路径: `console/utils/oauth/oauth_types.py`
- 测试路径: `console/tests/utils/oauth_types_test.py::OAuthTypeTests.test_get_support_oauth_servers`

### 将刷新的 OAuth access/refresh token 持久化到绑定用户

- Capability ID: `console.oauth.token-update`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.oauth.base.oauth.OAuth2Interface.update_access_token`
- 代码路径: `console/utils/oauth/base/oauth.py`
- 测试路径: `console/tests/utils/oauth_base_test.py::OAuthBaseTests.test_update_access_token_updates_bound_user`

### 拒绝不支持的 OAuth 服务类型

- Capability ID: `console.oauth.unsupported-type`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.oauth.oauth_types.get_oauth_instance`
- 代码路径: `console/utils/oauth/oauth_types.py`
- 测试路径: `console/tests/utils/oauth_types_test.py::OAuthTypeTests.test_get_oauth_instance_unsupported_type`

### 将 OAuth 服务和用户对象绑定到 helper 实例

- Capability ID: `console.oauth.user-binding`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.oauth.base.oauth.OAuth2Interface.set_oauth_user`
- 代码路径: `console/utils/oauth/base/oauth.py`
- 测试路径: `console/tests/utils/oauth_base_test.py::OAuthBaseTests.test_set_oauth_user_and_service`

### Skip KubeBlocks services during operator-managed component import

- Capability ID: `console.operator-managed.skip-kubeblocks-services`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.group_service.GroupService.get_watch_managed_data`
- 代码路径: `console/services/group_service.py`
- 测试路径: `console/tests/group_service_test.py::GroupServiceOperatorManagedTests`

### 执行制品包组件自动创建全流程

- Capability ID: `console.package-component.auto-create-flow`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_component_service.auto_create_component`
- 代码路径: `console/services/package_component_service.py`
- 测试路径: `console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_runs_full_package_flow`

### 制品包组件检测请求失败时拦截创建

- Capability ID: `console.package-component.check-request-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_component_service.auto_create_component`
- 代码路径: `console/services/package_component_service.py`
- 测试路径: `console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_rejects_check_request_failure`

### 制品包组件部署失败时拦截创建

- Capability ID: `console.package-component.deploy-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_component_service.auto_create_component`
- 代码路径: `console/services/package_component_service.py`
- 测试路径: `console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_rejects_deploy_failure`

### 制品包组件创建时拦截重复英文名

- Capability ID: `console.package-component.duplicate-name-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_component_service.auto_create_component`
- 代码路径: `console/services/package_component_service.py`
- 测试路径: `console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_rejects_duplicate_k8s_component_name`

### 单组件流程中拦截多组件制品包检测结果

- Capability ID: `console.package-component.multi-service-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_component_service.auto_create_component`
- 代码路径: `console/services/package_component_service.py`
- 测试路径: `console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_rejects_multi_service_package`

### 创建制品包组件前必须存在上传记录

- Capability ID: `console.package-component.require-upload-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_component_service.auto_create_component`
- 代码路径: `console/services/package_component_service.py`
- 测试路径: `console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_requires_existing_upload_record`

### 制品包列表为空时拦截组件创建

- Capability ID: `console.package-component.upload-missing`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_component_service.auto_create_component`
- 代码路径: `console/services/package_component_service.py`
- 测试路径: `console/tests/package_component_service_test.py::PackageComponentServiceTests.test_auto_create_component_requires_uploaded_package_list`

### Package Upload Archive Reuse

- Capability ID: `console.package-upload.archive-reuse`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_upload_tool_service`
- 代码路径: `console/services/package_upload_tool_service.py`
- 测试路径: `console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_prepare_upload_archive_reuses_supported_package_file`

### Package Upload Archive Zip Dir

- Capability ID: `console.package-upload.archive-zip-dir`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_upload_tool_service`
- 代码路径: `console/services/package_upload_tool_service.py`
- 测试路径: `console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_prepare_upload_archive_zips_directory`

### Package Upload Delete

- Capability ID: `console.package-upload.delete`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.package-upload.delete]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_delete_package_upload_delegates_to_upload_tool_service`

### Package Upload Delete Flow

- Capability ID: `console.package-upload.delete-flow`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_upload_tool_service`
- 代码路径: `console/services/package_upload_tool_service.py`
- 测试路径: `console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_delete_upload_cleans_remote_dir_and_marks_record`

### Package Upload File

- Capability ID: `console.package-upload.file`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.package-upload.file]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_upload_package_file_delegates_to_upload_tool_service`

### Package Upload Init

- Capability ID: `console.package-upload.init`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.package-upload.init]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_init_package_upload_delegates_to_upload_tool_service`

### Package Upload Init Flow

- Capability ID: `console.package-upload.init-flow`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_upload_tool_service`
- 代码路径: `console/services/package_upload_tool_service.py`
- 测试路径: `console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_init_upload_creates_remote_dir_and_record`

### Package Upload Local Package

- Capability ID: `console.package-upload.local-package`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.package-upload.local-package]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_create_component_from_local_package_calls_upload_tool_service`

### Package Upload Local Package Flow

- Capability ID: `console.package-upload.local-package-flow`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_upload_tool_service`
- 代码路径: `console/services/package_upload_tool_service.py`
- 测试路径: `console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_auto_create_component_from_local_path_runs_full_flow`

### create_component_from_local_package 工具 schema 暴露服务端本地路径指引

- Capability ID: `console.package-upload.local-path-create-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.list_tools[console.package-upload.local-path-create-schema]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_create_component_from_local_package_tool_schema_exposes_server_side_local_path_guidance`

### _normalize_local_path 在路径缺失时抛出结构化详情

- Capability ID: `console.package-upload.local-path-missing-details`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.package_upload_tool_service.PackageUploadToolService._normalize_local_path`
- 代码路径: `console/services/package_upload_tool_service.py`
- 测试路径: `console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_normalize_local_path_raises_structured_details_when_path_missing`

### _normalize_local_path 在路径为空时抛出结构化详情

- Capability ID: `console.package-upload.local-path-required-details`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.package_upload_tool_service.PackageUploadToolService._normalize_local_path`
- 代码路径: `console/services/package_upload_tool_service.py`
- 测试路径: `console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_normalize_local_path_raises_structured_details_when_path_empty`

### Package Upload Local Path Schema

- Capability ID: `console.package-upload.local-path-schema`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.package-upload.local-path-schema]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_upload_package_file_tool_schema_exposes_local_path_guidance`

### Package Upload Status

- Capability ID: `console.package-upload.status`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.package-upload.status]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_package_upload_status_delegates_to_upload_tool_service`

### Package Upload Status Flow

- Capability ID: `console.package-upload.status-flow`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_upload_tool_service`
- 代码路径: `console/services/package_upload_tool_service.py`
- 测试路径: `console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_get_upload_status_reads_packages_and_updates_record`

### Package Upload Upload Flow

- Capability ID: `console.package-upload.upload-flow`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.package_upload_tool_service`
- 代码路径: `console/services/package_upload_tool_service.py`
- 测试路径: `console/tests/package_upload_tool_service_test.py::PackageUploadToolServiceTests.test_upload_package_uploads_archive_and_returns_status`

### 从前端组件访问地址回填官方虚拟机插件访问前缀

- Capability ID: `console.platform-plugin.vm-access-url-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.plugin_service.RainbondPluginService.list_plugins`
- 代码路径: `console/services/plugin_service.py`
- 测试路径: `console/tests/rbd_plugin_service_test.py::RainbondPluginServiceTests.test_official_vm_plugin_uses_frontend_component_access_url_when_region_urls_missing`

### 校验虚拟机平台插件运行状态

- Capability ID: `console.platform-plugin.vm-runtime-status-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.platform_plugin_service.PlatformPluginService.ensure_vm_plugin_running`
- 代码路径: `console/services/platform_plugin_service.py`
- 测试路径: `console/tests/platform_plugin_service_test.py::PlatformPluginServiceTests.test_ensure_vm_plugin_running_rejects_non_running_status`

### Infer plugin build architecture from region chaos nodes

- Capability ID: `console.plugin-build.infer-arch`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.plugin_build_arch.resolve_plugin_build_arch`
- 代码路径: `console/services/plugin_build_arch.py`, `console/services/plugin/app_plugin.py`, `console/views/plugin/plugin_manage.py`
- 测试路径: `console/tests/plugin_build_arch_test.py::PluginBuildArchTests`

### 按组件 ID 删除其全部插件关联

- Capability ID: `console.plugin.delete-by-sid`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `dao_method`
- 业务入口: `console.repositories.plugin.service_plugin_repo.AppPluginRelationRepo.delete_by_sid`
- 代码路径: `console/repositories/plugin/service_plugin_repo.py`
- 测试路径: `console/tests/service_plugin_repo_delete_by_sid_test.py::DeleteBySidTest.test_delete_by_sid_deletes_matching_relations`

### 下游端口配置从 ORM 模型对象读取目标组件属性

- Capability ID: `console.plugin.downstream-port-config`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.plugin.app_plugin.AppPluginService.create_plugin_cfg_4marketsvc`
- 代码路径: `console/services/plugin/app_plugin.py`
- 测试路径: `console/tests/app_plugin_downstream_port_test.py::CreatePluginCfg4MarketsvcDownstreamPortTest.test_downstream_port_reads_dest_service_attributes`

### Pod Detail

- Capability ID: `console.pod.detail`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.pod.detail]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_pod_detail_returns_runtime_diagnostics`

### Pod Detail Kubeblocks

- Capability ID: `console.pod.detail-kubeblocks`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.call_tool[console.pod.detail-kubeblocks]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceApplicationToolTests.test_get_pod_detail_uses_kubeblocks_endpoint_for_kubeblocks_component`

### Treat duplicate region env create as idempotent during inner port enable

- Capability ID: `console.port-inner.env-sync-idempotent`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.env_service.AppEnvVarService.add_service_env_var`
- 代码路径: `console/services/app_config/env_service.py`
- 测试路径: `console/tests/env_service_region_idempotency_test.py::EnvServiceRegionIdempotencyTests.test_add_service_env_var_updates_region_when_env_already_exists`, `console/tests/env_service_region_idempotency_test.py::EnvServiceRegionIdempotencyTests.test_add_service_env_var_retries_add_when_region_update_reports_record_not_found`, `console/tests/env_service_region_idempotency_test.py::EnvServiceRegionIdempotencyTests.test_add_service_env_var_treats_second_add_conflict_as_success`

### 生成默认随机版本标识

- Capability ID: `console.random.default-version`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.randomutil.make_default_version`
- 代码路径: `console/utils/randomutil.py`
- 测试路径: `console/tests/utils/randomutil_test.py::RandomUtilTests.test_make_default_version`

### Docker 控制台后端使用 webtty 子协议

- Capability ID: `console.realtime-proxy.docker-console-subprotocol`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy._backend_websocket_subprotocols`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_docker_console_backend_uses_webtty_subprotocol`

### Docker 控制台活动跟踪在用户输入时刷新

- Capability ID: `console.realtime-proxy.docker-console-user-activity`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.DockerConsoleActivityTracker`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_docker_console_activity_tracker_refreshes_on_user_input`

### Docker 控制台活动跟踪忽略 webtty 心跳

- Capability ID: `console.realtime-proxy.docker-console-user-idle-timeout`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.DockerConsoleActivityTracker`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_docker_console_activity_tracker_ignores_webtty_ping`

### 文件操作上传原始转发 multipart 请求

- Capability ID: `console.realtime-proxy.file-operate-raw-multipart-forward`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.proxy_http_request`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_file_operate_upload_forwards_raw_multipart_body`

### 转发客户端请求的 websocket 子协议

- Capability ID: `console.realtime-proxy.forward-client-subprotocols`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy._backend_websocket_subprotocols`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_websocket_proxy_keeps_client_requested_subprotocols`

### 实时代理 HTTP 转发

- Capability ID: `console.realtime-proxy.http-forward`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.proxy_http_request`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_http_proxy_forwards_upload_request_to_region_websocket_service`

### 实时代理内部目标覆盖

- Capability ID: `console.realtime-proxy.internal-target-override`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.build_region_realtime_proxy_url`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_region_proxy_target_prefers_internal_override_for_builtin_region`

### 转发文件夹上传中的重复 multipart 文件字段

- Capability ID: `console.realtime-proxy.multipart-folder-upload-forward`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.build_multipart_payload`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_multipart_folder_upload_encodes_repeated_file_field`

### 实时代理重建分片上传请求

- Capability ID: `console.realtime-proxy.multipart-upload-forward`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.build_multipart_payload`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_http_proxy_rebuilds_multipart_upload_for_app_import`

### 非终端实时代理不触发用户空闲超时

- Capability ID: `console.realtime-proxy.non-terminal-no-user-idle-timeout`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.DockerConsoleActivityTracker`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_non_docker_console_activity_tracker_never_user_idle_expires`

### 组件构建包上传原始转发 multipart 请求

- Capability ID: `console.realtime-proxy.package-build-raw-multipart-forward`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.proxy_http_request`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_package_build_upload_forwards_raw_multipart_body`

### 实时代理 Region 目标 URL

- Capability ID: `console.realtime-proxy.region-target-url`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.build_region_realtime_proxy_url`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_region_proxy_target_keeps_region_websocket_host_for_http`

### 实时代理安全 WebSocket URL

- Capability ID: `console.realtime-proxy.secure-websocket-url`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.build_console_realtime_proxy_url`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_console_proxy_url_uses_wss_when_request_is_https`

### 实时代理上传 URL

- Capability ID: `console.realtime-proxy.upload-url`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_import_and_export_service.get_upload_package_url`
- 代码路径: `console/services/app_import_and_export_service.py`, `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_upload_package_url_returns_console_proxy_path`

### 后端 websocket 使用短读超时检测空闲

- Capability ID: `console.realtime-proxy.websocket-idle-timeout`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.utils.realtime_proxy.open_backend_websocket`
- 代码路径: `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_backend_websocket_uses_short_read_timeout_for_idle_checks`

### 实时代理 WebSocket URL

- Capability ID: `console.realtime-proxy.websocket-url`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_actions.app_log.AppWebSocketService.get_event_log_ws`
- 代码路径: `console/services/app_actions/app_log.py`, `console/utils/realtime_proxy.py`
- 测试路径: `console/tests/realtime_proxy_url_test.py::RealtimeProxyUrlTests.test_websocket_service_returns_console_proxy_url_without_6060`

### Region Api Batch Create Error Bean

- Capability ID: `console.region-api.batch-create-error-bean`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status`
- 代码路径: `www/apiclient/regionapibaseclient.py`
- 测试路径: `console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_preserves_batch_create_result_bean_for_coded_errors`

### 将上游域名冲突保留为可操作的 409 错误提示

- Capability ID: `console.region-api.domain-conflict-msg`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status`
- 代码路径: `www/apiclient/regionapibaseclient.py`
- 测试路径: `console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_keeps_domain_conflict_as_conflict_error`

### 将 Helm 资源归属冲突转换为可操作错误提示

- Capability ID: `console.region-api.helm-resource-conflict-msg`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status`
- 代码路径: `www/apiclient/regionapibaseclient.py`
- 测试路径: `console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_translates_helm_ownership_conflict_to_actionable_msg_show`

### 对非 Helm 冲突保留原始上游错误信息

- Capability ID: `console.region-api.proxy-error-pass-through`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status`
- 代码路径: `www/apiclient/regionapibaseclient.py`
- 测试路径: `console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_keeps_original_message_for_non_helm_conflicts`

### _check_status 将虚拟机快照功能门禁错误翻译为可操作提示

- Capability ID: `console.region-api.vm-snapshot-feature-gate-msg`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `www.apiclient.regionapibaseclient.RegionApiBaseHttpClient._check_status`
- 代码路径: `www/apiclient/regionapibaseclient.py`
- 测试路径: `console/tests/regionapibaseclient_test.py::RegionApiBaseHttpClientTestCase.test_check_status_translates_snapshot_feature_gate_error_to_actionable_msg_show`

### 依据配置项是否存在选择更新或新增数据中心配置

- Capability ID: `console.region.update-region-config`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.region_services.RegionService.update_region_config`
- 代码路径: `console/services/region_services.py`
- 测试路径: `console/tests/region_config_update_test.py::UpdateRegionConfigTest.test_update_when_config_exists_passes_dict_value`, `console/tests/region_config_update_test.py::UpdateRegionConfigTest.test_add_when_config_missing_passes_json_string_and_desc`

### 将请求中的布尔参数从字符串或布尔值安全转换

- Capability ID: `console.request-args.bool-coercion`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.bool_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::BoolArgumentTestCase`

### 缺失布尔查询参数时返回 false 默认值

- Capability ID: `console.request-args.bool-default-false`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_default_false_bool`

### 为布尔查询参数使用 true 默认值

- Capability ID: `console.request-args.bool-default-true`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_default_bool`

### 拒绝非法布尔查询参数值

- Capability ID: `console.request-args.bool-invalid`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_bool_error`

### 解析布尔查询参数

- Capability ID: `console.request-args.bool-parse`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_bool`

### 解析请求 data 载荷并处理默认值与必填校验

- Capability ID: `console.request-args.data-parse`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_item`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseDateTestCase`

### 拒绝类型不匹配的默认请求参数

- Capability ID: `console.request-args.default-type-error`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_default_error`

### 整型查询参数缺失时返回空值

- Capability ID: `console.request-args.int-missing`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_not__return_int`

### 解析整型查询参数

- Capability ID: `console.request-args.int-parse`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_int`

### 要求提供整型查询参数

- Capability ID: `console.request-args.int-required`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_int_must`

### 拒绝缺失的必填整型查询参数

- Capability ID: `console.request-args.int-required-missing`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_not_parse_argument_return_int_must`

### 缺失多值查询参数时返回列表默认值

- Capability ID: `console.request-args.list-default-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_list_default`

### 列表查询参数缺失时返回空值

- Capability ID: `console.request-args.list-missing`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_not_get_argument_return_list`

### 将重复查询参数解析为列表

- Capability ID: `console.request-args.list-parse`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_list`

### 要求提供列表查询参数

- Capability ID: `console.request-args.list-required`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_list_must`

### 拒绝缺失的必填列表查询参数

- Capability ID: `console.request-args.list-required-missing`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_not_parse_argument_return_list_must`

### 解析查询参数映射时保留 falsy 值

- Capability ID: `console.request-args.parse-args-keep-falsy`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_args`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_args_keep_falsy_values`

### 按配置批量解析查询参数

- Capability ID: `console.request-args.parse-batch`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_args`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_args`

### 将查询字符串参数解析为带类型的值

- Capability ID: `console.request-args.query-parse`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase`

### 解析字符串查询参数

- Capability ID: `console.request-args.string-parse`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_parse_argument_return_str`

### 拒绝不支持的请求参数类型

- Capability ID: `console.request-args.type-error`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_argument`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseArgumentTestCase.test_value_type_error`

### 从字典请求体中解析字段

- Capability ID: `console.request-data.dict-parse`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_item`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_dict_data`

### 解析单个请求体字段

- Capability ID: `console.request-data.item-parse`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_item`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_item`

### 要求提供单个请求体字段

- Capability ID: `console.request-data.item-required`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_item`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_item_must`

### 拒绝缺失的必填请求体字段

- Capability ID: `console.request-data.item-required-missing`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_item`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseDateTestCase.test_not_parse_item_must`

### 批量解析请求体数据

- Capability ID: `console.request-data.parse-batch`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_date`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_data`

### 解析请求 data 映射时保留 falsy 值

- Capability ID: `console.request-data.parse-date-keep-falsy`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_date`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_date_keep_falsy_values`

### 缺失请求 data 时抛出默认必填字段错误

- Capability ID: `console.request-data.required-default-error`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.reqparse.parse_item`
- 代码路径: `console/utils/reqparse.py`
- 测试路径: `console/tests/utils/reqparse_test.py::ParseDateTestCase.test_parse_item_required_uses_default_error_message`

### 查看资源中心 Pod 日志

- Capability ID: `console.resource-center.pod-logs`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team_resources.ResourceCenterPodLogsView.get`
- 代码路径: `console/views/team_resources.py`, `www/apiclient/regionapi.py`
- 测试路径: `console/tests/team_resources_test.py::ResourceCenterPodLogsViewTestCase.test_get_sends_heartbeat_before_upstream_logs`, `console/tests/regionapi_sse_proxy_test.py::RegionApiSSEProxyTests.test_sse_proxy_passes_region_auth_headers`, `console/tests/regionapi_sse_proxy_test.py::RegionApiSSEProxyTests.test_sse_proxy_rewrites_console_tenant_name_to_region_tenant_name`, `console/tests/regionapi_sse_proxy_test.py::RegionApiSSEProxyTests.test_get_component_pod_log_uses_bounded_read_timeout`

### Rainbond 安装失败时返回结构化错误且不进入集成中状态

- Capability ID: `console.rke2.cluster-install-structured-helm-error`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.rke2.ClusterRKEInstallRB.post`
- 代码路径: `console/views/rke2.py`, `console/utils/k8s_cli.py`
- 测试路径: `console/tests/rke2_cluster_errors_test.py::ClusterRKEErrorTests.test_cluster_install_returns_structured_helm_error_without_saving_integrating`

### 请求的 RKE 集群元数据缺失时返回 404

- Capability ID: `console.rke2.cluster-missing-metadata-404`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.rke2.ClusterRKE.get`
- 代码路径: `console/views/rke2.py`
- 测试路径: `console/tests/rke2_cluster_errors_test.py::ClusterRKEErrorTests.test_cluster_get_returns_structured_404_when_cluster_metadata_missing`

### 清洗 Rainbond 安装中的 Helm 子进程失败信息

- Capability ID: `console.rke2.helm-subprocess-error-sanitized`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.k8s_cli.K8sClient.install_rainbond`
- 代码路径: `console/utils/k8s_cli.py`
- 测试路径: `console/tests/rke2_cluster_errors_test.py::ClusterRKEErrorTests.test_install_rainbond_returns_sanitized_subprocess_error`

### 创建组件共享记录

- Capability ID: `console.service-share.create-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.service_share.ServiceShareRecordView.post`
- 代码路径: `console/views/service_share.py`, `console/services/share_services.py`
- 测试路径: `console/tests/service_share_test.py::ServiceShareRecordViewTestCase`

### 创建基于快照的服务分享记录

- Capability ID: `console.service-share.create-snapshot-record`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.service_share.ServiceShareRecordView.post`
- 代码路径: `console/views/service_share.py`, `console/services/share_services.py`
- 测试路径: `console/tests/service_share_test.py::ServiceShareRecordViewTestCase.test_post_snapshot_mode_uses_hidden_template_app_id`

### 服务分享异常时返回错误响应

- Capability ID: `console.service-share.error-response`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.service_share.ServiceShareRecordView.post`
- 代码路径: `console/views/service_share.py`
- 测试路径: `console/tests/service_share_test.py::ServiceShareRecordViewTestCase.test_post_returns_500_response_for_unexpected_exception`

### 列出团队本地可分享应用版本

- Capability ID: `console.service-share.local-app-versions`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.share_services.ShareService.get_team_local_apps_versions`
- 代码路径: `console/services/share_services.py`
- 测试路径: `console/tests/service_share_test.py::ShareServicePreferredAppTestCase.test_get_team_local_apps_versions_keeps_team_apps_when_preferred_app_is_hidden_snapshot`

### 解析最近一次分享的应用版本

- Capability ID: `console.service-share.resolve-last-shared-app`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.share_services.ShareService.get_last_shared_app_and_app_list`
- 代码路径: `console/services/share_services.py`
- 测试路径: `console/tests/service_share_test.py::ShareServicePreferredAppTestCase.test_get_last_shared_app_ignores_missing_versions_for_preferred_local_app`

### 允许已停止组件发布

- Capability ID: `console.service-share.stopped-component-publish`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.share_services.ShareService.check_service_source`
- 代码路径: `console/services/share_services.py`
- 测试路径: `console/tests/service_share_test.py::ShareServiceCheckServiceSourceTestCase`

### 查看组件共享详情

- Capability ID: `console.service-share.view-info`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.service_share.ServiceShareInfoView.get`
- 代码路径: `console/views/service_share.py`, `console/services/share_services.py`
- 测试路径: `console/tests/service_share_test.py::ServiceShareInfoViewTestCase`

### 查看分享快照详情

- Capability ID: `console.service-share.view-snapshot-info`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.service_share.ServiceShareInfoView.get`
- 代码路径: `console/views/service_share.py`, `console/services/share_services.py`
- 测试路径: `console/tests/service_share_test.py::ServiceShareInfoViewTestCase.test_get_returns_snapshot_template_payload`

### 将虚拟机系统盘发布为 qcow2 镜像源

- Capability ID: `console.service-share.vm-qcow2-publish`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.share_services.ShareService.sync_event`
- 代码路径: `console/repositories/share_repo.py`, `console/services/share_services.py`
- 测试路径: `console/tests/service_share_test.py::ShareRepoVMServiceSourceTestCase.test_get_service_list_keeps_vm_run_components_for_publish`, `console/tests/service_share_test.py::ShareServiceCreateSnapshotPublishTestCase.test_sync_event_passes_vm_image_source_for_vm_publish`, `console/tests/service_share_test.py::ShareServiceCreateSnapshotPublishTestCase.test_sync_event_passes_vm_export_token_for_live_vm_publish`, `console/tests/service_share_test.py::ShareServiceVMPublishMetadataTestCase`

### 虚拟机发布关机限制

- Capability ID: `console.service-share.vm-shutdown-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.share_services.ShareService.check_service_source`
- 代码路径: `console/services/share_services.py`
- 测试路径: `console/tests/service_share_test.py::ShareServiceCheckServiceSourceTestCase`

### 执行源码组件自动创建全流程

- Capability ID: `console.source-component.auto-create-flow`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.auto_create_component`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_runs_full_source_flow`

### 应用默认源码构建配置失败时抛错

- Capability ID: `console.source-component.build-config-error`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.apply_default_build_config`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_apply_default_build_config_raises_when_save_fails`

### 源码组件检测失败时中止创建

- Capability ID: `console.source-component.check-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.auto_create_component`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_raises_on_check_failure`

### 源码组件检测失败时返回首个错误

- Capability ID: `console.source-component.check-poll-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service._wait_for_check_result`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_wait_for_check_result_raises_with_first_error_info`

### 源码组件检测轮询直到成功

- Capability ID: `console.source-component.check-poll-success`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service._wait_for_check_result`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_wait_for_check_result_retries_until_success`

### 源码组件检测请求失败时拦截创建

- Capability ID: `console.source-component.check-request-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.auto_create_component`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_rejects_check_request_failure`

### Source Component Check Timeout Pending

- Capability ID: `console.source-component.check-timeout-pending`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.source_component_service`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_returns_pending_result_when_check_times_out`

### 源码组件部署失败时拦截创建

- Capability ID: `console.source-component.deploy-failure`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.auto_create_component`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_rejects_deploy_failure`

### 识别源码仓库服务类型

- Capability ID: `console.source-component.detect-server-type`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.infer_server_type`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_infer_server_type_supports_git_svn_and_oss`

### 源码组件创建时拦截重复英文名

- Capability ID: `console.source-component.duplicate-name-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.auto_create_component`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_rejects_duplicate_k8s_component_name`

### 拦截不支持的源码仓库服务类型

- Capability ID: `console.source-component.invalid-server-type`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.infer_server_type`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_infer_server_type_rejects_unknown_server_type`

### 单组件流程中拦截多组件源码检测结果

- Capability ID: `console.source-component.multi-service-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.auto_create_component`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_rejects_multi_service_detection`

### 规范化源码来源类型

- Capability ID: `console.source-component.normalize-code-source`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.normalize_code_from`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_normalize_code_from_maps_generic_git_to_gitlab_manual`

### 按来源类型规范化源码版本

- Capability ID: `console.source-component.normalize-code-version`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.normalize_code_version`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_normalize_code_version_handles_tag_and_oss`

### 为 Git 地址追加一次子目录参数

- Capability ID: `console.source-component.normalize-git-url`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.source_component_service.normalize_git_url`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_normalize_git_url_appends_subdirectory_once`

### Source Component Prefer Dockerfile

- Capability ID: `console.source-component.prefer-dockerfile`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.source_component_service`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_prefers_dockerfile_when_requested`

### Source Component Prefer Dockerfile From Dockerfiles Flag

- Capability ID: `console.source-component.prefer-dockerfile-from-dockerfiles-flag`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.source_component_service`
- 代码路径: `console/services/source_component_service.py`
- 测试路径: `console/tests/source_component_service_test.py::SourceComponentServiceTests.test_auto_create_component_prefers_dockerfile_when_dockerfiles_exist`

### 创建团队时拒绝非法命名空间

- Capability ID: `console.team.create-invalid-namespace`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.team.AddTeamView.post`
- 代码路径: `console/views/team.py`
- 测试路径: `console/tests/add_team_namespace_validation_test.py::AddTeamInvalidNamespaceTest.test_invalid_namespace_raises_qualified_name_error_not_typeerror`

### 测试清单校验忽略嵌套 worktree 测试

- Capability ID: `console.test-manifest.ignore-worktrees`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `scripts.validate_test_manifest.collect_marked_tests`
- 代码路径: `scripts/validate_test_manifest.py`
- 测试路径: `scripts/validate_test_manifest_test.py::ValidateTestManifestTests`

### 返回默认格式的当前日期字符串

- Capability ID: `console.timeutil.current-date-str`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.timeutil.current_time_to_str`
- 代码路径: `console/utils/timeutil.py`
- 测试路径: `console/tests/utils/timeutil_test.py::TimeUtilTests.test_current_time_to_str`

### 返回当前 datetime 对象

- Capability ID: `console.timeutil.current-time`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.timeutil.current_time`
- 代码路径: `console/utils/timeutil.py`
- 测试路径: `console/tests/utils/timeutil_test.py::TimeUtilTests.test_current_time`

### 返回格式化的当前时间字符串

- Capability ID: `console.timeutil.current-time-str`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.timeutil.current_time_str`
- 代码路径: `console/utils/timeutil.py`
- 测试路径: `console/tests/utils/timeutil_test.py::TimeUtilTests.test_current_time_str`

### 将 datetime 对象格式化为指定字符串

- Capability ID: `console.timeutil.format`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.timeutil.time_to_str`
- 代码路径: `console/utils/timeutil.py`
- 测试路径: `console/tests/utils/timeutil_test.py::TimeUtilTests.test_time_to_str`

### 将格式化时间字符串解析为 datetime 对象

- Capability ID: `console.timeutil.parse`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.timeutil.str_to_time`
- 代码路径: `console/utils/timeutil.py`
- 测试路径: `console/tests/utils/timeutil_test.py::TimeUtilTests.test_str_to_time`

### 向企业管理员暴露管理工具集

- Capability ID: `console.tool-visibility.enterprise-admin`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.list_tools[enterprise_admin]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_list_tools_for_enterprise_admin_includes_region_and_enterprise_tools`

### 向普通用户隐藏企业管理工具

- Capability ID: `console.tool-visibility.standard-user`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.list_tools[standard_user]`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_list_tools_for_non_enterprise_admin_hides_region_and_enterprise_tools`

### 校验路径是否满足 URL 路径合法性规则

- Capability ID: `console.url.path-legal`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.urlutil.is_path_legal`
- 代码路径: `console/utils/urlutil.py`
- 测试路径: `console/tests/utils/urlutil_test.py::UrlUtilTests.test_is_path_legal`

### 根据基础路径和参数构建 GET URL

- Capability ID: `console.url.query-build`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.urlutil.set_get_url`
- 代码路径: `console/utils/urlutil.py`
- 测试路径: `console/tests/utils/urlutil_test.py::UrlUtilTests.test_set_get_url`

### 即使没有查询参数也能构建 GET URL

- Capability ID: `console.url.query-empty`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.urlutil.set_get_url`
- 代码路径: `console/utils/urlutil.py`
- 测试路径: `console/tests/utils/urlutil_test.py::UrlUtilTests.test_set_get_url_with_empty_params`

### 删除访问令牌时记录令牌备注

- Capability ID: `console.user.access-token-delete-log`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.user_accesstoken.UserAccessTokenRUDView.delete`
- 代码路径: `console/views/user_accesstoken.py`
- 测试路径: `console/tests/user_accesstoken_delete_log_test.py::UserAccessTokenDeleteLogTest.test_delete_logs_token_note_without_nameerror`

### 查看当前用户身份信息

- Capability ID: `console.user.current-profile`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.mcp_query_service.get_current_user`
- 代码路径: `console/services/mcp_query_service.py`
- 测试路径: `console/tests/mcp_query_service_test.py::MCPQueryServiceToolVisibilityTests.test_get_current_user_returns_identity_and_enterprise_admin_flag`

### 删除收藏视图时记录收藏名称

- Capability ID: `console.user.favorite-delete-log`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.user_operation.UserFavoriteUDView.delete`
- 代码路径: `console/views/user_operation.py`
- 测试路径: `console/tests/user_favorite_delete_log_test.py::UserFavoriteDeleteLogTest`

### 通过用户仓储按用户 ID 列表批量查询用户

- Capability ID: `console.user.get-users-by-ids`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.user_services.UserService.get_users_by_user_ids`
- 代码路径: `console/services/user_services.py`, `console/repositories/user_repo.py`
- 测试路径: `console/tests/user_services_get_by_ids_test.py::GetUsersByUserIdsTest.test_delegates_to_repo_get_by_user_ids`

### 校验用户展示名称的中英文数字与连接符规则

- Capability ID: `console.validation.display-name`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.validation.validate_name`
- 代码路径: `console/utils/validation.py`
- 测试路径: `console/tests/utils/validation_test.py::NamespaceNormalizationTests.test_validate_name`

### 校验 Kubernetes 合法资源名称格式

- Capability ID: `console.validation.k8s-qualified-name`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.validation.is_qualified_name`
- 代码路径: `console/utils/validation.py`
- 测试路径: `console/tests/utils/validation_test.py::NamespaceNormalizationTests.test_is_qualified_name`

### 比较语义化风格的版本字符串

- Capability ID: `console.version.compare`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.version.compare_version`
- 代码路径: `console/utils/version.py`
- 测试路径: `console/tests/utils/version_test.py::VersionUtilsTests.test_compare_version`

### 筛选出高于当前版本的新版本

- Capability ID: `console.version.newer-filter`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.version.get_new_versions`
- 代码路径: `console/utils/version.py`
- 测试路径: `console/tests/utils/version_test.py::VersionUtilsTests.test_get_new_versions`

### 按降序排列版本字符串

- Capability ID: `console.version.sort-desc`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.utils.version.sorted_versions`
- 代码路径: `console/utils/version.py`
- 测试路径: `console/tests/utils/version_test.py::VersionUtilsTests.test_sorted_versions`

### 虚拟机平台运行状态校验委托到平台插件守卫

- Capability ID: `console.virtual-machine.platform-runtime-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.ensure_vm_platform_running`
- 代码路径: `console/services/virtual_machine.py`
- 测试路径: `console/tests/vm_create_flow_regression_test.py::VMCreateFlowRegressionTests.test_ensure_vm_platform_running_delegates_to_platform_plugin_guard`

### 使用 registry 导入的系统盘创建虚拟机

- Capability ID: `console.virtual-machine.registry-root-disk`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.create_vm`
- 代码路径: `console/services/virtual_machine.py`
- 测试路径: `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests`

### 仅当活跃虚拟机仍引用时阻止删除镜像资产

- Capability ID: `console.vm-asset.delete-active-reference-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.delete_vm_image`
- 代码路径: `console/services/virtual_machine.py`
- 测试路径: `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_ignores_orphan_vm_asset_attrs`, `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_blocks_active_vm_asset_reference`, `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_ignores_incomplete_vm_service_reference`

### Delete internal VM registry manifest before removing local VM asset

- Capability ID: `console.vm-asset.delete-internal-registry-manifest`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.delete_vm_image`
- 代码路径: `console/services/virtual_machine.py`, `console/repositories/virtual_machine.py`, `www/apiclient/regionapi.py`
- 测试路径: `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_deletes_unique_internal_registry_manifest`, `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_skips_registry_manifest_when_image_url_is_shared`, `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_delete_vm_image_skips_registry_manifest_for_external_registry_asset`

### 删除未完成虚拟机组件时保留已就绪镜像资产

- Capability ID: `console.vm-asset.incomplete-service-cleanup-preserves-ready-assets`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_actions.app_manage.AppManageService._truncate_service`
- 代码路径: `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/app_manage_test.py::AppManageIncompleteVMCleanupTests.test_truncate_service_keeps_ready_uploaded_vm_asset`

### 虚拟机镜像资产引用组件列表

- Capability ID: `console.vm-asset.reference-components`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.serialize_vm_image`
- 代码路径: `console/services/virtual_machine.py`
- 测试路径: `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_get_vm_asset_includes_explicit_reference_components`, `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_get_vm_asset_includes_legacy_image_reference_components`

### 在缺少查询参数时从插件回填虚拟机概览 VNC 地址

- Capability ID: `console.vm-overview.vnc-url-plugin-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_overview.AppDetailView.get`
- 代码路径: `console/views/app_overview.py`
- 测试路径: `console/tests/vm_detail_view_test.py::AppVMDetailViewTests.test_get_builds_vm_vnc_url_from_plugin_fallback_when_query_param_missing`

### VM profile falls back to template root disk metadata

- Capability ID: `console.vm-profile.template-root-disk-fallback`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.get_vm_profile`
- 代码路径: `console/services/virtual_machine.py`
- 测试路径: `console/tests/virtual_machine_service_test.py::VirtualMachineServiceTests.test_get_vm_profile_falls_back_to_template_root_disk_metadata_when_asset_missing`

### update_check_app 为新建虚拟机根盘使用所选存储类型

- Capability ID: `console.vm-root-disk-selected-storage-type`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app.AppService.update_check_app`
- 代码路径: `console/services/app.py`
- 测试路径: `console/tests/vm_live_migration_storage_test.py::VMLiveMigrationStorageTests.test_update_check_app_uses_selected_storage_type_for_new_vm_root_disk`

### 虚拟机平台异常时禁止创建虚拟机组件

- Capability ID: `console.vm-run.platform-runtime-guard`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_create.vm_run.VMRunCreateView.post`
- 代码路径: `console/views/app_create/vm_run.py`
- 测试路径: `console/tests/vm_asset_instantiation_test.py::VMAssetInstantiationTests.test_vm_run_create_rejects_when_vm_plugin_not_running`

### 允许虚拟机使用任意访问模式的存储

- Capability ID: `console.vm-storage-any-access-mode`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.volume_service.AppVolumeService.build_vm_live_migration_volume_settings`
- 代码路径: `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/vm_live_migration_storage_test.py::VMLiveMigrationStorageTests`

### delete 允许异常状态虚拟机跳过运行中校验

- Capability ID: `console.vm-template-import.delete-abnormal-vm`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `workflow`
- 业务入口: `console.services.app_actions.app_manage.AppManageService.delete`
- 代码路径: `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/app_manage_test.py::AppManageVMRestoreDeleteTests.test_delete_allows_abnormal_vm_to_skip_running_guard`

### Allow deleting restoring VM components

- Capability ID: `console.vm-template-import.delete-restoring-vm`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_actions.app_manage.AppManageService.delete`
- 代码路径: `console/services/app_actions/app_manage.py`
- 测试路径: `console/tests/app_manage_test.py::AppManageVMRestoreDeleteTests`

### VM template import restore operation record exposes progress

- Capability ID: `console.vm-template-import.restore-operation-record`
- 状态: `active`
- 测试类型: `unit`
- 接口类型: `service_method`
- 业务入口: `console.services.app_actions.app_log.AppEventService.build_vm_restore_event`
- 代码路径: `console/services/app_actions/app_log.py`, `console/services/app.py`, `console/views/app_event.py`
- 测试路径: `console/tests/vm_profile_runtime_status_test.py::VMRestoreEventTests.test_build_vm_restore_event_exposes_progress_and_importer_logs`, `console/tests/vm_profile_runtime_status_test.py::VMRestoreEventTests.test_build_vm_restore_event_marks_success_after_import_finishes`

### 应用关联的团队不存在时返回404错误

- Capability ID: `openapi.app-service.team-not-found`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `openapi.services.app_service.AppService.get_app_services_and_status`
- 代码路径: `openapi/services/app_service.py`
- 测试路径: `console/tests/openapi_app_service_team_not_found_test.py::AppServiceTeamNotFoundTest`

### OpenAPI 创建第三方 api 组件时生成密钥

- Capability ID: `openapi.app.create-third-component-deploy-key`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `openapi.views.apps.apps.CreateThirdComponentView.post`
- 代码路径: `openapi/views/apps/apps.py`, `console/repositories/deploy_repo.py`
- 测试路径: `console/tests/openapi_third_component_deploy_repo_test.py::ThirdComponentDeployRepoTest.test_deploy_repo_is_the_singleton_not_the_module`

### OpenAPI 关闭团队全部应用

- Capability ID: `openapi.app.team-apps-close`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `openapi.views.apps.apps.TeamAppsCloseView.post`
- 代码路径: `openapi/views/apps/apps.py`
- 测试路径: `console/tests/openapi_team_apps_close_test.py::TeamAppsCloseTest.test_post_unpacks_three_return_values_from_batch_action`

### 团队未在该集群中初始化时返回409错误

- Capability ID: `openapi.base.team-not-initialized-in-region`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `openapi.views.base.TeamAPIView.initial`
- 代码路径: `openapi/views/base.py`, `openapi/views/exceptions.py`
- 测试路径: `console/tests/openapi_base_team_region_init_test.py::TeamAPIViewRegionInitTest`

### OpenAPI 企业组件状态总览

- Capability ID: `openapi.enterprise.service-overview`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `openapi.views.enterprise_view.ServiceOverview.get`
- 代码路径: `openapi/views/enterprise_view.py`, `console/services/service_overview.py`
- 测试路径: `console/tests/openapi_service_overview_import_test.py::ServiceOverviewImportTest.test_service_overview_singleton_is_resolvable`

### HTTP 策略高级配置服务层默认缺失 set_headers

- Capability ID: `openapi.service-config.domain-set-headers-service-default`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.domain_service.DomainService.update_http_rule_config`
- 代码路径: `console/services/app_config/domain_service.py`
- 测试路径: `console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_http_rule_config_defaults_missing_set_headers_in_service`

### OpenAPI 组件环境变量备注可省略

- Capability ID: `openapi.service-config.env-note-optional`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.env_service.AppEnvVarService.update_or_create_envs`
- 代码路径: `console/services/app_config/env_service.py`, `openapi/serializer/app_serializer.py`
- 测试路径: `console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_update_or_create_envs_defaults_missing_note`

### OpenAPI HTTP 网关 set_headers 可省略

- Capability ID: `openapi.service-config.http-set-headers-optional`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `openapi.serializer.gateway_serializer.HTTPConfiguration`
- 代码路径: `openapi/serializer/gateway_serializer.py`
- 测试路径: `console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_http_configuration_defaults_missing_set_headers`

### OpenAPI 组件端口别名可留空自动生成

- Capability ID: `openapi.service-config.port-alias-blank`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `openapi.serializer.app_serializer.ComponentPortReqSerializers`
- 代码路径: `openapi/serializer/app_serializer.py`
- 测试路径: `console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_component_port_serializer_allows_blank_alias_for_auto_generation`

### OpenAPI 开启组件外部端口时解析应用上下文

- Capability ID: `openapi.service-config.port-open-outer-app-context`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.port_service.AppPortService.manage_port`
- 代码路径: `console/services/app_config/port_service.py`
- 测试路径: `console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_manage_port_resolves_app_when_opening_outer_port`

### OpenAPI 参数校验错误不返回 traceback

- Capability ID: `openapi.service-config.validation-error-shape`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `package_function`
- 业务入口: `console.views.base.custom_exception_handler`
- 代码路径: `console/views/base.py`
- 测试路径: `console/tests/openapi_service_config_validation_test.py::OpenAPIServiceConfigValidationTest.test_validation_error_response_does_not_expose_traceback`

### OpenAPI 删除团队时正确透出业务异常

- Capability ID: `openapi.team.delete-error-propagation`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `openapi.views.team_view.TeamInfo.delete`
- 代码路径: `openapi/views/team_view.py`
- 测试路径: `console/tests/openapi_team_delete_except_test.py::TeamDeleteExceptTest.test_service_error_propagates_instead_of_typeerror`

### VM disk layout accepts container disk CD-ROM media

- Capability ID: `rainbond-console.vm-disks.container-disk-cdrom`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.validate_vm_disk_layout`
- 代码路径: `console/services/virtual_machine.py`
- 测试路径: `console/tests/vm_create_flow_regression_test.py::VMCreateFlowRegressionUnitTests.test_validate_vm_disk_layout_accepts_container_disk_cdrom`, `console/tests/vm_create_flow_regression_test.py::VMCreateFlowRegressionUnitTests.test_validate_vm_disk_layout_rejects_container_disk_without_image`

### 当 VM 运行时提示不完整时仍为 ISO 虚拟机磁盘列表补出安装光盘

- Capability ID: `rainbond-console.vm-disks.iso-installer-compat`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.list_vm_disks`
- 代码路径: `console/services/virtual_machine.py`
- 测试路径: `console/tests/vm_disk_installer_compat_test.py::VMInstallerMediaCompatUnitTests.test_get_vm_runtime_config_includes_boot_source_format`, `console/tests/vm_disk_installer_compat_test.py::VMInstallerMediaCompatUnitTests.test_list_vm_disks_falls_back_to_asset_format_for_legacy_iso_vm_without_runtime_hint`

### 虚拟机资产就绪需要 ready 状态与镜像地址

- Capability ID: `rainbond-console.vm-export.asset-ready-storage-status`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.is_vm_asset_ready`
- 代码路径: `console/services/virtual_machine.py`
- 测试路径: `console/tests/vm_create_flow_regression_test.py`

### resolve_vm_volume_path 为虚拟机热迁移分配唯一磁盘路径

- Capability ID: `rainbond-console.vm-live-migration-unique-disk-path`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.app_config.volume_service.AppVolumeService.resolve_vm_volume_path`
- 代码路径: `console/services/app_config/volume_service.py`
- 测试路径: `console/tests/vm_live_migration_storage_test.py::VMLiveMigrationStorageTests.test_resolve_vm_volume_path_allocates_unique_disk_suffix_for_duplicate_vm_device_path`, `console/tests/vm_live_migration_storage_test.py::VMLiveMigrationStorageTests.test_resolve_vm_volume_path_keeps_existing_path_when_editing_same_vm_device_type`

### 从现有磁盘资产创建虚拟机时复用已就绪运行时镜像

- Capability ID: `rainbond-console.vm-run.disk-asset-create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_create.vm_run.VMRunCreateView.post`
- 代码路径: `console/views/app_create/vm_run.py`, `console/services/virtual_machine.py`, `console/services/vm_boot_source.py`
- 测试路径: `console/tests/vm_asset_instantiation_test.py::VMAssetInstantiationTests::test_vm_run_create_from_existing_disk_asset_reuses_ready_runtime_image`, `console/tests/vm_asset_instantiation_test.py::VMAssetInstantiationTests::test_vm_run_create_uses_requested_format_for_suffixless_existing_disk_asset_import`

### resolve_vm_boot_mode 对 Windows ISO 忽略过期资产启动模式

- Capability ID: `rainbond-console.vm-run.vm-export-ignore-stale-boot-mode`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `service_method`
- 业务入口: `console.services.virtual_machine.VirtualMachineService.resolve_vm_boot_mode`
- 代码路径: `console/services/virtual_machine.py`
- 测试路径: `console/tests/vm_create_flow_regression_test.py`

### 虚拟机运行创建支持多磁盘资产实例化

- Capability ID: `rainbond-console.vm-run.vm-export-multi-disk-create`
- 状态: `active`
- 测试类型: `regression`
- 接口类型: `view_endpoint`
- 业务入口: `console.views.app_create.vm_run.VMRunCreateView.post`
- 代码路径: `console/views/app_create/vm_run.py`
- 测试路径: `console/tests/vm_asset_instantiation_test.py`
