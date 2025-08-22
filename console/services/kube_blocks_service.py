# -*- coding: utf8 -*-
"""
KubeBlocks 相关服务
"""
import logging

from django.db import transaction

from console.exception.bcode import ErrK8sComponentNameExists
from console.services.app import app_service
from console.services.app_config.env_service import AppEnvVarService
from console.services.group_service import group_service
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("kubeblocks_service")
region_api = RegionInvokeApi()


class KubeBlocksService(object):
    
    @transaction.atomic
    def create_database_cluster(self, tenant, user, region_name, cluster_params):
        """
        创建数据库集群（用户感知为通过容器镜像创建 Rainbond 组件）

        """
        try:
            # 提取参数
            group_id = cluster_params.get("group_id")
            cluster_name = cluster_params["cluster_name"]
            database_type = cluster_params["database_type"]
            version = cluster_params["version"]
            k8s_component_name = cluster_params.get("k8s_component_name", "")
            arch = cluster_params.get("arch", "amd64")
            
            service_cname = cluster_name
            docker_cmd = "alpine/socat:1.8.0.3"
            image = ""
            image_type = "docker_image"
            
            if k8s_component_name and app_service.is_k8s_component_name_duplicate(group_id, k8s_component_name):
                raise ErrK8sComponentNameExists
            
            code, msg_show, new_service = app_service.create_docker_run_app(
                region_name,
                tenant,
                user,
                service_cname,
                docker_cmd,
                image_type,
                k8s_component_name,
                image,
                arch
            )
            
            if code != 200:
                return False, None
            
            new_service.service_name = new_service.k8s_component_name
            new_service.save()
            
            code, msg_show = group_service.add_service_to_group(
                tenant,
                region_name,
                group_id,
                new_service.service_id
            )
            
            if code != 200:
                new_service.delete()
                return False, None
            
            cluster_data = self._build_block_mechanica_request(cluster_params, new_service, tenant.namespace)
            
            try:
                res, body = region_api.create_kubeblocks_database_cluster(region_name, cluster_data)
                
                if res.get("status") != 200:
                    logger.error(f"KubeBlocks 集群创建失败，但组件创建成功: {body}")
            except Exception as cluster_error:
                logger.exception(f"KubeBlocks 集群创建异常，但组件创建成功: {str(cluster_error)}")
            
            result_data = new_service.to_dict()
            result_data["app_alias"] = new_service.service_alias
            result_data["group_id"] = group_id
            
            logger.info(f"成功通过镜像创建组件: {service_cname}")
            return True, result_data
                
        except Exception as e:
            logger.exception(f"创建组件异常: {str(e)}")
            return False, None
    
    def add_database_env_vars(self, tenant, service, user, region_name):
        """
        为数据库组件添加环境变量

        """
        try:
            env_service = AppEnvVarService()
            
            connect_info = self._get_database_connect_info(service, region_name)
            
            if not connect_info.get("username") and not connect_info.get("password"):
                return
            
            # 添加数据库连接信息
            env_vars = [
                {
                    "name": "Password",
                    "attr_name": "DB_PASS",
                    "attr_value": connect_info.get("password", ""),  # 默认值
                    "scope": "outer"
                },
                {
                    "name": "Username", 
                    "attr_name": "DB_USER",
                    "attr_value": connect_info.get("username", "root"),  # 默认值
                    "scope": "outer"
                }
            ]
            
            # 只添加非空值的环境变量
            for env_var in env_vars:
                if not env_var["attr_value"]:
                    continue
                    
                try:
                    env_service.add_service_env_var(
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
                except Exception:
                    pass
                    
        except Exception:
            pass
    
    def _get_database_connect_info(self, service, region_name):
        """
        从 Block Mechanica API 获取数据库连接信息

        """
        try:
            request_data = {
                "RBDService": {
                    "service_id": service.service_id
                }
            }
            
            res, body = region_api.get_kubeblocks_connect_info(region_name, request_data)
            
            if res.get("status") == 200:
                connect_list = body.get("list", [])
                
                if connect_list and len(connect_list) > 0:
                    connect_data = connect_list[0]
                    return {
                        "username": connect_data.get("user", "root"),
                        "password": connect_data.get("password", "")
                    }
            
        except Exception:
            pass
        
        return {"username": "", "password": ""}
    
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

kubeblocks_service = KubeBlocksService() 