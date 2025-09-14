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

class KubeBlocksClusterParametersView(RegionTenantHeaderView):
    def get(self, request, team_name, region_name, service_id, *args, **kwargs):
        """
        获取 KubeBlocks 数据库参数列表（分页/搜索）
        """
        try:
            # 获取查询参数
            page = request.GET.get('page', 1)
            page_size = request.GET.get('page_size', 6)
            keyword = request.GET.get('keyword', '').strip() or None

            status_code, data = kubeblocks_service.get_cluster_parameters(
                region_name, service_id, page, page_size, keyword
            )

            if status_code == 200:
                logger.debug(f"KubeBlocks 获取集群参数: {data}")
                return Response(general_message(
                    200,
                    "查询成功",
                    "获取参数列表成功",
                    list=data.get('list', []),
                    page=data.get('page', 1),
                    total=data.get('number', 0)
                ))
            else:
                msg_show = data.get("msg_show", "获取参数失败")
                return Response(general_message(status_code, "查询失败", msg_show))

        except Exception as e:
            logger.exception(f"获取KubeBlocks集群参数异常: {str(e)}")
            return Response(general_message(500, "后端服务异常", f"后端服务异常: {str(e)}"))

    def post(self, request, team_name, region_name, service_id, *args, **kwargs):
        """
        批量更新 KubeBlocks 数据库参数
        """
        try:
            # 获取请求体数据
            body = request.data or {}

            status_code, data = kubeblocks_service.update_cluster_parameters(
                region_name, service_id, body
            )

            if status_code == 200:
                # 与控制台通用返回结构对齐：更新结果放入 bean，前端读取 data.bean
                logger.debug(f"KubeBlocks 更新集群参数: {data}")
                return Response(general_message(200, "更新成功", "参数更新成功", bean=data))
            else:
                msg_show = data.get("msg_show", "更新参数失败")
                return Response(general_message(status_code, "更新失败", msg_show))

        except Exception as e:
            logger.exception(f"更新KubeBlocks数据库参数异常: {str(e)}")
            return Response(general_message(500, "后端服务异常", f"后端服务异常: {str(e)}"))
