# -*- coding: utf8 -*-
"""
KubeBlocks 相关服务
"""
import logging
from datetime import datetime, timezone
from django.db import transaction

from console.services.app_config.env_service import AppEnvVarService
from console.services.app_config.port_service import AppPortService
from console.services.group_service import GroupService
from console.services.app import app_service
from console.services.app_actions import app_manage_service
from www.apiclient.regionapi import RegionInvokeApi
from console.exception.main import ServiceHandleException
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
        一站式创建 KubeBlocks 组件的完整流程
        
        Args:
            tenant: 租户对象
            user: 用户对象  
            region_name: 区域名称
            creation_params: 创建参数，包含组件基础信息和集群配置
            
        Returns:
            tuple: (success, data, error_msg)
                - success: bool 是否成功
                - data: dict 组件信息
                - error_msg: str 错误信息
        """
        new_service = None
        try:
            # 第一阶段：创建组件元数据和基础配置
            logger.info(f"开始创建KubeBlocks组件: {creation_params.get('service_cname')}")
            
            new_service = self._create_component_metadata(tenant, user, region_name, creation_params)

            # 第二阶段：创建KubeBlocks集群
            cluster_result = self._create_kubeblocks_cluster(tenant, user, region_name, new_service, creation_params)
            
            # 第二阶段后：更新组件的 k8s_component_name
            self._update_k8s_component_name_from_cluster(new_service, cluster_result)
            
            # 第三阶段：加入应用分组
            self._add_to_application_group(tenant, region_name, creation_params.get('group_id'), new_service.service_id)
            
            # 第四阶段：在Region中创建资源
            self._create_region_service(tenant, new_service, user.nick_name)

            # 第五阶段：配置连接信息（环境变量）
            self._configure_connection_env_vars(tenant, user, region_name, new_service)
            
            # 第六阶段：配置端口信息
            self._configure_service_ports(tenant, user, new_service, region_name)
            
            # 第七阶段：构建部署组件
            deploy_result = self._deploy_component(tenant, new_service, user)
            
            # 第八阶段：创建部署关系记录
            from console.repositories.deploy_repo import deploy_repo
            deploy_repo.create_deploy_relation_by_service_id(service_id=new_service.service_id)
            logger.info(f"为组件 {new_service.service_alias} 创建部署关系记录")
            
            logger.info(f"KubeBlocks组件创建成功: {new_service.service_alias}")
            
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
        """创建组件元数据"""
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
    
    def _add_to_application_group(self, tenant, region_name, group_id, service_id):
        """
        将组件加入应用分组
        
        复用现有的应用分组服务，确保与其他组件创建流程保持一致。
        使用推荐的 add_component_to_app 方法而不是已弃用的 add_service_to_group。
        
        Args:
            tenant: 租户对象
            region_name (str): 区域名称
            group_id: 应用分组ID
            service_id (str): 组件服务ID
        
        Raises:
            ErrApplicationNotFound: 当应用分组不存在时抛出异常
        """
        try:
            GroupService.add_component_to_app(
                tenant=tenant,
                region_name=region_name,
                app_id=group_id,
                component_id=service_id
            )
            logger.info(f"成功将组件 {service_id} 加入应用分组 {group_id}")
        except Exception as e:
            logger.error(f"将组件加入应用分组失败: {str(e)}")
            raise ServiceHandleException(
                msg=f"加入应用分组失败: {str(e)}",
                msg_show="加入应用分组失败"
            )
    
    def _create_kubeblocks_cluster(self, tenant, user, region_name, new_service, params):
        """创建KubeBlocks集群"""
        # 构建集群创建参数（与KubeBlocksClustersView.post的参数保持一致）
        cluster_params = {
            "group_id": params.get("group_id"),
            "app_name": params.get("app_name", ""),
            "cluster_name": params.get("cluster_name"),
            "database_type": params.get("database_type"),
            "version": params.get("version"),
            "cpu": params.get("cpu"),
            "memory": params.get("memory"),
            "storage_size": params.get("storage_size"),
            "storage_class": params.get("storage_class", ""),
            "replicas": params.get("replicas", 1),
            "backup_repo": params.get("backup_repo", ""),
            "backup_schedule": params.get("backup_schedule", {}),
            "retention_period": params.get("retention_period", "7d"),
            "termination_policy": params.get("termination_policy", "Delete"),
            "k8s_component_name": new_service.k8s_component_name,
            "arch": params.get("arch", "amd64")
        }
        
        # 创建集群（传递已创建的 kubeblocks 组件对象）
        success, cluster_data = kubeblocks_service.create_cluster(
            tenant, user, region_name, cluster_params, new_service
        )
        
        if not success:
            raise ServiceHandleException(
                msg="KubeBlocks集群创建失败", 
                msg_show="KubeBlocks集群创建失败"
            )
        
        return cluster_data
    
    def _configure_connection_env_vars(self, tenant, user, region_name, new_service):
        """配置数据库连接环境变量"""
        # 配置数据库连接信息，失败时抛出异常
        kubeblocks_service.add_database_env_vars(tenant, new_service, user, region_name)
        logger.info(f"为组件 {new_service.service_alias} 配置连接环境变量成功")
    
    def _configure_service_ports(self, tenant, user, new_service, region_name):
        """配置服务端口"""
        request_data = {
            "RBDService": {
                "service_id": new_service.service_id
            }
        }
        res, body = region_api.get_kubeblocks_connect_info(region_name=region_name, cluster_data=request_data)
        if res.get("status") != 200 or not isinstance(body, dict):
            status = res.get("status") if isinstance(res, dict) else "unknown"
            raise ServiceHandleException(
                msg=f"获取连接信息失败，状态码: {status}",
                msg_show="获取端口信息失败"
            )

        bean = body.get("bean", {}) if isinstance(body, dict) else {}
        port = bean.get("port")
        if not isinstance(port, int):
            raise ServiceHandleException(
                msg="Block Mechanica 返回的端口信息无效",
                msg_show="端口信息无效"
            )
        port_alias = "DB"
        # 检查端口是否已存在
        existing_ports = self.port_service.get_service_ports(new_service)
        if not existing_ports:
            # 添加默认端口
            code, msg, port_data = self.port_service.add_service_port(
                tenant=tenant,
                service=new_service,
                container_port=port,
                protocol="http",
                port_alias=port_alias,
                is_inner_service=True,
                is_outer_service=False,
                k8s_service_name="",
                user_name=user.nick_name
            )
            
            if code != 200:
                logger.error(f"添加默认端口失败: {msg}")
                raise ServiceHandleException(
                    msg=f"添加默认端口失败: {msg}",
                    msg_show="端口配置失败"
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
            logger.info(f"在Region中创建服务资源成功: {new_service.service_alias}")
            return result_service
        except Exception as e:
            logger.error(f"在Region中创建服务资源失败: {str(e)}")
            raise ServiceHandleException(
                msg=f"Region资源创建失败: {str(e)}", 
                msg_show="Region资源创建失败"
            )
    
    def _deploy_component(self, tenant, new_service, user):
        """构建部署组件"""
        try:
            # 设置架构亲和性（在部署前执行）
            from console.services.app_config.arch_service import arch_service
            arch_service.update_affinity_by_arch(
                new_service.arch, tenant, new_service.service_region, new_service
            )
            logger.info(f"为组件 {new_service.service_alias} 设置架构亲和性: {new_service.arch}")
            
            # 调用标准的部署流程
            deploy_result = app_manage_service.deploy(
                tenant=tenant,
                service=new_service,
                user=user,
                oauth_instance=None
            )
            logger.info(f"组件部署成功: {new_service.service_alias}")
            return deploy_result
        except Exception as e:
            logger.error(f"组件部署失败: {str(e)}")
            raise ServiceHandleException(
                msg=f"组件部署失败: {str(e)}", 
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
                logger.info(f"成功获取组件 {updated_service.service_alias} 的分组ID: {group_info.ID}")
            else:
                logger.warning(f"未找到组件 {updated_service.service_id} 的分组关系")
                result_data["group_id"] = None
        except Exception as e:
            logger.error(f"获取组件分组信息失败: {e}")
            result_data["group_id"] = None
        
        # 如果有部署结果，添加部署相关信息
        if deploy_result:
            result_data.update({
                "status": "running",
                "status_cn": "运行中"
            })
        
        return result_data
    
    def _update_k8s_component_name_from_cluster(self, new_service, cluster_result):
        """
        从集群创建结果中更新组件的 k8s_component_name
        
        格式: {cluster_name}-{component_spec_name}
        例如: string-a0e0-mysql
        
        Args:
            new_service: 组件对象
            cluster_result: 集群创建结果数据
        """
        try:
            # 早期返回：检查 cluster_result 有效性
            if not cluster_result or not isinstance(cluster_result, dict):
                logger.warning("集群创建结果无效或为空")
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
            logger.info(f"成功更新组件 {new_service.service_alias} 的 k8s_component_name 为: {new_k8s_component_name}")
        except Exception as e:
            raise ServiceHandleException(
                msg=f"更新 k8s_component_name 失败: {str(e)}",
                msg_show="更新 k8s_component_name 失败"
            )
    
    def _cleanup_on_failure(self, new_service, tenant, region_name):
        """失败时清理资源"""
        try:
            if new_service and new_service.service_id:
                # 清理KubeBlocks集群
                kubeblocks_service.delete_kubeblocks_cluster([new_service.service_id], region_name)
                
                # 清理组件（如果已创建）
                if new_service.pk:
                    new_service.delete()
                    
                logger.info(f"清理失败的组件资源: {new_service.service_id}")
        except Exception as e:
            logger.error(f"清理失败资源时出错: {str(e)}")
    
    def create_cluster(self, tenant, user, region_name, cluster_params, kubeblocks_service):
        """
        创建 KubeBlocks 数据库集群
        
        纯集群创建逻辑，不涉及组件创建。接收已创建的 kubeblocks 组件对象，
        调用 Region API 创建对应的 KubeBlocks 集群。
        
        Args:
            tenant: 租户对象
            user: 用户对象
            region_name (str): 区域名称
            cluster_params (dict): 集群创建参数
            kubeblocks_service: 已创建的 kubeblocks 组件对象
            
        Returns:
            tuple: (success: bool, cluster_data: dict)
                - success: 是否创建成功
                - cluster_data: 集群创建结果数据
        """
        try:
            # 参数验证
            is_valid, error_msg = self.validate_cluster_params(cluster_params)
            if not is_valid:
                logger.error(f"KubeBlocks 集群参数验证失败: {error_msg}")
                return False, None
            
            # 构建集群创建请求数据
            cluster_data = self._build_block_mechanica_request(cluster_params, kubeblocks_service, tenant.namespace)
            
            # 调用 Region API 创建集群
            res, body = region_api.create_kubeblocks_cluster(region_name, cluster_data)
            
            if res.get("status") != 200:
                error_msg = f"KubeBlocks 集群创建失败: {body}"
                logger.error(error_msg)
                return False, None
            
            logger.info(f"成功创建 KubeBlocks 集群: {cluster_params.get('cluster_name')}")
            return True, body
            
        except Exception as e:
            logger.exception(f"创建 KubeBlocks 集群异常: {str(e)}")
            return False, None
    
    def add_database_env_vars(self, tenant, service, user, region_name):
        """
        为数据库组件添加环境变量
        
        失败时抛出ServiceHandleException异常
        """
        from console.exception.main import ServiceHandleException
        
        env_service = AppEnvVarService()
        
        # 获取数据库连接信息
        connect_info = self._get_database_connect_info(service, region_name)
        
        if not connect_info.get("username") and not connect_info.get("password"):
            raise ServiceHandleException(
                msg="无法获取数据库连接信息",
                msg_show="获取数据库连接信息失败"
            )
        
        # 添加数据库连接信息
        env_vars = [
            {
                "name": "Password",
                "attr_name": "DB_PASS",
                "attr_value": connect_info.get("password", ""),
                "scope": "outer"
            },
            {
                "name": "Username", 
                "attr_name": "DB_USER",
                "attr_value": connect_info.get("username", "root"),
                "scope": "outer"
            }
        ]
        
        # 添加环境变量，失败时抛出异常
        for env_var in env_vars:
            if not env_var["attr_value"]:
                continue
                
            code, msg, env = env_service.add_service_env_var(
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
                    msg=f"添加环境变量 {env_var['attr_name']} 失败: {msg}",
                    msg_show="添加数据库环境变量失败"
                )
    
    def _get_database_connect_info(self, service, region_name):
        """
        从 Block Mechanica API 获取数据库连接信息
        
        失败时抛出ServiceHandleException异常
        """
        from console.exception.main import ServiceHandleException
        
        try:
            request_data = {
                "RBDService": {
                    "service_id": service.service_id
                }
            }
            
            res, body = region_api.get_kubeblocks_connect_info(region_name, request_data)
            
            if res.get("status") == 200:
                bean = body.get("bean", {})
                connect_list = bean.get("connect_infos", [])
                
                if connect_list and len(connect_list) > 0:
                    connect_data = connect_list[0]
                    return {
                        "username": connect_data.get("user", "root"),
                        "password": connect_data.get("password", "")
                    }
                else:
                    raise ServiceHandleException(
                        msg="KubeBlocks API 返回空的连接信息列表",
                        msg_show="获取数据库连接信息为空"
                    )
            else:
                status = res.get("status", "未知")
                raise ServiceHandleException(
                    msg=f"KubeBlocks API 调用失败，状态码: {status}",
                    msg_show="获取数据库连接信息失败"
                )
                
        except ServiceHandleException:
            raise
        except Exception as e:
            raise ServiceHandleException(
                msg=f"调用 KubeBlocks API 获取连接信息异常: {str(e)}",
                msg_show="获取数据库连接信息异常"
            )
    
    def _build_block_mechanica_request(self, cluster_params, new_service, namespace):
        """
        构建 Block Mechanica 的 CreateClusterRequest 数据
        """
        cluster_data = {
            "name": cluster_params.get("k8s_component_name", "") or cluster_params["cluster_name"],  # 优先使用 k8s_component_name
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
        if not self._validate_cpu_format(cpu):
            return False, "CPU 配置格式不正确"
        
        # 内存格式校验
        memory = params["memory"]
        if not self._validate_memory_format(memory):
            return False, "内存配置格式不正确"
        
        # 存储格式校验
        storage_size = params["storage_size"]
        if not self._validate_storage_format(storage_size):
            return False, "存储大小格式不正确"
        
        # 保留时间格式校验
        retention_period = params.get("retention_period", "7d")
        if not self._validate_retention_period_format(retention_period):
            return False, "备份保留期格式不正确"
        
        return True, ""
    
    def _validate_cpu_format(self, cpu):
        """验证 CPU 格式"""
        import re
        pattern = r'^\d+(\.\d+)?[m]?$'
        return bool(re.match(pattern, cpu))
    
    def _validate_memory_format(self, memory):
        """验证内存格式"""
        import re
        pattern = r'^\d+(\.\d+)?(Mi|Gi|Ti)$'
        return bool(re.match(pattern, memory))
    
    def _validate_storage_format(self, storage):
        """验证存储格式"""
        import re
        pattern = r'^\d+(\.\d+)?(Mi|Gi|Ti)$'
        return bool(re.match(pattern, storage))
    
    def _validate_retention_period_format(self, retention_period):
        """验证备份保留期格式"""
        import re
        pattern = r'^\d+[dwmy]$'
        return bool(re.match(pattern, retention_period))
    
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

    def delete_kubeblocks_cluster(self, service_ids, region_name):
        """
        删除 KubeBlocks 集群
        
        通过 Block Mechanica API 删除与 Rainbond 组件关联的数据库集群
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
            
            if res.get("status") == 200:
                response_data = body
                if response_data.get("code") == 0:
                    logger.info("成功删除 KubeBlocks 集群: %s", str(service_ids))
                else:
                    error_msg = response_data.get("message", "删除失败")
                    logger.error("删除 KubeBlocks 集群失败: service_ids=%s, 错误: %s", str(service_ids), error_msg)
            else:
                status_code = res.get("status", 500)
                logger.error("删除 KubeBlocks 集群 API 调用返回非 200 状态: status=%s, service_ids=%s", 
                             status_code, str(service_ids))
                
        except Exception as e:
            logger.exception("删除 KubeBlocks 集群发生异常: service_ids=%s, region=%s, 错误=%s", 
                             str(service_ids), region_name, str(e))

    def get_component_info(self, region_name, service_id):
        """
        获取组件信息，判断是否为 KubeBlocks Component 并获取数据库类型等关键信息
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空", "bean": {"isKubeBlocksComponent": False}}
            
        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空", "bean": {"isKubeBlocksComponent": False}}
            
        try:
            res, body = region_api.get_kubeblocks_component_info(region_name, service_id)
            status_code = res.get("status", 500)
            
            if status_code == 200:
                bean = body.get("bean", {})
                bean.setdefault("isKubeBlocksComponent", bean.get("isKubeBlocksComponent", False))
                return 200, {"msg_show": "查询成功", "bean": bean}
            elif status_code == 404:
                return 404, {"msg_show": "组件不存在", "bean": {"isKubeBlocksComponent": False}}
            elif status_code == 403:
                return 403, {"msg_show": "无权限", "bean": {"isKubeBlocksComponent": False}}
            else:
                msg_show = body.get("msg_show", "查询失败") if isinstance(body, dict) else "查询失败"
                return status_code, {"msg_show": msg_show, "bean": {"isKubeBlocksComponent": False}}
                
        except Exception as e:
            logger.exception("获取组件信息异常: service_id=%s, region=%s, 错误=%s", 
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"后端服务异常: {str(e)}", "bean": {"isKubeBlocksComponent": False}}
    
    def get_component_port_info(self, service, region_name):
        """
        从 KubeBlocks Component Info API 获取端口信息
        
        Args:
            service: 组件对象
            region_name: 区域名称
            
        Returns:
            dict: 端口信息，格式为 {"port": 3306}
            
        Raises:
            ServiceHandleException: 当API调用失败或端口信息不存在时
        """
        from console.exception.main import ServiceHandleException
        
        if not service or not service.service_id:
            raise ServiceHandleException(
                msg="组件对象或组件ID不能为空",
                msg_show="组件信息无效"
            )
        
        if not region_name or not region_name.strip():
            raise ServiceHandleException(
                msg="区域名称不能为空",
                msg_show="区域信息无效"
            )
        
        try:
            # 调用现有的 region API
            res, body = region_api.get_kubeblocks_component_info(region_name, service.service_id)
            
            if res.get("status") == 200:
                bean = body.get("bean", {})
                port = bean.get("port")
                
                if port and isinstance(port, int):
                    logger.info(f"成功获取组件 {service.service_alias} 端口信息: {port}")
                    return {"port": port}
                else:
                    raise ServiceHandleException(
                        msg="KubeBlocks API 返回的端口信息无效",
                        msg_show="获取端口信息为空或无效"
                    )
            elif res.get("status") == 404:
                raise ServiceHandleException(
                    msg="组件不存在",
                    msg_show="组件不存在"
                )
            elif res.get("status") == 403:
                raise ServiceHandleException(
                    msg="无权限访问组件信息",
                    msg_show="无权限"
                )
            else:
                status = res.get("status", "未知")
                error_msg = body.get("msg_show", "查询失败") if isinstance(body, dict) else "查询失败"
                raise ServiceHandleException(
                    msg=f"KubeBlocks API 调用失败，状态码: {status}, 错误: {error_msg}",
                    msg_show="获取端口信息失败"
                )
        
        except ServiceHandleException:
            # 重新抛出服务异常
            raise
        except Exception as e:
            logger.exception("获取组件端口信息异常: service_id=%s, region=%s, 错误=%s", 
                           service.service_id, region_name, str(e))
            raise ServiceHandleException(
                msg=f"获取组件端口信息异常: {str(e)}",
                msg_show="获取端口信息失败"
            )
    
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
                return 200, {"msg_show": "查询成功", "bean": bean}
            elif status_code == 404:
                logger.error(f"集群不存在: service_id={service_id}")
                return 404, {"msg_show": "集群不存在"}
            elif status_code == 403:
                logger.error(f"无权限访问集群: service_id={service_id}")
                return 403, {"msg_show": "无权限"}
            else:
                msg_show = body.get("msg_show", "查询失败") if isinstance(body, dict) else "查询失败"
                logger.error(f"查询集群详情失败: status={status_code}, msg={msg_show}")
                return status_code, {"msg_show": msg_show}
                
        except Exception as e:
            logger.exception(f"查询集群详情异常: service_id={service_id}, region={region_name}, 错误={str(e)}")
            return 500, {"msg_show": f"后端服务异常: {str(e)}"}
    
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
                return 200, {"msg_show": "备份配置更新成功", "bean": data.get('bean') if isinstance(data, dict) else data}
            else:
                msg_show = data.get('msg_show', '备份配置更新失败') if isinstance(data, dict) else '备份配置更新失败'
                return status_code, {"msg_show": msg_show}
                
        except Exception as e:
            logger.exception("更新备份配置异常: service_id=%s, region=%s, 错误=%s", 
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"请求异常: {str(e)}"}
    
    def get_backup_list(self, region_name, service_id):
        """
        获取 KubeBlocks Cluster 的备份列表
        """
        if not region_name or not region_name.strip():
            return 400, {"msg_show": "区域名称不能为空"}
            
        if not service_id or not service_id.strip():
            return 400, {"msg_show": "组件ID不能为空"}
            
        try:
            res, data = region_api.get_kubeblocks_backup_list(region_name, service_id)
            status_code = res.get('status', 500)
            
            if status_code == 200:
                backup_list = data.get('list', []) if isinstance(data, dict) else []
                return 200, {"msg_show": "获取备份列表成功", "list": backup_list}
            else:
                msg_show = data.get('msg_show', '获取备份列表失败') if isinstance(data, dict) else '获取备份列表失败'
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

    def _get_kubeblocks_status_map(self, kubeblocks_status):
        """
        KubeBlocks 状态到 Rainbond 状态映射
        """
        status_mapping = {
            # 支持小写状态值（实际API返回的格式）
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
            },
            # 向后兼容：支持大写状态值
            "Creating": {
                "rainbond_status": "creating",
                "status_cn": "创建中",
                "disabledAction": ['restart', 'stop', 'reboot'],
                "activeAction": [],
            },
            "Running": {
                "rainbond_status": "running", 
                "status_cn": "运行中",
                "disabledAction": ['restart'],
                "activeAction": ['stop', 'reboot'],
            },
            "Updating": {
                "rainbond_status": "upgrade",
                "status_cn": "升级中", 
                "disabledAction": ['restart', 'stop'],
                "activeAction": ['reboot'],
            },
            "Stopping": {
                "rainbond_status": "stopping",
                "status_cn": "关闭中",
                "disabledAction": ['restart', 'stop', 'reboot'],
                "activeAction": [],
            },
            "Stopped": {
                "rainbond_status": "closed",
                "status_cn": "已关闭",
                "disabledAction": ['stop', 'reboot'],
                "activeAction": ['restart'],
            },
            "Deleting": {
                "rainbond_status": "stopping", 
                "status_cn": "删除中",
                "disabledAction": ['restart', 'stop', 'reboot'],
                "activeAction": [],
            },
            "Failed": {
                "rainbond_status": "failure",
                "status_cn": "未知",
                "disabledAction": ['restart'],
                "activeAction": ['stop', 'reboot'],
            },
            "Abnormal": {
                "rainbond_status": "abnormal",
                "status_cn": "运行异常",
                "disabledAction": ['restart'],
                "activeAction": ['stop', 'reboot'],
            }
        }
        
        return status_mapping.get(kubeblocks_status, {
            "rainbond_status": "unKnow",
            "status_cn": "未知",
            "disabledAction": ['restart', 'reboot'],
            "activeAction": ['stop'],
        })
    
    def get_kubeblocks_service_status(self, region_name, service_id):
        """
        获取 KubeBlocks 组件状态信息
        
        复用现有的状态处理逻辑，将 KubeBlocks 集群状态映射为 Rainbond 组件状态格式
        
        Returns:
            dict: 包含 status, status_cn, disabledAction, activeAction, start_time 的状态映射
                 失败时返回 None
        """
        try:
            status_code, response = self.get_cluster_detail(region_name, service_id)
            
            if status_code != 200:
                if status_code == 503:
                    logger.warning(f"KubeBlocks 服务不可用: status={status_code}, service_id={service_id}")
                else:
                    logger.warning(f"获取 KubeBlocks 集群详情失败: status={status_code}, service_id={service_id}")
                return None
                
            bean = response.get("bean", {})
            basic_info = bean.get("basic", {})
            status_info = basic_info.get("status", {})
            
            # 从状态信息字典中提取实际的状态字符串
            if isinstance(status_info, dict):
                kubeblocks_status = status_info.get("status", "")
                start_time = status_info.get("start_time", "")
            else:
                # 向后兼容：如果是字符串则直接使用
                kubeblocks_status = status_info
                start_time = ""
            
            if not kubeblocks_status:
                logger.warning(f"KubeBlocks 集群状态为空: service_id={service_id}")
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
            logger.exception(f"获取 KubeBlocks 组件状态异常: service_id={service_id}, region={region_name}, 错误={str(e)}")
            return None

    def get_multiple_kubeblocks_status_and_resources(self, region_name, service_ids):
        """
        批量获取 KubeBlocks 组件的状态和资源信息
        
        Args:
            region_name (str): 区域名称
            service_ids (list): 组件ID列表
            
        Returns:
            dict: {service_id: {"status": "...", "status_cn": "...", "used_mem": 0}}
        """
        result = {}
        
        for service_id in service_ids:
            try:
                # 获取状态信息
                # TODO 调用了两次 get_cluster_detail
                kb_status = self.get_kubeblocks_service_status(region_name, service_id)
                
                # 获取资源信息
                kb_resource = self.get_kubeblocks_resource_info(region_name, service_id)
                
                result[service_id] = {
                    "status": kb_status.get("status", "failure") if kb_status else "failure",
                    "status_cn": kb_status.get("status_cn", "获取状态失败") if kb_status else "获取状态失败",
                    "used_mem": kb_resource.get("used_mem", 0) if kb_resource else 0
                }
                
            except Exception as e:
                logger.exception(f"获取 KubeBlocks 组件 {service_id} 信息失败: {str(e)}")
                # 降级处理：资源消耗设为0
                result[service_id] = {
                    "status": "failure",
                    "status_cn": "获取状态失败", 
                    "used_mem": 0
                }
                
        return result
    
    def get_kubeblocks_resource_info(self, region_name, service_id):
        """
        获取 KubeBlocks 组件的资源信息
        
        Args:
            region_name (str): 区域名称
            service_id (str): 组件ID
            
        Returns:
            dict: {"used_mem": 内存消耗(MB), "used_cpu": CPU消耗}
        """
        try:
            # 获取集群详情
            status_code, response = self.get_cluster_detail(region_name, service_id)
            
            if status_code != 200:
                logger.warning(f"获取 KubeBlocks 集群详情失败: status={status_code}, service_id={service_id}")
                return {"used_mem": 0, "used_cpu": 0}
                
            bean = response.get("bean", {})
            resource_info = bean.get("resource", {})
            
            # 提取资源信息并转换单位
            memory_mb = resource_info.get("memory", 0)  # MB
            cpu_cores = resource_info.get("cpu", 0)     # millicores
            
            # CPU 单位转换：millicores -> cores
            cpu_cores = cpu_cores / 1000.0 if cpu_cores else 0
            
            # 副本数
            replicas = resource_info.get("replicas", 1)
            
            # 计算总资源（分配资源 = 单实例资源 × 副本数）
            total_memory = memory_mb * replicas
            total_cpu = cpu_cores * replicas
            
            logger.debug(f"KubeBlocks 组件 {service_id} 资源信息: 内存={total_memory}MB, CPU={total_cpu}cores")
            
            return {
                "used_mem": int(total_memory),  # 使用分配的内存作为 used_mem
                "used_cpu": round(total_cpu, 2)
            }
            
        except Exception as e:
            logger.exception(f"获取 KubeBlocks 组件资源信息异常: service_id={service_id}, region={region_name}, 错误={str(e)}")
            return {"used_mem": 0, "used_cpu": 0}

    def manage_cluster_status(self, service, region_name, oauth_instance, operation):
        """
        管理 KubeBlocks 集群状态
        """
        res, body = region_api.manage_cluster_status(region_name, [service.service_id], operation)
        logger.warning(f"kubeblocks manage_cluster_service: res={res}, body={body}")
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



    def get_cluster_events(self, region_name, service_id, page, page_size):
        """
        获取 KubeBlocks 集群事件（操作记录）列表

        返回:
            (status_code, data) 其中 data 格式: { 'list': [...], 'number': int }
        """
        try:
            res, body = region_api.get_kubeblocks_cluster_events(region_name, service_id, page, page_size)
            status_code = res.get('status', 500) if isinstance(res, dict) else getattr(res, 'status', 500)
            if status_code == 200:
                events = []
                total = 0
                if isinstance(body, dict):
                    events = body.get('list', []) or []
                    total = body.get('number', 0) or 0
                return 200, { 'list': events, 'number': int(total) }
            else:
                msg_show = (body.get('msg_show') if isinstance(body, dict) else None) or '获取 KubeBlocks 事件失败'
                return status_code, { 'msg_show': msg_show, 'list': [], 'number': 0 }
        except Exception as e:
            logger.exception("获取 KubeBlocks 事件异常: service_id=%s, region=%s, 错误=%s", service_id, region_name, str(e))
            return 500, { 'msg_show': f'请求异常: {str(e)}', 'list': [], 'number': 0 }

    def normalize_kb_events(self, events, tenant, service):
        """
        将 KB 事件补齐为 UI/Console 统一结构（仅补齐必要字段）

        填充/默认规则:
          - target: 'service'
          - target_id: service.service_id
          - tenant_id: tenant.tenant_id
          - user_name: 缺省 'system'
          - syn_type: 1 （KB 暂不提供详情日志）
        保留（若存在）:
          - event_id, opt_type, status, final_status, message, reason, create_time, end_time
        """
        normalized = []
        if not events:
            return normalized

        def _kb_time_to_local_rfc3339(tstr):
            """仅转换 KB 的时间到本地时区 RFC3339(+HH:MM) 字符串。

            兼容 Python 3.6：不使用 fromisoformat，采用 strptime(%z)。
            - 支持 Z 结尾（转为 +0000）
            - 支持带冒号偏移（+08:00 -> +0800）
            - 失败则返回原字符串
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
            for key in ['event_id', 'opt_type', 'status', 'final_status', 'message', 'reason', 'create_time', 'end_time']:
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
            # 透传来自 Block Mechanica 的操作者信息；若无则不设置，避免覆盖上游默认
            ev_user = ev.get('user_name')
            if isinstance(ev_user, str) and ev_user:
                item['user_name'] = ev_user
            # KB 事件当前不开放详情日志
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
                msg_show = response_body.get("msg_show", "更新参数失败") if isinstance(response_body, dict) else "更新参数失败"
                return status_code, {"msg_show": msg_show}

        except Exception as e:
            logger.exception("更新KubeBlocks集群参数异常: service_id=%s, region=%s, 错误=%s",
                             service_id, region_name, str(e))
            return 500, {"msg_show": f"请求异常: {str(e)}"}

kubeblocks_service = KubeBlocksService()
