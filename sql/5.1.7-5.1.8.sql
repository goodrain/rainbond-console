-- 权限组
update console.tenant_permission_group set group_name = '第三方组件相关' where group_name = '三方服务相关';

-- 应用信息
update console.tenant_user_permission set per_info = '应用管理' where codename = 'manage_group';
update console.tenant_user_permission set per_info = '应用分享' where codename = 'share_service';

-- 组件信息
update console.tenant_user_permission set per_info = '查看组件信息' where codename = 'view_service';
update console.tenant_user_permission set per_info = '部署组件' where codename = 'deploy_service';
update console.tenant_user_permission set per_info = '创建组件' where codename = 'create_service';
update console.tenant_user_permission set per_info = '删除组件' where codename = 'delete_service';
update console.tenant_user_permission set per_info = '关闭组件' where codename = 'stop_service';
update console.tenant_user_permission set per_info = '启动组件' where codename = 'start_service';
update console.tenant_user_permission set per_info = '重启组件' where codename = 'restart_service';
update console.tenant_user_permission set per_info = '回滚组件' where codename = 'rollback_service';
update console.tenant_user_permission set per_info = '组件容器管理' where codename = 'manage_service_container';
update console.tenant_user_permission set per_info = '组件伸缩管理' where codename = 'manage_service_extend';
update console.tenant_user_permission set per_info = '组件配置管理' where codename = 'manage_service_config';
update console.tenant_user_permission set per_info = '组件扩展管理' where codename = 'manage_service_plugin';
update console.tenant_user_permission set per_info = '组件权限设置' where codename = 'manage_service_member_perms';

-- 第三方组件
update console.tenant_user_permission set per_info = '创建第三方组件' where codename = 'create_three_service';
alter table console.console_sys_config modify `value` varchar(4096);