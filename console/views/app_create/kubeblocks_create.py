# -*- coding: utf-8 -*-
"""
KubeBlocks 组件创建视图

用于处理 KubeBlocks 组件的一站式创建请求，提供 REST API 接口供前端调用。
与常规组件创建不同，此API在单次调用中完成组件创建、集群部署、连接配置等全部流程。
"""

import logging
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.bcode import ErrK8sComponentNameExists
from console.exception.main import ServiceHandleException
from console.services.app import app_service
from console.services.kube_blocks_service import kubeblocks_service
from console.services.operation_log import operation_log_service, OperationType
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_message

logger = logging.getLogger("default")

# TODO 关于这个创建操作：
# 可以调用现有的 service KubeBlocksService.create_cluster 实现
# 故需要对 service 的创建逻辑进行调整
# 不同于常规的组件创建需要 console 创建 -> create-check -> create-configFile ->
#  create-configPort -> region_service -> deploy 的流程
# 这里的流程直接完成 console 创建，create-configFile, create-configPort,
# region_service, deploy, cluster 创建等步骤, 同时在 regions_service 创建之前获取到 cluster 的连接信息，
# 添加到组件的连接信息中
# 这块应该让前端跳过 create-check 开始的这些页面, 执行完之后直接跳转到组件详情
# 或许可以复用 kubeblocks_service：(但是需要修改)
# - add_database_env_vars
# - create_cluster
class KubeBlocksComponentCreateView(RegionTenantHeaderView):
    """
    KubeBlocks 组件一站式创建视图
    
    处理 KubeBlocks 组件的完整创建流程，包括：
    - 组件元数据创建
    - KubeBlocks 集群创建  
    - 连接信息配置
    - Region 资源创建
    - 组件构建部署
    """
    
    @never_cache
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        一站式创建 KubeBlocks 组件
        
        在单次API调用中完成从组件创建到部署的完整流程，
        与常规组件部署完成后返回相同格式的数据。
        
        Parameters (扁平结构，所有参数均为顶级字段):
        
        必填字段:
        - cluster_name (str): 集群名称，同时作为Rainbond组件中文显示名称，必填
        - database_type (str): 数据库类型（mysql、postgresql、redis等），必填
        - version (str): 数据库版本，必填
        - cpu (str): CPU配置（如：1、500m），必填
        - memory (str): 内存配置（如：1Gi、2Gi），必填
        - storage_size (str): 存储大小（如：10Gi、100Gi），必填
        
        应用分组相关字段:
        - group_id (str/int): 应用分组ID，可选（空、-1、""、"0"时自动创建新应用）
        - app_name (str): 新应用名称，仅在group_id为空时使用，可选
        
        可选配置字段:
        - k8s_app (str): Kubernetes组件名称，可选（空时自动生成）
        - storage_class (str): 存储类名称，可选
        - replicas (int): 副本数量，默认1
        - arch (str): 架构类型，默认amd64
        - termination_policy (str): 删除策略，默认Delete
        
        备份相关字段:
        - backup_repo (str): 备份仓库名称，不为空时启用备份，可选
        - backup_schedule (dict): 备份调度配置，仅backup_repo不为空时生效，可选
        - retention_period (str): 备份保留期，默认7d，仅backup_repo不为空时生效，可选
        
        Returns:
        JSON 响应格式（与标准组件部署完成后格式一致）:
        {
            "code": 200,
            "msg": "success",
            "msg_show": "创建成功", 
            "data": {
                "bean": {
                    "service_id": "组件ID",
                    "service_cname": "组件显示名称",
                    "service_alias": "组件别名",
                    "status": "running",
                    // 其他标准组件字段...
                }
            }
        }
        """
        
        # 按照实际 API 规范直接从请求体获取参数（扁平结构）
        # 根据 @kubeblocks_api_doc.md 规范，所有参数均为顶级字段
        service_cname = request.data.get("cluster_name", "").strip()  # cluster_name 作为组件中文显示名称
        k8s_component_name = request.data.get("k8s_app", "")  # k8s_app 作为 K8s 组件英文名
        group_id = request.data.get("group_id", -1)  # 应用分组ID（可选，可以是字符串或数字）
        
        # 处理 group_id 字段（支持字符串和数字类型）
        if isinstance(group_id, str):
            if group_id in ["", "-1", "0"]:
                group_id = -1
            else:
                try:
                    group_id = int(group_id)
                except ValueError:
                    group_id = -1
        
        # 检查 K8s 组件名称是否重复（如果指定了名称）
        if k8s_component_name and app_service.is_k8s_component_name_duplicate(group_id, k8s_component_name):
            raise ErrK8sComponentNameExists

        try:
            # 基础参数验证
            # 检查组件名称（必填）
            if not service_cname:
                return Response(
                    general_message(400, "cluster_name required", "组件名称不能为空"),
                    status=400
                )
            
            # 集群配置必填参数检查（直接从请求体获取）
            required_cluster_fields = ["cluster_name", "database_type", "version", 
                                     "cpu", "memory", "storage_size"]
            for field in required_cluster_fields:
                if not request.data.get(field):
                    return Response(
                        general_message(400, f"{field} required", f"{field}不能为空"),
                        status=400
                    )
            
            # 准备创建参数（直接使用请求体数据，符合扁平结构规范）
            creation_params = dict(request.data)  # 获取所有请求参数
            creation_params["service_cname"] = service_cname  # 确保组件显示名称正确
            creation_params["k8s_component_name"] = k8s_component_name  # 确保 K8s 组件名称正确  
            creation_params["group_id"] = group_id  # 使用处理后的应用组ID
            
            # 调用 KubeBlocks 服务执行完整创建流程
            success, result_data, error_msg = kubeblocks_service.create_complete_kubeblocks_component(
                tenant=self.tenant,
                user=self.user,
                region_name=self.response_region,
                creation_params=creation_params
            )
            
            if not success:
                return Response(
                    general_message(500, "create failed", error_msg or "创建失败"),
                    status=500
                )
            
            # 记录操作日志
            operation_log_service.create_log(
                user=self.user,
                operation_type=OperationType.COMPONENT_MANAGE,
                comment=f"创建KubeBlocks组件: {service_cname} (类型: {request.data.get('database_type', 'unknown')})",
                enterprise_id=self.user.enterprise_id,
                team_name=self.tenant.tenant_name,
                service_alias=result_data.get("service_alias", ""),
                service_cname=service_cname,
                is_openapi=False
            )
            
            # 返回与标准组件部署完成后相同格式的响应
            return Response(
                general_message(200, "success", "创建成功", bean=result_data)
            )
            
        except ErrK8sComponentNameExists:
            return Response(
                general_message(400, "k8s component name exists", "Kubernetes组件名称已存在"),
                status=400
            )
        except ServiceHandleException as e:
            logger.error(f"KubeBlocks组件创建业务异常: {e.msg}")
            return Response(
                general_message(400, "service error", e.msg_show or e.msg),
                status=400
            )
        except Exception as e:
            logger.exception(f"创建KubeBlocks组件异常: {e}")
            return Response(
                general_message(500, "create error", f"创建异常: {str(e)}"),
                status=500
            )
