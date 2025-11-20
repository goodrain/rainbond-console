# -*- coding: utf8 -*-
"""
KubeBlocks 相关服务
"""
import logging
from datetime import datetime

from django.db import transaction

from console.exception.main import ServiceHandleException
from console.repositories.deploy_repo import deploy_repo
from console.services.app import app_service
from console.services.app_actions import app_manage_service
from console.services.app_config.env_service import AppEnvVarService
from console.services.app_config.port_service import AppPortService
from console.services.group_service import GroupService
from console.repositories.group import group_repo
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class KubeBlocksService(object):

    def __init__(self):
        self.env_service = AppEnvVarService()
        self.port_service = AppPortService()
        self.group_service = GroupService()

    @transaction.atomic
    def create_complete_kubeblocks_component(self, tenant, user, region_name, creation_params):
        """
        一次性创建 KubeBlocks Component
        """
        new_service = None
        try:
            # 创建组件元数据和基础配置
            new_service = self._create_component_metadata(tenant, user, region_name, creation_params)

            # 创建KubeBlocks集群
            success, cluster_result = self._create_cluster(tenant, user, region_name, creation_params, new_service)
            if not success:
                logger.error("KubeBlocks集群创建失败，触发资源清理")
                self._cleanup_on_failure(new_service, tenant, region_name)
                return False, cluster_result, "KubeBlocks集群创建失败"

            # 更新组件的 k8s_component_name
            self._update_component_name(new_service, cluster_result)

            # 加入应用分组
            self._add_to_application_group(tenant, region_name, creation_params.get('group_id'), new_service.service_id)

            # 在Region中创建资源
            self._create_region_service(tenant, new_service, user.nick_name)

            connect_ctx = self._fetch_connection_info(
                region_name=region_name,
                service_id=new_service.service_id
            )

            # 配置连接信息（环境变量）
            self._add_database_env_vars(tenant, user, region_name, new_service, connect_ctx=connect_ctx)

            # 配置端口信息,传递数据库类型
            database_type = creation_params.get('database_type', '')
            self._configure_service_ports(tenant, user, region_name, new_service, connect_ctx=connect_ctx, database_type=database_type)

            # 构建部署组件
            deploy_result = self._deploy_component(tenant, new_service, user)

            # 创建部署关系记录
            deploy_repo.create_deploy_relation_by_service_id(service_id=new_service.service_id)

            # 构建返回数据（与标准组件部署完成后格式一致）
            result_data = self._build_success_response(new_service, deploy_result)

            return True, result_data, None

        except Exception as e:
            logger.exception(f"创建KubeBlocks组件失败: {str(e)}")

            # 清理资源
            if new_service:
                self._cleanup_on_failure(new_service, tenant, region_name)

            return False, None, str(e)

    def _create_component_metadata(self, tenant, user, region_name, params):
        """
        创建组件元数据
        """
        service_cname = params.get('service_cname', '').strip()
        k8s_component_name = params.get('k8s_component_name', '')
        arch = params.get('arch', 'amd64')

        # 调用现有的组件创建方法
        code, msg, new_service = app_service.create_kubeblocks_component(
            region=region_name,
            tenant=tenant,
            user=user,
            service_cname=service_cname,
            k8s_component_name=k8s_component_name,
            arch=arch
        )

        if code != 200:
            raise ServiceHandleException(msg=msg, msg_show=msg)

        return new_service

    def _create_cluster(self, tenant, user, region_name, params, kubeblocks_service):
        """
        创建 KubeBlocks 数据库集群

        Args:
            params (dict): 集群创建参数
            kubeblocks_service: 已创建的 kubeblocks_component
        """
        try:
            cluster_params = dict(params)
            cluster_params["k8s_component_name"] = kubeblocks_service.k8s_component_name

            is_valid, error_msg = self.validate_cluster_params(cluster_params)
            if not is_valid:
                logger.error(f"KubeBlocks 集群参数验证失败: {error_msg}")
                return False, None

            # 构建集群创建请求数据
            cluster_data = self._build_cluster_request(cluster_params, kubeblocks_service, tenant.namespace)

            # 调用 Region API 创建集群
            res, body = region_api.create_kubeblocks_cluster(region_name, cluster_data)

            if res.get("status") != 200:
                error_msg = f"KubeBlocks 集群创建失败: {body}"
                logger.error(error_msg)
                return False, None

            return True, body

        except Exception as e:
            logger.exception(f"创建 KubeBlocks 集群异常: {str(e)}")
            return False, None

    def validate_cluster_params(self, params):
        """
        验证集群创建参数
        """
        required_fields = {
            "cluster_name": "集群名称",
            "database_type": "数据库类型",
            "version": "数据库版本",
            "cpu": "CPU 配置",
            "memory": "内存配置",
            "storage_size": "存储大小"
        }

        optional_fields = {
            "group_id": {"type": [str, int], "desc": "应用分组 ID", "default": None},
            "app_name": {"type": str, "desc": "应用名称", "default": ""},
            "storage_class": {"type": str, "desc": "存储类名称", "default": ""},
            "backup_repo": {"type": str, "desc": "备份仓库名称", "default": ""},
            "k8s_component_name": {"type": str, "desc": "K8s组件名称", "default": ""},
            "arch": {"type": str, "desc": "架构类型", "default": "amd64"},
            "termination_policy": {"type": str, "desc": "删除策略", "default": "Delete"},
            "retention_period": {"type": str, "desc": "备份保留期", "default": "7d"},
            "backup_schedule": {"type": dict, "desc": "备份调度配置", "default": {}}
        }

        for field, desc in required_fields.items():
            value = params.get(field)
            if value is None or value == "":
                return False, f"{desc}不能为空"
            if not isinstance(value, str):
                return False, f"{desc}必须是字符串类型"
            params[field] = value.strip()
            if not params[field]:
                return False, f"{desc}不能只包含空格"

        for field, config in optional_fields.items():
            value = params.get(field)
            if value is not None:
                allowed_types = config["type"] if isinstance(config["type"], list) else [config["type"]]
                if not any(isinstance(value, t) for t in allowed_types):
                    type_names = [t.__name__ for t in allowed_types]
                    return False, f"{config['desc']}必须是{'/'.join(type_names)}类型"
                if isinstance(value, str):
                    params[field] = value.strip()
            else:
                params[field] = config.get("default")

        replicas = params.get("replicas", 1)
        try:
            replicas = int(replicas)
            if replicas < 1 or replicas > 100:
                return False, "副本数量必须在1-100之间"
        except (ValueError, TypeError):
            return False, "副本数量必须是有效的整数"
        params["replicas"] = replicas

        group_id = params.get("group_id")
        if group_id is not None:
            if isinstance(group_id, str):
                if group_id.strip() in ["", "-1"]:
                    params["group_id"] = None
                else:
                    try:
                        group_id = int(group_id.strip())
                        params["group_id"] = group_id if group_id > 0 else None
                    except ValueError:
                        return False, "应用分组 ID 必须是有效的数字"
            elif isinstance(group_id, int):
                params["group_id"] = group_id if group_id > 0 else None

        backup_schedule = params.get("backup_schedule", {})
        if backup_schedule:
            valid_frequencies = ["hourly", "daily", "weekly"]
            frequency = backup_schedule.get("frequency", "daily")
            if frequency not in valid_frequencies:
                return False, f"备份频率必须是 {', '.join(valid_frequencies)} 之一"

            try:
                hour = int(backup_schedule.get("hour", 2))
                if hour < 0 or hour > 23:
                    return False, "备份小时数必须在0-23之间"

                minute = int(backup_schedule.get("minute", 0))
                if minute < 0 or minute > 59:
                    return False, "备份分钟数必须在0-59之间"

                if frequency == "weekly":
                    weekday = int(backup_schedule.get("dayOfWeek", 1))
                    if weekday < 1 or weekday > 7:
                        return False, "备份星期数必须在1-7之间"

            except (ValueError, TypeError):
                return False, "备份时间参数必须是有效的数字"

        termination_policy = params.get("termination_policy", "Delete")
        valid_policies = ["Delete", "WipeOut"]  # 删除策略只支持 Delete 和 WipeOut
        if termination_policy not in valid_policies:
            return False, f"删除策略必须是 {', '.join(valid_policies)} 之一"

        # CPU 格式校验
        cpu = params["cpu"]
        if not self._is_valid_cpu(cpu):
            return False, "CPU 配置格式不正确"

        # 内存格式校验
        memory = params["memory"]
        if not self._is_valid_memory(memory):
            return False, "内存配置格式不正确"

        # 存储格式校验
        storage_size = params["storage_size"]
        if not self.is_valid_storage(storage_size):
            return False, "存储大小格式不正确"

        # 保留时间格式校验
        retention_period = params.get("retention_period", "7d")
        if not self.is_valid_retention_period(retention_period):
            return False, "备份保留期格式不正确"

        return True, ""

    def _is_valid_cpu(self, cpu):
        """验证 CPU 格式"""
        import re
        pattern = r'^\d+(\.\d+)?[m]?$'
        return bool(re.match(pattern, cpu))

    def _is_valid_memory(self, memory):
        """验证内存格式"""
        import re
        pattern = r'^\d+(\.\d+)?(Mi|Gi|Ti)$'
        return bool(re.match(pattern, memory))

    def is_valid_storage(self, storage):
        """验证存储格式"""
        import re
        pattern = r'^\d+(\.\d+)?(Mi|Gi|Ti)$'
        return bool(re.match(pattern, storage))

    def is_valid_retention_period(self, retention_period):
        """验证备份保留期格式"""
        import re
        pattern = r'^\d+[dwmy]$'
        return bool(re.match(pattern, retention_period))

    def _build_cluster_request(self, cluster_params, new_service, namespace):
        """
        构建创建 Cluster 的请求数据
        """
        cluster_data = {
            "name": cluster_params.get("k8s_component_name", "") or cluster_params["cluster_name"],
            "namespace": namespace,
            "type": cluster_params["database_type"],
            "version": cluster_params["version"],
            "cpu": cluster_params["cpu"],
            "memory": cluster_params["memory"],
            "storage": cluster_params["storage_size"],
            "replicas": cluster_params.get("replicas", 1),
            "storageClass": cluster_params.get("storage_class", ""),
            "backupRepo": cluster_params.get("backup_repo", ""),
            "terminationPolicy": cluster_params.get("termination_policy", "Delete"),
            "rbdService": {
                "service_id": new_service.service_id,
                "service_alias": new_service.service_alias
            }
        }

        backup_repo = cluster_params.get("backup_repo", "")
        if backup_repo and backup_repo.strip():
            backup_schedule = cluster_params.get("backup_schedule", {})
            schedule = {
                "frequency": backup_schedule.get("frequency", "daily"),
                "dayOfWeek": backup_schedule.get("dayOfWeek", 1),
                "hour": backup_schedule.get("hour", 2),
                "minute": backup_schedule.get("minute", 0)
            }
            cluster_data["schedule"] = schedule

        if backup_repo and backup_repo.strip():
            retention_period = cluster_params.get("retention_period", "7d")
            cluster_data["retentionPeriod"] = retention_period

        return cluster_data

    def _update_component_name(self, new_service, cluster_result):
        """
        从集群创建结果中更新组件的 k8s_component_name

        格式: {cluster_name}-{component_spec_name}
        例如: string-a0e0-mysql

        Args:
            new_service: 组件对象
            cluster_result: 集群创建结果数据
        """
        try:
            if not cluster_result or not isinstance(cluster_result, dict):
                logger.warning("集群创建结果无效或为空 %s", cluster_result)
                return

            bean = cluster_result.get('bean', {})
            metadata = bean.get('metadata', {})
            spec = bean.get('spec', {})

            # 提取并验证必要字段
            cluster_name = metadata.get('name', '').strip()
            component_specs = spec.get('componentSpecs', [])

            if not cluster_name or not component_specs:
                return

            # 获取并验证组件名称
            component_name = component_specs[0].get('name', '').strip()
            if not component_name:
                logger.warning(f"集群创建结果中未找到有效的组件规格名称: componentSpecs={component_specs}")
                return

            # 成功路径：更新组件名称
            new_k8s_component_name = f"{cluster_name}-{component_name}"
            new_service.k8s_component_name = new_k8s_component_name
            new_service.version = component_specs[0].get('serviceVersion', '').strip()
            new_service.create_status = "complete"
            new_service.action = True

            new_service.save()
        except Exception as e:
            raise ServiceHandleException(
                msg=f"failed to update k8s_component_name: {str(e)}",
                msg_show="更新 k8s_component_name 失败"
            )

    def _add_to_application_group(self, tenant, region_name, group_id, service_id):
        """
        将组件加入应用分组
        """
        try:
            GroupService.add_component_to_app(
                tenant=tenant,
                region_name=region_name,
                app_id=group_id,
                component_id=service_id
            )
        except Exception as e:
            raise ServiceHandleException(
                msg=f"failed to add component to app group: {str(e)}",
                msg_show="加入应用分组失败"
            )

    def _create_region_service(self, tenant, new_service, user_name):
        """在Region中创建服务资源"""
        try:
            result_service = app_service.create_region_service(
                tenant=tenant,
                service=new_service,
                user_name=user_name,
                do_deploy=False  # 先不部署，后续单独部署
            )
            return result_service
        except Exception as e:
            raise ServiceHandleException(
                msg=f"failed to create region service: {str(e)}",
                msg_show="Region资源创建失败"
            )

    def _fetch_connection_info(self, region_name, service_id, msg_show="获取连接信息失败"):
        """
        获取指定Cluster的连接信息
        """
        request_data = {
            "RBDService": {
                "service_id": service_id
            }
        }
        res, body = region_api.get_kubeblocks_connect_info(region_name=region_name, cluster_data=request_data)
        if res.get("status") != 200 or not isinstance(body, dict):
            status = res.get("status") if isinstance(res, dict) else "unknown"
            raise ServiceHandleException(
                msg=f"failed to get connection info, status code: {status}",
                msg_show=msg_show
            )
        bean = body.get("bean", {})
        if not isinstance(bean, dict):
            raise ServiceHandleException(
                msg="invalid connection info returned",
                msg_show=msg_show
            )
        return bean

    def _add_database_env_vars(self, tenant, user, region_name, service, connect_ctx=None):
        """
        为数据库组件添加环境变量
        """
        # 获取数据库连接信息
        connect_info = self._get_database_connect_info(service, region_name, connect_ctx=connect_ctx)

        if not connect_info.get("username") and not connect_info.get("password"):
            raise ServiceHandleException(
                msg="failed to get database connection info",
                msg_show="获取数据库连接信息失败"
            )

        # 添加数据库连接信息
        env_vars = [
            {
                "name": "Password",
                "attr_name": "DEFAULT_PASSWORD",
                "attr_value": connect_info.get("password", ""),
                "scope": "outer"
            },
            {
                "name": "Username",
                "attr_name": "DEFAULT_USERNAME",
                "attr_value": connect_info.get("username", "root"),
                "scope": "outer"
            }
        ]

        # 添加环境变量，失败时抛出异常
        for env_var in env_vars:
            if not env_var["attr_value"]:
                continue

            code, msg, env = self.env_service.add_service_env_var(
                tenant=tenant,
                service=service,
                container_port=0,
                name=env_var["name"],
                attr_name=env_var["attr_name"],
                attr_value=env_var["attr_value"],
                is_change=True,
                scope=env_var["scope"],
                user_name=user.get_username()
            )

            # 检查环境变量添加结果
            if code != 200 and code != 412:  # 412表示环境变量已存在，这是可接受的
                raise ServiceHandleException(
                    msg=f"failed to add env var {env_var['attr_name']}: {msg}",
                    msg_show="添加数据库环境变量失败",
                    status_code=code
                )

    def _get_database_connect_info(self, service, region_name, connect_ctx=None):
        """
        获取数据库连接信息
        """
        try:
            if connect_ctx is None:
                connect_ctx = self._fetch_connection_info(
                    region_name=region_name,
                    service_id=service.service_id,
                    msg_show="获取数据库连接信息失败"
                )
            elif not isinstance(connect_ctx, dict):
                raise ServiceHandleException(
                    msg="invalid connection info returned",
                    msg_show="获取数据库连接信息失败"
                )

            connect_list = connect_ctx.get("connect_infos", [])

            if connect_list and len(connect_list) > 0:
                connect_data = connect_list[0]
                return {
                    "username": connect_data.get("user", "root"),
                    "password": connect_data.get("password", "")
                }
            else:
                raise ServiceHandleException(
                    msg="KubeBlocks API returned empty connection info list",
                    msg_show="获取数据库连接信息为空"
                )

        except Exception as e:
            raise ServiceHandleException(
                msg=f"failed to call KubeBlocks API to get connection info: {str(e)}",
                msg_show="获取数据库连接信息异常"
            )

    def _configure_service_ports(self, tenant, user, region_name, service, connect_ctx=None, database_type=''):
        """配置服务端口"""
        if connect_ctx is None:
            connect_ctx = self._fetch_connection_info(
                region_name=region_name,
                service_id=service.service_id,
                msg_show="获取端口信息失败"
            )
        if not isinstance(connect_ctx, dict):
            raise ServiceHandleException(
                msg="invalid connection info returned",
                msg_show="端口信息无效"
            )
        port = connect_ctx.get("port")
        if not isinstance(port, int):
            raise ServiceHandleException(
                msg="invalid port info returned",
                msg_show="端口信息无效"
            )

        # 根据数据库类型设置端口别名
        port_alias = self._get_port_alias_by_database_type(database_type)
        protocol = "tcp"

        # 检查端口是否已存在
        existing_ports = self.port_service.get_service_ports(service)
        if not existing_ports:
            # 添加端口
            code, msg, port_data = self.port_service.add_service_port(
                tenant=tenant,
                service=service,
                container_port=port,
                protocol=protocol,
                port_alias=port_alias,
                is_inner_service=True,
                is_outer_service=True,
                k8s_service_name="",
                user_name=user.nick_name
            )

            if code != 200:
                logger.error(f"添加默认端口失败: {msg}")
                raise ServiceHandleException(
                    msg=f"failed to add default port: {msg}",
                    msg_show="端口配置失败",
                    status_code=code
                )

            # 开启对外服务
            self._enable_port_outer_service(
                tenant=tenant,
                service=service,
                region_name=region_name,
                port=port_data,
                user=user
            )

    def _get_port_alias_by_database_type(self, database_type):
        """
        根据数据库类型返回对应的端口别名

        Args:
            database_type: 数据库类型 (mysql, postgresql, redis, rabbitmq等)

        Returns:
            str: 端口别名
        """
        # 数据库类型到端口别名的映射
        database_type_lower = database_type.lower() if database_type else ''

        port_alias_mapping = {
            'mysql': 'MYSQL',
            'postgresql': 'POSTGRESQL',
            'redis': 'REDIS',
            'rabbitmq': 'RABBITMQ',
        }

        # 返回对应的别名,如果找不到则返回默认值 DB
        return port_alias_mapping.get(database_type_lower, 'DB')

    def _enable_port_outer_service(self, tenant, service, region_name, port, user):
        """
        为指定端口开启对外服务
        """
        try:
            app = group_repo.get_by_service_id(tenant.tenant_id, service.service_id)
            if app is None:
                raise ServiceHandleException(
                    msg=f"Application group not found for service_id={service.service_id}",
                    msg_show="未找到组件所属的应用分组"
                )

            code, msg, port_data = self.port_service.manage_port(
                tenant=tenant,
                service=service,
                region_name=region_name,
                container_port=port.container_port,
                action="open_outer",
                protocol=port.protocol,
                port_alias=port.port_alias,
                k8s_service_name="",
                user_name=user.nick_name,
                app=app
            )

            if code != 200:
                logger.error(f"开启对外服务失败: service={service.service_id}, port={port.container_port}, msg={msg}")
                raise ServiceHandleException(
                    msg=f"failed to open outer service: {msg}",
                    msg_show="开启对外服务失败",
                    status_code=code
                )

            # 同步端口状态到 Region
            updated_port = self.port_service.get_service_port_by_port(service, port.container_port)
            port_dict = updated_port.to_dict()

            self.port_service.update_service_port(
                tenant=tenant,
                region_name=region_name,
                service_alias=service.service_alias,
                body=[port_dict],
                user_name=user.nick_name
            )

        except ServiceHandleException:
            raise
        except Exception as e:
            logger.exception(f"开启端口对外服务失败: service={service.service_id}, port={port.container_port}, error={str(e)}")
            raise ServiceHandleException(
                msg=f"failed to enable port outer service: {str(e)}",
                msg_show="开启端口对外服务失败"
            )

    def _deploy_component(self, tenant, new_service, user):
        """构建部署组件"""
        try:
            # 设置架构亲和性（在部署前执行）
            from console.services.app_config.arch_service import arch_service
            arch_service.update_affinity_by_arch(
                new_service.arch, tenant, new_service.service_region, new_service
            )

            # 调用标准的部署流程
            deploy_result = app_manage_service.deploy(
                tenant=tenant,
                service=new_service,
                user=user,
                oauth_instance=None
            )
            return deploy_result
        except Exception as e:
            raise ServiceHandleException(
                msg=f"failed to deploy component: {str(e)}",
                msg_show="组件部署失败"
            )

    def _build_success_response(self, new_service, deploy_result):
        """构建成功响应数据（与标准组件部署完成后格式一致）"""
        # 获取最新的服务信息
        updated_service = TenantServiceInfo.objects.get(
            service_id=new_service.service_id,
            tenant_id=new_service.tenant_id
        )

        # 构建与app_build.py部署成功后相同格式的响应
        result_data = {
            "service_id": updated_service.service_id,
            "service_cname": updated_service.service_cname,
            "service_alias": updated_service.service_alias,
            "service_key": updated_service.service_key,
            "category": updated_service.category,
            "version": updated_service.version,
            "create_status": updated_service.create_status,
            "deploy_version": updated_service.deploy_version,
            "service_type": updated_service.service_type,
            "extend_method": updated_service.extend_method,
            "min_memory": updated_service.min_memory,
            "min_cpu": updated_service.min_cpu,
        }

        # 获取组件所属的应用分组ID（前端跳转必需）
        try:
            group_info = self.group_service.get_service_group_info(updated_service.service_id)
            if group_info:
                result_data["group_id"] = group_info.ID
            else:
                logger.warning(f"未找到组件 {updated_service.service_id} 的分组关系")
                result_data["group_id"] = None
        except Exception as e:
            logger.exception(f"获取组件分组信息失败: {e}")
            result_data["group_id"] = None

        # 如果有部署结果，添加部署相关信息
        if deploy_result:
            result_data.update({
                "status": "running",
                "status_cn": "运行中"
            })

        return result_data

    def _cleanup_on_failure(self, new_service, tenant, region_name):
        """失败时清理资源"""
        try:
            if new_service and new_service.service_id:
                # 清理KubeBlocks集群
                self.delete_kubeblocks_cluster([new_service.service_id], region_name)

                # 清理组件（如果已创建）
                if new_service.pk:
                    new_service.delete()
        except Exception as e:
            logger.exception(f"清理失败资源时出错: {str(e)}")

    def restore_component_from_backup(self, tenant, user, region_name, old_service, backup_name):
        """
        基于旧组件创建一个新的 KubeBlocks 组件，并从备份恢复到该新组件。

        流程：
        1) 创建新组件元数据（中文名追加 -restore）
        2) 使用新组件 service_id 调用 restore 接口
        3) 用返回的 new_service 更新新组件的 k8s_component_name，置为 complete
        4) 将新组件加入旧组件所属应用
        5) 在 Region 中创建新组件资源
        6) 复制旧组件端口到新组件（先端口后连接信息）
        7) 复制旧组件连接信息（环境变量）到新组件
        8) 部署并创建部署关系
        """
        new_service = None
        try:
            # 创建新组件元数据 {service_cname}-restore
            restore_cname = (old_service.service_cname or "").strip() + "-restore"
            if len(restore_cname) > 100:
                restore_cname = restore_cname[:100]

            code, msg, new_service = app_service.create_kubeblocks_component(
                region=region_name,
                tenant=tenant,
                user=user,
                service_cname=restore_cname,
                k8s_component_name="",
                arch=getattr(old_service, 'arch', 'amd64') or 'amd64'
            )
            if code != 200 or not new_service:
                return 500, {"msg_show": msg or "创建新组件失败"}

            # 将备份恢复到新组件
            status_code, region_restore_data = self.restore_cluster_from_backup(region_name, old_service, new_service,
                                                                                backup_name)
            if status_code != 200:
                msg_show = region_restore_data.get("msg_show", "恢复失败") if isinstance(region_restore_data,
                                                                                         dict) else "恢复失败"
                raise ServiceHandleException(
                    msg="restore from backup failed",
                    msg_show=msg_show
                )

            # 更新新组件 k8s_component_name 与状态
            if not isinstance(region_restore_data, dict):
                region_restore_data = {}
            bean = region_restore_data.setdefault('bean', {})
            new_k8s_name = bean.get('new_service')
            if isinstance(new_k8s_name, str) and new_k8s_name:
                new_service.k8s_component_name = new_k8s_name
            new_service.create_status = "complete"
            new_service.action = True
            new_service.save()

            # 将新组件加入旧组件所属 group(应用)
            group_info = self.group_service.get_service_group_info(old_service.service_id)
            group_id = group_info.ID if group_info else None
            self._add_to_application_group(tenant, region_name, group_id, new_service.service_id)

            self._create_region_service(tenant, new_service, user.nick_name)

            # 复制端口
            old_ports = self.port_service.get_service_ports(old_service) or []
            for p in old_ports:
                try:
                    code, msg, new_port = self.port_service.add_service_port(
                        tenant=tenant,
                        service=new_service,
                        container_port=int(p.container_port),
                        protocol=p.protocol,
                        port_alias=p.port_alias,
                        is_inner_service=bool(p.is_inner_service),
                        is_outer_service=bool(p.is_outer_service),
                        user_name=user.nick_name
                    )

                    if code != 200:
                        logger.error(f"复制端口失败: new={new_service.service_id}, port={p.container_port}, msg={msg}")
                        raise ServiceHandleException(msg="copy port failed", msg_show="复制端口失败")

                    if p.is_outer_service:
                        self._enable_port_outer_service(
                            tenant=tenant,
                            service=new_service,
                            region_name=region_name,
                            port=new_port,
                            user=user
                        )

                except Exception as e:
                    logger.exception("复制端口失败: new=%s old=%s port=%s error=%s",
                                     new_service.service_id, old_service.service_id, p.container_port, str(e))
                    raise ServiceHandleException(msg="copy port failed", msg_show="复制端口失败")

            old_envs = self.env_service.get_env_var(old_service) or []
            for env in old_envs:
                try:
                    if getattr(env, 'container_port', 0):
                        continue
                    self.env_service.add_service_env_var(
                        tenant=tenant,
                        service=new_service,
                        container_port=0,
                        name=env.name,
                        attr_name=env.attr_name,
                        attr_value=env.attr_value,
                        is_change=env.is_change,
                        scope=env.scope,
                        user_name=user.nick_name
                    )
                except Exception as e:
                    logger.exception("复制环境变量失败: new=%s old=%s env=%s error=%s",
                                     new_service.service_id, old_service.service_id, env.attr_name, str(e))
                    raise ServiceHandleException(msg="copy env var failed", msg_show="复制环境变量失败")

            self._deploy_component(tenant, new_service, user)
            deploy_repo.create_deploy_relation_by_service_id(service_id=new_service.service_id)

            # 构建返回结果
            bean = region_restore_data.setdefault('bean', {})
            bean['service_alias'] = new_service.service_alias
            bean['service_id'] = new_service.service_id

            group_info = self.group_service.get_service_group_info(new_service.service_id)
            bean['group_id'] = group_info.ID

            return 200, region_restore_data

        except Exception as e:
            logger.exception("从备份恢复到新组件失败: %s", str(e))
            # 删除新建的 cluster 与 kubeblocks component
            try:
                if new_service and getattr(new_service, 'service_id', None):
                    self.delete_kubeblocks_cluster([new_service.service_id], region_name)
                    try:
                        new_service.delete()
                    except Exception:
                        pass
            except Exception:
                logger.exception("回滚失败")
            return 500, {"msg_show": str(e) or "恢复失败"}

    def restore_cluster_from_backup(self, region_name, old_service, new_service, backup_name):
        """
        从备份中恢复 KubeBlocks Cluster
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}

        if not (old_service and old_service.service_id and new_service and new_service.service_id):
            return 400, {"msg_show": "组件信息无效"}

        if not backup_name or not backup_name.strip():
            return 400, {"msg_show": "备份名称不能为空"}

        try:
            # 修复参数顺序：传递完整的三个参数
            res, body = region_api.restore_cluster_from_backup(
                region_name,
                old_service.service_id,
                new_service.service_id,
                backup_name
            )
            status_code = res.get("status", 500)

            if status_code == 200:
                return 200, body
            else:
                msg_show = body.get("msg_show", "恢复失败") if isinstance(body, dict) else "恢复失败"
                logger.error(
                    f"KubeBlocks 集群恢复失败: service_id={old_service.service_id}, backup={backup_name}, status={status_code}, msg={msg_show}")
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception(
                f"KubeBlocks 集群恢复异常: service_id={old_service.service_id}, backup={backup_name}, 错误={str(e)}")
            return 500, {"msg_show": f"恢复操作异常: {str(e)}"}

    def get_backup_list(self, region_name, service_id, page=None, page_size=None):
        """
        获取 KubeBlocks Cluster 的备份列表
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}

        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空"}

        try:
            res, body = region_api.get_kubeblocks_backup_list(region_name, service_id, page, page_size)
            status_code = res.get("status", 500)

            if status_code == 200:
                return 200, body
            else:
                msg_show = body.get("msg_show", "获取备份列表失败") if isinstance(body, dict) else "获取备份列表失败"
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception("获取备份列表异常: service_id=%s, region=%s, 错误=%s",
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"请求异常: {str(e)}"}

    def create_manual_backup(self, region_name, service_id):
        """
        创建 KubeBlocks Cluster 的手动备份
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}

        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空"}

        try:
            res, data = region_api.create_kubeblocks_manual_backup(region_name, service_id)
            status_code = res.get('status', 500)

            if status_code == 200:
                return 200, {"msg_show": "手动备份已启动", "bean": data.get('bean') if isinstance(data, dict) else data}
            else:
                msg_show = data.get('msg_show', '手动备份启动失败') if isinstance(data, dict) else '手动备份启动失败'
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception("创建手动备份异常: service_id=%s, region=%s, 错误=%s",
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"请求异常: {str(e)}"}

    def delete_backups(self, region_name, service_id, backups):
        """
        删除 KubeBlocks Cluster 的备份
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}

        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空"}

        if backups is not None and not isinstance(backups, list):
            return 400, {"msg_show": "参数 backups 必须为数组"}

        try:
            res, data = region_api.delete_kubeblocks_backups(region_name, service_id, backups)
            status_code = res.get('status', 500)

            if status_code == 200:
                deleted_list = data.get('list', []) if isinstance(data, dict) else []
                return 200, {"msg_show": "备份删除成功", "list": deleted_list}
            else:
                msg_show = data.get('msg_show', '备份删除失败') if isinstance(data, dict) else '备份删除失败'
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception("删除备份异常: service_id=%s, region=%s, 错误=%s",
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"请求异常: {str(e)}"}

    def update_backup_config(self, region_name, service_id, backup_config):
        """
        更新 KubeBlocks Cluster 的备份配置
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}

        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空"}

        if not isinstance(backup_config, dict):
            return 400, {"msg_show": "参数必须为 JSON 对象"}

        try:
            body = dict(backup_config)
            if not body.get('rbdService'):
                body['rbdService'] = {'service_id': service_id}

            res, data = region_api.update_kubeblocks_backup_config(region_name, service_id, body)
            status_code = res.get('status', 500)

            if status_code == 200:
                return 200, {"msg_show": "备份配置更新成功",
                             "bean": data.get('bean') if isinstance(data, dict) else data}
            else:
                msg_show = data.get('msg_show', '备份配置更新失败') if isinstance(data, dict) else '备份配置更新失败'
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception("更新备份配置异常: service_id=%s, region=%s, 错误=%s",
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"请求异常: {str(e)}"}

    def get_cluster_detail(self, region_name, service_id):
        """
        获取 KubeBlocks Cluster 详情
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}

        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空"}

        try:
            res, body = region_api.get_kubeblocks_cluster_detail(region_name, service_id)
            status_code = res.get("status", 500)

            if status_code == 200:
                bean = body.get("bean", {})
                self._sync_to_rainbond(service_id, bean)
                return 200, {"msg_show": "查询成功", "bean": bean}
            else:
                msg_show = body.get("msg_show", "查询失败") if isinstance(body, dict) else "查询失败"
                logger.error(f"查询 KubeBlocks Cluster 详情失败: status={status_code}, msg={msg_show}")
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception(f"查询 KubeBlocks Cluster 详情异常: service_id={service_id}, region={region_name}, 错误={str(e)}")
            return 500, {"msg_show": f"后端服务异常: {str(e)}"}

    def _sync_to_rainbond(self, service_id, cluster_detail_bean):
        """
        同步 KubeBlocks Cluster 资源信息到 Rainbond 组件,
        仅在资源配置发生变化时更新数据库
        """
        try:
            service = TenantServiceInfo.objects.filter(service_id=service_id).first()
            if not service:
                return

            resource_info = cluster_detail_bean.get("resource", {})
            if not resource_info:
                return

            memory = resource_info.get("memory", 0)
            cpu = resource_info.get("cpu", 0)

            # 从 basic.replicas 数组的长度生成副本数
            # 处理多 Component Cluster
            basic_info = cluster_detail_bean.get("basic", {})
            replicas_list = basic_info.get("replicas", [])
            replicas = len(replicas_list) if replicas_list else 1

            memory = int(memory) if memory else 0
            cpu = int(cpu) if cpu else 0
            replicas = int(replicas) if replicas else 1

            has_changes = False

            if service.min_memory != memory:
                service.min_memory = memory
                has_changes = True

            if service.min_cpu != cpu:
                service.min_cpu = cpu
                has_changes = True

            if service.min_node != replicas:
                service.min_node = replicas
                has_changes = True

            if has_changes:
                service.save(update_fields=['min_memory', 'min_cpu', 'min_node'])

        except Exception as e:
            logger.exception(f"同步 KubeBlocks 资源到 Rainbond 失败: service_id={service_id}, 错误={str(e)}")

    def expand_cluster(self, region_name, service_id, expansion_data):
        """
        KubeBlocks Cluster 伸缩操作
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}

        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空"}

        if not isinstance(expansion_data, dict):
            return 400, {"msg_show": "伸缩配置数据格式错误"}

        try:
            scale_body = dict(expansion_data)
            if not scale_body.get('rbdService'):
                scale_body['rbdService'] = {'service_id': service_id}

            res, body = region_api.expansion_kubeblocks_cluster(region_name, service_id, scale_body)
            status_code = res.get('status', 500)

            if status_code == 200:
                return 200, {"msg_show": "伸缩成功", "bean": body.get('bean') if isinstance(body, dict) else body}
            else:
                msg_show = body.get('msg_show', '伸缩失败') if isinstance(body, dict) else '伸缩失败'
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception("集群伸缩异常: service_id=%s, region=%s, 错误=%s",
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"请求异常: {str(e)}"}

    def manage_cluster_status(self, service_or_ids, region_name, oauth_instance, operation):
        """
        管理 KubeBlocks 集群状态

        Args:
            service_or_ids: service 对象(单个) 或 service_ids 列表(批量)
        """
        # 支持单个 service 对象或批量 service_ids
        if isinstance(service_or_ids, list):
            service_ids = service_or_ids
        else:
            service_ids = [service_or_ids.service_id]

        res, body = region_api.manage_cluster_status(region_name, service_ids, operation)
        status_code = 500
        message = ""
        try:
            if isinstance(res, dict):
                status_code = res.get("status", 500)
            else:
                # 兜底：支持可能的对象属性
                status_code = getattr(res, "status", 500)

            if isinstance(body, dict):
                message = body.get("msg") or body.get("message") or ""
        except Exception as e:
            logger.exception(f"解析 KubeBlocks manage_cluster_status 响应异常: {e}")
        return status_code, message

    def delete_kubeblocks_cluster(self, service_ids, region_name):
        """
        删除 KubeBlocks 集群

        通过删除与 kubeblocks_component 关联的数据库集群
        静默处理
        """
        if not service_ids:
            logger.debug("delete_kubeblocks_cluster 调用时 service_ids 为空，跳过")
            return

        try:
            delete_data = {
                "serviceIDs": service_ids
            }

            res, body = region_api.delete_kubeblocks_cluster(region_name, delete_data)

            if res.get("status") != 200:
                status_code = res.get("status", 500)
                logger.error("删除 KubeBlocks 集群 API 调用返回非 200 状态: status=%s, service_ids=%s",
                             status_code, str(service_ids))

        except Exception as e:
            logger.exception("删除 KubeBlocks 集群发生异常: service_ids=%s, region=%s, 错误=%s",
                             str(service_ids), region_name, str(e))

    def get_kubeblocks_service_status(self, region_name, service_id, cluster_detail=None):
        """
        获取 KubeBlocks 组件状态信息

        Args:
            service_id (str): 组件ID
            cluster_detail (dict, optional): cluster detail

        Returns:
            dict: 包含 status, status_cn, disabledAction, activeAction, start_time 的状态映射
                 失败时返回 None
        """
        try:
            if cluster_detail is None:
                status_code, response = self.get_cluster_detail(region_name, service_id)

                if status_code != 200:
                    if status_code == 503:
                        logger.warning(f"KubeBlocks 服务不可用: status={status_code}, service_id={service_id}")
                    else:
                        logger.warning(f"获取 KubeBlocks 集群详情失败: status={status_code}, service_id={service_id}")
                    return None

                bean = response.get("bean", {})
            else:
                bean = cluster_detail
            basic_info = bean.get("basic", {})
            status_info = basic_info.get("status", {})

            # 从状态信息字典中提取实际的状态字符串
            if isinstance(status_info, dict):
                kubeblocks_status = status_info.get("status", "")
                start_time = status_info.get("start_time", "")
            else:
                # 如果是字符串则直接使用
                kubeblocks_status = status_info
                start_time = ""

            if not kubeblocks_status:
                logger.warning(f"KubeBlocks Cluster 状态为空: service_id={service_id}")
                return None

            # 映射 KubeBlocks 状态到 Rainbond 状态
            status_mapping = self._get_kubeblocks_status_map(kubeblocks_status)

            # 构建返回的状态映射
            status_info_map = {
                "status": status_mapping["rainbond_status"],
                "status_cn": status_mapping["status_cn"],
                "disabledAction": status_mapping["disabledAction"],
                "activeAction": status_mapping["activeAction"],
                "start_time": start_time  # 使用实际的启动时间
            }

            return status_info_map

        except Exception as e:
            logger.exception(
                f"获取 KubeBlocks 组件状态异常: service_id={service_id}, region={region_name}, 错误={str(e)}")
            return None

    def get_kubeblocks_resource_info(self, region_name, service_id, cluster_detail=None):
        """
        获取 KubeBlocks 组件的资源信息

        Args:
            service_id (str): 组件ID
            cluster_detail (dict, optional): cluster detail

        Returns:
            dict: {"used_mem": 内存消耗(MB), "used_cpu": CPU消耗}
        """
        try:
            if cluster_detail is None:
                status_code, response = self.get_cluster_detail(region_name, service_id)

                if status_code != 200:
                    logger.warning(f"获取 KubeBlocks 集群详情失败: status={status_code}, service_id={service_id}")
                    return {"used_mem": 0, "used_cpu": 0}

                bean = response.get("bean", {})
            else:
                bean = cluster_detail
            resource_info = bean.get("resource", {})

            # 提取资源信息并转换单位
            memory_mb = resource_info.get("memory", 0)  # MB
            cpu_cores = resource_info.get("cpu", 0)  # millicores

            # CPU 单位转换：millicores -> cores
            cpu_cores = cpu_cores / 1000.0 if cpu_cores else 0

            # 副本数
            replicas = resource_info.get("replicas", 1)

            # 计算总资源（分配资源 = 单实例资源 × 副本数）
            total_memory = memory_mb * replicas
            total_cpu = cpu_cores * replicas

            return {
                "used_mem": int(total_memory),  # 使用分配的内存作为 used_mem
                "used_cpu": round(total_cpu, 2)
            }

        except Exception as e:
            logger.exception(
                f"获取 KubeBlocks 组件资源信息异常: service_id={service_id}, region={region_name}, 错误={str(e)}")
            return {"used_mem": 0, "used_cpu": 0}

    def get_kubeblocks_components_info(self, region_name, service_ids):
        """
        批量获取 KubeBlocks 组件的状态和资源信息

        Args:
            service_ids (list): 组件ID列表
        """
        result = {}

        for service_id in service_ids:
            try:
                status_code, response = self.get_cluster_detail(region_name, service_id)

                if status_code != 200:
                    logger.warning(f"获取集群详情失败: service_id={service_id}, status={status_code}")
                    result[service_id] = {
                        "status": "failure",
                        "status_cn": "获取状态失败",
                        "used_mem": 0
                    }
                    continue

                cluster_detail = response.get("bean", {})

                kb_status = self.get_kubeblocks_service_status(
                    region_name, service_id, cluster_detail=cluster_detail)
                kb_resource = self.get_kubeblocks_resource_info(
                    region_name, service_id, cluster_detail=cluster_detail)

                result[service_id] = {
                    "status": kb_status.get("status", "failure") if kb_status else "failure",
                    "status_cn": kb_status.get("status_cn", "获取状态失败") if kb_status else "获取状态失败",
                    "used_mem": kb_resource.get("used_mem", 0) if kb_resource else 0
                }

            except Exception as e:
                logger.exception(f"获取 KubeBlocks 组件 {service_id} 信息失败: {str(e)}")
                result[service_id] = {
                    "status": "failure",
                    "status_cn": "获取状态失败",
                    "used_mem": 0
                }

        return result

    def _get_kubeblocks_status_map(self, kubeblocks_status):
        """
        KubeBlocks 状态到 Rainbond 状态映射
        """
        normalized_status = kubeblocks_status.lower() if kubeblocks_status else ""

        status_mapping = {
            "creating": {
                "rainbond_status": "creating",
                "status_cn": "创建中",
                "disabledAction": ['restart', 'stop', 'reboot'],
                "activeAction": [],
            },
            "running": {
                "rainbond_status": "running",
                "status_cn": "运行中",
                "disabledAction": ['restart'],
                "activeAction": ['stop', 'reboot'],
            },
            "updating": {
                "rainbond_status": "upgrade",
                "status_cn": "升级中",
                "disabledAction": ['restart', 'stop'],
                "activeAction": ['reboot'],
            },
            "stopping": {
                "rainbond_status": "stopping",
                "status_cn": "关闭中",
                "disabledAction": ['restart', 'stop', 'reboot'],
                "activeAction": [],
            },
            "stopped": {
                "rainbond_status": "closed",
                "status_cn": "已关闭",
                "disabledAction": ['stop', 'reboot'],
                "activeAction": ['restart'],
            },
            "deleting": {
                "rainbond_status": "stopping",
                "status_cn": "删除中",
                "disabledAction": ['restart', 'stop', 'reboot'],
                "activeAction": [],
            },
            "failed": {
                "rainbond_status": "failure",
                "status_cn": "未知",
                "disabledAction": ['restart'],
                "activeAction": ['stop', 'reboot'],
            },
            "abnormal": {
                "rainbond_status": "abnormal",
                "status_cn": "运行异常",
                "disabledAction": ['restart'],
                "activeAction": ['stop', 'reboot'],
            }
        }

        return status_mapping.get(normalized_status, {
            "rainbond_status": "unKnow",
            "status_cn": "未知",
            "disabledAction": ['restart', 'reboot'],
            "activeAction": ['stop'],
        })

    def get_cluster_events(self, region_name, service_id, tenant, service, page, page_size):
        """
        获取 KubeBlocks 集群事件列表
        """
        try:
            res, body = region_api.get_kubeblocks_cluster_events(region_name, service_id, page, page_size)
            status_code = res.get('status', 500) if isinstance(res, dict) else getattr(res, 'status', 500)

            if status_code == 200:
                events = body.get('list', []) or []
                total = body.get('number', 0) or 0

                normalized_events = self.normalize_kb_events(events, tenant, service)
                has_next = page * page_size < total

                return normalized_events, int(total), has_next
            else:
                return [], 0, False
        except Exception as e:
            logger.exception("获取 KubeBlocks 事件异常: service_id=%s, region=%s, 错误=%s", service_id, region_name,
                             str(e))
            return [], 0, False

    def merge_region_and_kb_events(self, target, target_id, tenant, region_name, service, page, page_size):
        """
        合并 Region event 和 KubeBlocks event
        """
        from console.services.app_actions import event_service
        from www.models.main import TenantServiceInfo
        import json

        window = page * page_size

        try:
            # 获取 Region 事件
            region_events, region_total, _ = event_service.get_target_events(
                target, target_id, tenant, region_name, page, window
            )

            # 获取 KB 事件（格式与 Region 事件一致）
            kb_events, kb_total, _ = self.get_cluster_events(
                region_name, target_id, tenant, service, page, window
            )

            merged_map = {}
            for ev in (region_events or []):
                eid = ev.get('event_id')
                if eid and eid not in merged_map:
                    merged_map[eid] = ev
            for ev in (kb_events or []):
                eid = ev.get('event_id')
                if eid and eid not in merged_map:
                    merged_map[eid] = ev

            merged = list(merged_map.values())
            merged.sort(key=lambda x: (x.get('create_time', ''), x.get('event_id', '')), reverse=True)
            start = (page - 1) * page_size
            end = page * page_size
            page_list = merged[start:end]
            total = int(region_total) + int(kb_total)
            has_next = end < total

            for event in page_list:
                if event.get("opt_type") == "INITIATING":
                    msg = event.get("message", "")
                    alias = msg.split(",") if msg else []
                    relys = []
                    for ali in alias:
                        service_obj = TenantServiceInfo.objects.filter(
                            service_alias=ali, tenant_id=tenant.tenant_id
                        ).first()
                        if service_obj:
                            relys.append({
                                "service_cname": service_obj.service_cname,
                                "serivce_alias": service_obj.service_alias,
                            })
                    if relys:
                        event["Message"] = "依赖的其他组件暂未运行 {0}".format(json.dumps(relys, ensure_ascii=False))

            return page_list, total, has_next

        except Exception as e:
            logger.exception(f"合并 Region 和 KubeBlocks 事件失败: {e}")
            raise

    def normalize_kb_events(self, events, tenant, service):
        """
        将 KB 事件补齐为 UI/Console 统一结构（仅补齐必要字段）

        填充字段:
          - target: 'service'
          - target_id: service.service_id
          - tenant_id: tenant.tenant_id
          - user_name: 缺省 'system'
          - syn_type: 1 （KB 暂不提供详情日志）
        """
        normalized = []
        if not events:
            return normalized

        def _kb_time_to_local_rfc3339(tstr):
            """
            仅转换 KB 的时间到本地时区 RFC3339(+HH:MM) 字符串。
            """
            try:
                if not isinstance(tstr, str) or not tstr:
                    return tstr
                s = tstr.strip()
                # 1) Z -> +0000
                if s.endswith('Z'):
                    s = s[:-1] + '+0000'
                # 2) +08:00 -> +0800 ； -05:30 -> -0530
                elif len(s) >= 6 and (s[-6] == '+' or s[-6] == '-') and s[-3] == ':':
                    s = s[:-3] + s[-2:]

                dt = None
                for fmt in ('%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z'):
                    try:
                        dt = datetime.strptime(s, fmt)
                        break
                    except Exception:
                        dt = None
                if dt is None:
                    return tstr

                local_tz = datetime.now().astimezone().tzinfo
                dt_local = dt.astimezone(local_tz).replace(microsecond=0)
                return dt_local.isoformat()
            except Exception:
                return tstr

        for ev in events:
            if not isinstance(ev, dict):
                continue
            item = {}
            # 保留已有字段
            for key in ['event_id', 'opt_type', 'status', 'final_status', 'message', 'reason', 'create_time',
                        'end_time']:
                if key in ev:
                    val = ev.get(key)
                    if key in ('create_time', 'end_time'):
                        item[key] = _kb_time_to_local_rfc3339(val)
                    else:
                        item[key] = val
            # 补齐字段
            item['target'] = 'service'
            try:
                item['target_id'] = service.service_id
            except Exception:
                item['target_id'] = ''
            try:
                item['tenant_id'] = tenant.tenant_id
            except Exception:
                item['tenant_id'] = ''
            ev_user = ev.get('user_name')
            if isinstance(ev_user, str) and ev_user:
                item['user_name'] = ev_user
            item['syn_type'] = 1
            normalized.append(item)
        return normalized

    def get_cluster_parameters(self, region_name, service_id, page=1, page_size=20, keyword=None):
        """
        分页获取 KubeBlocks 数据库参数列表
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}

        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空"}

        try:
            # 参数校验和默认值设置
            try:
                page = int(page) if page else 1
                page = max(1, page)  # 页码最小为1
            except (ValueError, TypeError):
                page = 1

            try:
                page_size = int(page_size) if page_size else 20
                page_size = max(1, min(page_size, 100))  # 限制在1-100之间
            except (ValueError, TypeError):
                page_size = 20

            # 调用Region API
            res, body = region_api.get_kubeblocks_cluster_parameters(
                region_name, service_id, page, page_size, keyword
            )
            status_code = res.get("status", 500)

            if status_code == 200:
                return 200, body  # 透传原始数据
            elif status_code == 404:
                return 404, {"msg_show": "集群不存在"}
            elif status_code == 403:
                return 403, {"msg_show": "无权限"}
            else:
                msg_show = body.get("msg_show", "获取参数失败") if isinstance(body, dict) else "获取参数失败"
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception("获取KubeBlocks集群参数异常: service_id=%s, region=%s, 错误=%s",
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"请求异常: {str(e)}"}

    def update_cluster_parameters(self, region_name, service_id, body):
        """
        批量更新 KubeBlocks 数据库参数
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}

        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空"}

        if not isinstance(body, dict):
            return 400, {"msg_show": "请求体必须为JSON对象"}

        try:
            # 调用Region API进行更新
            res, response_body = region_api.update_kubeblocks_cluster_parameters(
                region_name, service_id, body
            )
            status_code = res.get("status", 500)

            if status_code == 200:
                return 200, response_body  # 透传原始数据，包含applied/invalids
            elif status_code == 404:
                return 404, {"msg_show": "集群不存在"}
            elif status_code == 403:
                return 403, {"msg_show": "无权限"}
            else:
                msg_show = response_body.get("msg_show", "更新参数失败") if isinstance(response_body,
                                                                                       dict) else "更新参数失败"
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception("更新KubeBlocks集群参数异常: service_id=%s, region=%s, 错误=%s",
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"请求异常: {str(e)}"}

    def get_supported_databases(self, region_name):
        """
        获取指定区域下 KubeBlocks 支持的数据库类型列表
        """
        try:
            res, body = region_api.get_kubeblocks_supported_databases(region_name)
            status_code = res.get("status", 500)
            if status_code == 200:
                return 200, {"list": body.get("list", [])}
            else:
                return status_code, {"list": []}
        except Exception as e:
            logger.exception(f"获取数据库类型列表异常: {str(e)}")
            return 500, {"list": []}

    def get_storage_classes(self, region_name):
        """
        获取指定区域下 KubeBlocks StorageClass 列表
        """
        try:
            res, body = region_api.get_kubeblocks_storage_classes(region_name)
            status_code = res.get("status", 500)
            if status_code == 200:
                return 200, {"list": body.get("list", [])}
            else:
                return status_code, {"list": []}
        except Exception as e:
            logger.exception(f"获取存储类列表异常: {str(e)}")
            return 500, {"list": []}

    def get_backup_repos(self, region_name):
        """
        获取指定区域下 KubeBlocks BackupRepo 列表
        """
        try:
            res, body = region_api.get_kubeblocks_backup_repos(region_name)
            status_code = res.get("status", 500)
            if status_code == 200:
                return 200, {"list": body.get("list", [])}
            else:
                return status_code, {"list": []}
        except Exception as e:
            logger.exception(f"获取备份仓库列表异常: {str(e)}")
            return 500, {"list": []}


kubeblocks_service = KubeBlocksService()
