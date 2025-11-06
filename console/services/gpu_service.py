# -*- coding: utf8 -*-
"""
GPU 管理服务
提供GPU资源管理、配额管理等业务逻辑
"""
import logging

from console.repositories.gpu_repo import gpu_quota_repo, service_gpu_repo
from www.apiclient.regionapi import RegionInvokeApi

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class GPUService(object):
    """GPU 服务类"""

    def get_team_gpu_quota(self, team_id):
        """
        获取团队GPU配额
        :param team_id: 团队ID
        :return: 配额信息字典
        """
        try:
            quota = gpu_quota_repo.get_by_tenant_id(team_id)
            if not quota:
                # 返回默认配额（不限制）
                return {
                    'tenant_id': team_id,
                    'gpu_limit': 0,
                    'gpu_memory_limit': 0
                }
            return {
                'tenant_id': quota.tenant_id,
                'gpu_limit': quota.gpu_limit,
                'gpu_memory_limit': quota.gpu_memory_limit,
                'create_time': quota.create_time.isoformat() if quota.create_time else None,
                'update_time': quota.update_time.isoformat() if quota.update_time else None
            }
        except Exception as e:
            logger.exception("获取团队GPU配额失败: team_id={}, error={}".format(team_id, str(e)))
            raise

    def set_team_gpu_quota(self, team_id, gpu_limit, gpu_memory_limit):
        """
        设置团队GPU配额
        :param team_id: 团队ID
        :param gpu_limit: GPU卡数限制
        :param gpu_memory_limit: GPU显存限制(MB)
        :return: 配额信息字典
        """
        try:
            quota = gpu_quota_repo.create_or_update(
                tenant_id=team_id,
                gpu_limit=gpu_limit,
                gpu_memory_limit=gpu_memory_limit
            )
            return {
                'tenant_id': quota.tenant_id,
                'gpu_limit': quota.gpu_limit,
                'gpu_memory_limit': quota.gpu_memory_limit,
                'create_time': quota.create_time.isoformat() if quota.create_time else None,
                'update_time': quota.update_time.isoformat() if quota.update_time else None
            }
        except Exception as e:
            logger.exception("设置团队GPU配额失败: team_id={}, error={}".format(team_id, str(e)))
            raise

    def get_team_gpu_usage(self, team_id):
        """
        获取团队GPU使用情况
        :param team_id: 团队ID
        :return: 使用情况字典
        """
        try:
            # 获取配额
            quota = gpu_quota_repo.get_by_tenant_id(team_id)
            gpu_limit = quota.gpu_limit if quota else 0
            gpu_memory_limit = quota.gpu_memory_limit if quota else 0

            # 统计团队所有服务的GPU使用
            used_gpu = 0
            used_gpu_memory = 0

            gpu_configs = service_gpu_repo.get_by_tenant_id(team_id)
            for config in gpu_configs:
                if config.enable_gpu:
                    used_gpu += config.gpu_count
                    used_gpu_memory += config.gpu_memory

            # 计算使用率
            usage_rate = 0.0
            if gpu_limit > 0:
                usage_rate = round((used_gpu / gpu_limit) * 100, 2)

            return {
                'tenant_id': team_id,
                'used_gpu': used_gpu,
                'used_gpu_memory': used_gpu_memory,
                'gpu_limit': gpu_limit,
                'gpu_memory_limit': gpu_memory_limit,
                'usage_rate': usage_rate
            }
        except Exception as e:
            logger.exception("获取团队GPU使用情况失败: team_id={}, error={}".format(team_id, str(e)))
            raise

    def validate_gpu_quota(self, team_id, request_gpu, request_memory, exclude_service_id=None):
        """
        验证GPU配额是否充足
        :param team_id: 团队ID
        :param request_gpu: 请求的GPU卡数
        :param request_memory: 请求的显存(MB)
        :param exclude_service_id: 排除的服务ID（用于更新服务时）
        :return: (是否通过, 错误信息)
        """
        try:
            usage = self.get_team_gpu_usage(team_id)

            # 如果是更新服务，需要减去原有的使用量
            if exclude_service_id:
                old_config = service_gpu_repo.get_by_service_id(exclude_service_id)
                if old_config and old_config.enable_gpu:
                    usage['used_gpu'] -= old_config.gpu_count
                    usage['used_gpu_memory'] -= old_config.gpu_memory

            # 检查GPU卡数配额
            if usage['gpu_limit'] > 0:
                if usage['used_gpu'] + request_gpu > usage['gpu_limit']:
                    msg = "GPU卡数配额不足: 团队配额 {} 张，已使用 {} 张，本次请求 {} 张，超出 {} 张".format(
                        usage['gpu_limit'],
                        usage['used_gpu'],
                        request_gpu,
                        usage['used_gpu'] + request_gpu - usage['gpu_limit']
                    )
                    return False, msg

            # 检查显存配额
            if usage['gpu_memory_limit'] > 0:
                if usage['used_gpu_memory'] + request_memory > usage['gpu_memory_limit']:
                    msg = "GPU显存配额不足: 团队配额 {} MB，已使用 {} MB，本次请求 {} MB，超出 {} MB".format(
                        usage['gpu_memory_limit'],
                        usage['used_gpu_memory'],
                        request_memory,
                        usage['used_gpu_memory'] + request_memory - usage['gpu_memory_limit']
                    )
                    return False, msg

            return True, ""
        except Exception as e:
            logger.exception("验证GPU配额失败: team_id={}, error={}".format(team_id, str(e)))
            raise

    def get_service_gpu_config(self, service_id):
        """
        获取组件GPU配置
        :param service_id: 服务ID
        :return: GPU配置字典
        """
        try:
            config = service_gpu_repo.get_by_service_id(service_id)
            if not config:
                # 返回默认配置
                return {
                    'service_id': service_id,
                    'enable_gpu': False,
                    'gpu_count': 0,
                    'gpu_memory': 0,
                    'gpu_cores': 0,
                    'gpu_model_preference': ''
                }
            return {
                'service_id': config.service_id,
                'enable_gpu': config.enable_gpu,
                'gpu_count': config.gpu_count,
                'gpu_memory': config.gpu_memory,
                'gpu_cores': config.gpu_cores,
                'gpu_model_preference': config.gpu_model_preference or '',
                'create_time': config.create_time.isoformat() if config.create_time else None,
                'update_time': config.update_time.isoformat() if config.update_time else None
            }
        except Exception as e:
            logger.exception("获取组件GPU配置失败: service_id={}, error={}".format(service_id, str(e)))
            raise

    def set_service_gpu_config(self, team_id, service_id, enable_gpu, gpu_count=0,
                               gpu_memory=0, gpu_cores=0, gpu_model_preference=''):
        """
        设置组件GPU配置
        :param team_id: 团队ID
        :param service_id: 服务ID
        :param enable_gpu: 是否启用GPU
        :param gpu_count: GPU卡数
        :param gpu_memory: GPU显存(MB)
        :param gpu_cores: GPU算力百分比
        :param gpu_model_preference: GPU型号偏好
        :return: GPU配置字典
        """
        try:
            # 如果启用GPU，需要验证配额
            if enable_gpu:
                is_valid, error_msg = self.validate_gpu_quota(
                    team_id, gpu_count, gpu_memory, exclude_service_id=service_id
                )
                if not is_valid:
                    raise Exception(error_msg)

            config = service_gpu_repo.create_or_update(
                service_id=service_id,
                enable_gpu=enable_gpu,
                gpu_count=gpu_count,
                gpu_memory=gpu_memory,
                gpu_cores=gpu_cores,
                gpu_model_preference=gpu_model_preference
            )

            return {
                'service_id': config.service_id,
                'enable_gpu': config.enable_gpu,
                'gpu_count': config.gpu_count,
                'gpu_memory': config.gpu_memory,
                'gpu_cores': config.gpu_cores,
                'gpu_model_preference': config.gpu_model_preference or '',
                'create_time': config.create_time.isoformat() if config.create_time else None,
                'update_time': config.update_time.isoformat() if config.update_time else None
            }
        except Exception as e:
            logger.exception("设置组件GPU配置失败: service_id={}, error={}".format(service_id, str(e)))
            raise

    def delete_service_gpu_config(self, service_id):
        """
        删除组件GPU配置
        :param service_id: 服务ID
        """
        try:
            service_gpu_repo.delete_by_service_id(service_id)
        except Exception as e:
            logger.exception("删除组件GPU配置失败: service_id={}, error={}".format(service_id, str(e)))
            raise


# 创建单例
gpu_service = GPUService()
