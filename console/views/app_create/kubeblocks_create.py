# -*- coding: utf-8 -*-
import logging
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from console.exception.bcode import ErrK8sComponentNameExists
from console.exception.main import ServiceHandleException
from console.services.app import app_service
from console.services.kubeblocks_service import kubeblocks_service
from console.services.operation_log import operation_log_service, OperationType
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_message

logger = logging.getLogger("default")

class KubeBlocksComponentCreateView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        一次性完成创建 KubeBlocks Component 的创建
        
        在单次API调用中完成从组件创建到部署的完整流程，
        与常规组件部署完成后返回相同格式的数据。
        """
        service_cname = request.data.get("cluster_name", "").strip()
        k8s_component_name = request.data.get("k8s_app", "")
        group_id = request.data.get("group_id", -1)
        
        if isinstance(group_id, str):
            if group_id in ["", "-1", "0"]:
                group_id = -1
            else:
                try:
                    group_id = int(group_id)
                except ValueError:
                    group_id = -1
        
        if k8s_component_name and app_service.is_k8s_component_name_duplicate(group_id, k8s_component_name):
            raise ErrK8sComponentNameExists

        try:
            # 检查组件名称
            if not service_cname:
                return Response(
                    general_message(400, "cluster_name required", "组件名称不能为空"),
                    status=400
                )
            
            # 集群配置必填参数检查
            required_cluster_fields = ["cluster_name", "database_type", "version", 
                                     "cpu", "memory", "storage_size"]
            for field in required_cluster_fields:
                if not request.data.get(field):
                    return Response(
                        general_message(400, f"{field} required", f"{field}不能为空"),
                        status=400
                    )
            
            # 准备创建参数
            creation_params = dict(request.data)
            creation_params["service_cname"] = service_cname
            creation_params["k8s_component_name"] = k8s_component_name
            creation_params["group_id"] = group_id
            
            # 完整创建 KubeBlocks Component
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
            
            # **返回与标准组件部署完成后相同格式的响应**
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
