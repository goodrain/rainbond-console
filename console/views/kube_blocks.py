# -*- coding: utf8 -*-
import logging

from rest_framework.response import Response

from console.exception.bcode import ErrK8sComponentNameExists
from console.services.kube_blocks_service import kubeblocks_service
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class KubeBlocksAddonsView(RegionTenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        """
        获取指定区域下 KubeBlocks 支持的数据库类型列表
        """
        try:
            status, data = kubeblocks_service.get_supported_databases(region_name)
            return Response(general_message(status, "success" if status == 200 else "failed", "成功获取" if status == 200 else "获取失败", list=data.get("list", [])))

        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, "request error", f"请求异常: {str(e)}"), status=500)


class KubeBlocksStorageClassesView(RegionTenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        """
        获取指定区域下 KubeBlocks StorageClass 列表
        """
        try:
            status, data = kubeblocks_service.get_storage_classes(region_name)
            return Response(general_message(status, "success" if status == 200 else "failed", "成功获取" if status == 200 else "获取失败", list=data.get("list", [])))
        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, "request error", f"请求异常: {str(e)}"), status=500)

class KubeBlocksBackupReposView(RegionTenantHeaderView):
    def get(self, request, team_name, region_name, *args, **kwargs):
        """
        获取指定区域下 KubeBlocks BackupRepo 列表
        """
        try:
            status, data = kubeblocks_service.get_backup_repos(region_name)
            return Response(general_message(status, "success" if status == 200 else "failed", "成功获取" if status == 200 else "获取失败", list=data.get("list", [])))
        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, "request error", f"请求异常: {str(e)}"), status=500)


class KubeBlocksClustersView(RegionTenantHeaderView):
    def post(self, request, team_name, region_name, *args, **kwargs):
        """
        创建 KubeBlocks 数据库集群
        ---
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: region_name
              description: 区域名称
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用分组ID
              required: false
              type: string
              paramType: form
            - name: app_name
              description: 应用名称
              required: false
              type: string
              paramType: form
            - name: cluster_name
              description: 数据库集群名称
              required: true
              type: string
              paramType: form
            - name: database_type
              description: 数据库类型
              required: true
              type: string
              paramType: form
            - name: version
              description: 数据库版本
              required: true
              type: string
              paramType: form
            - name: cpu
              description: CPU 配置
              required: true
              type: string
              paramType: form
            - name: memory
              description: 内存配置
              required: true
              type: string
              paramType: form
            - name: storage_size
              description: 存储大小
              required: true
              type: string
              paramType: form
            - name: storage_class
              description: 存储类名称
              required: false
              type: string
              paramType: form
            - name: replicas
              description: 副本数量
              required: false
              type: integer
              paramType: form
            - name: backup_repo
              description: 备份仓库名称
              required: false
              type: string
              paramType: form
            - name: backup_schedule
              description: 备份调度配置
              required: false
              type: object
              paramType: form
            - name: retention_period
              description: 备份保留期（如：7d, 30d）
              required: false
              type: string
              paramType: form
            - name: termination_policy
              description: 删除策略（Delete, WipeOut）
              required: false
              type: string
              paramType: form
            - name: k8s_app
              description: 组件名称，用于创建 KubeBlocks 集群的名称
              required: false
              type: string
              paramType: form
            - name: k8s_component_name
              description: K8s组件名称，与 k8s_app 功能相同
              required: false
              type: string
              paramType: form
            - name: arch
              description: 架构类型
              required: false
              type: string
              paramType: form
        """
        
        try:
            data = request.data or {}
            if isinstance(data.get("config"), dict):
                merged = dict(data)
                cfg = merged.pop("config")
                if isinstance(cfg, dict):
                    merged.update(cfg)
                data = merged

            cluster_params = {
                "group_id": data.get("group_id"),
                "app_name": data.get("app_name", ""),
                "cluster_name": data.get("cluster_name"),
                "database_type": data.get("database_type"),
                "version": data.get("version"),
                "cpu": data.get("cpu"),
                "memory": data.get("memory"),
                "storage_size": data.get("storage_size"),
                "storage_class": data.get("storage_class", ""),
                "replicas": data.get("replicas", 1),
                "backup_repo": data.get("backup_repo", ""),
                "backup_schedule": data.get("backup_schedule", {}),
                "retention_period": data.get("retention_period", "7d"),
                "termination_policy": data.get("termination_policy", "Delete"),
                "k8s_component_name": data.get("k8s_app") or data.get("k8s_component_name", ""),
                "arch": data.get("arch", "amd64")
            }
            
            is_valid, error_msg = kubeblocks_service.validate_cluster_params(cluster_params)
            if not is_valid:
                return Response(general_message(400, "params error", error_msg), status=400)
            
            # 创建 Cluster 和 KubeBlocks Component
            success, data = kubeblocks_service.create_database_cluster(
                self.tenant, 
                self.user, 
                self.response_region, 
                cluster_params
            )
            
            if success:
                return Response(general_message(200, "success", "组件创建成功", bean=data), status=200)
            else:
                return Response(general_message(500, "failed", "创建失败"), status=500)

        except ErrK8sComponentNameExists:
            return Response(general_message(400, "k8s component name exists", "组件英文名已存在"), status=400)
        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, "request error", f"请求异常: {str(e)}"), status=500)

class KubeBlocksComponentInfoView(RegionTenantHeaderView):
    def get(self, request, team_name, region_name, service_id, *args, **kwargs):
        """
        判断某个组件是否为 KubeBlocks 组件，并获取其数据库类型等关键信息
        """
        try:
            status_code, data = kubeblocks_service.get_component_info(region_name, service_id)
            
            if status_code == 200:
                bean = data.get("bean", {})
                return Response(general_message(200, "查询成功", data.get("msg_show", "查询成功"), bean=bean))
            else:
                bean = data.get("bean", {"isKubeBlocksComponent": False})
                msg_show = data.get("msg_show", "查询失败")
                return Response(general_message(status_code, "查询失败", msg_show, bean=bean))
                
        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, "后端服务异常", f"后端服务异常: {str(e)}", bean={"isKubeBlocksComponent": False}))

class KubeBlocksClusterDetailView(RegionTenantHeaderView):
    def get(self, request, team_name, region_name, service_id, *args, **kwargs):
        """
        获取 Cluster detail
        """
        try:
            logger.debug(f"查询 KubeBlocks 集群详情: team_name={team_name}, region_name={region_name}, service_id={service_id}")
            
            status_code, data = kubeblocks_service.get_cluster_detail(region_name, service_id)
            
            if status_code == 200:
                bean = data.get("bean", {})
                msg_show = data.get("msg_show", "查询成功")
                return Response(general_message(200, "查询成功", msg_show, bean=bean))
            else:
                msg_show = data.get("msg_show", "查询失败")
                return Response(general_message(status_code, "查询失败", msg_show))
                
        except Exception as e:
            logger.exception(f"查询集群详情异常: {str(e)}")
            return Response(general_message(500, "后端服务异常", f"后端服务异常: {str(e)}"))

    def put(self, request, team_name, region_name, service_id, *args, **kwargs):
        """
        伸缩 Cluster
        """
        try:
            expansion_body = request.data or {}
            status_code, data = kubeblocks_service.expand_cluster(region_name, service_id, expansion_body)
            
            if status_code == 200:
                bean = data.get('bean', {})
                msg_show = data.get("msg_show", "伸缩成功")
                return Response(general_message(200, 'success', msg_show, bean=bean))
            else:
                msg_show = data.get('msg_show', '伸缩失败')
                return Response(general_message(status_code, 'failed', msg_show))
                
        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, 'request error', f'请求异常: {str(e)}'))


class KubeBlocksClusterBackupView(RegionTenantHeaderView):
    def put(self, request, team_name, region_name, service_id, *args, **kwargs):
        """
        更新 KubeBlocks 集群的备份配置
        """
        try:
            body = request.data or {}
            status_code, data = kubeblocks_service.update_backup_config(region_name, service_id, body)
            
            if status_code == 200:
                bean = data.get('bean', {})
                msg_show = data.get("msg_show", "备份配置更新成功")
                return Response(general_message(200, 'success', msg_show, bean=bean))
            else:
                msg_show = data.get('msg_show', '备份配置更新失败')
                return Response(general_message(status_code, 'failed', msg_show))
                
        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, 'request error', f'请求异常: {str(e)}'))

class KubeBlocksClusterBackupListView(RegionTenantHeaderView):
    def get(self, request, team_name, region_name, service_id, *args, **kwargs):
        """
        获取备份列表
        """
        try:
            status_code, data = kubeblocks_service.get_backup_list(region_name, service_id)
            
            if status_code == 200:
                backup_list = data.get('list', [])
                msg_show = data.get("msg_show", "获取备份列表成功")
                return Response(general_message(200, 'success', msg_show, list=backup_list))
            else:
                msg_show = data.get('msg_show', '获取备份列表失败')
                return Response(general_message(status_code, 'failed', msg_show))
            
        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, 'request error', f'请求异常: {str(e)}'))

    def post(self, request, team_name, region_name, service_id, *args, **kwargs):
        """
        创建手动备份
        """
        try:
            status_code, data = kubeblocks_service.create_manual_backup(region_name, service_id)
            
            if status_code == 200:
                bean = data.get('bean', {})
                msg_show = data.get("msg_show", "手动备份已启动")
                return Response(general_message(200, 'success', msg_show, bean=bean))
            else:
                msg_show = data.get('msg_show', '手动备份启动失败')
                return Response(general_message(status_code, 'failed', msg_show))
            
        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, 'request error', f'请求异常: {str(e)}'))
    
    def delete(self, request, team_name, region_name, service_id, *args, **kwargs):
        """
        删除备份
        """
        try:
            request_data = request.data or {}
            backups = request_data.get('backups', None)

            status_code, data = kubeblocks_service.delete_backups(region_name, service_id, backups)

            if status_code == 200:
                deleted_list = data.get('list', [])
                msg_show = data.get("msg_show", "备份删除成功")
                return Response(general_message(200, 'success', msg_show, list=deleted_list))
            else:
                msg_show = data.get('msg_show', '备份删除失败')
                return Response(general_message(status_code, 'failed', msg_show))

        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, 'request error', f'请求异常: {str(e)}'))
