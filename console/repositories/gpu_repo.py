# -*- coding: utf8 -*-
"""
GPU 数据访问层
提供GPU配额和配置的数据库操作
"""
import logging

from www.models.main import TenantGPUQuota, TenantServiceGPU
from console.repositories.team_repo import team_repo

logger = logging.getLogger("default")


class GPUQuotaRepository(object):
    """GPU配额数据访问"""

    def get_by_tenant_id(self, tenant_id):
        """
        根据租户ID获取GPU配额
        :param tenant_id: 租户ID
        :return: TenantGPUQuota对象或None
        """
        try:
            return TenantGPUQuota.objects.filter(tenant_id=tenant_id).first()
        except TenantGPUQuota.DoesNotExist:
            return None
        except Exception as e:
            logger.exception("获取GPU配额失败: tenant_id={}, error={}".format(tenant_id, str(e)))
            raise

    def create_or_update(self, tenant_id, gpu_limit, gpu_memory_limit):
        """
        创建或更新GPU配额
        :param tenant_id: 租户ID
        :param gpu_limit: GPU卡数限制
        :param gpu_memory_limit: GPU显存限制(MB)
        :return: TenantGPUQuota对象
        """
        try:
            quota, created = TenantGPUQuota.objects.update_or_create(
                tenant_id=tenant_id,
                defaults={
                    'gpu_limit': gpu_limit,
                    'gpu_memory_limit': gpu_memory_limit
                }
            )
            return quota
        except Exception as e:
            logger.exception("创建或更新GPU配额失败: tenant_id={}, error={}".format(tenant_id, str(e)))
            raise

    def delete_by_tenant_id(self, tenant_id):
        """
        删除GPU配额
        :param tenant_id: 租户ID
        """
        try:
            TenantGPUQuota.objects.filter(tenant_id=tenant_id).delete()
        except Exception as e:
            logger.exception("删除GPU配额失败: tenant_id={}, error={}".format(tenant_id, str(e)))
            raise

    def list_all(self):
        """
        获取所有GPU配额
        :return: QuerySet
        """
        try:
            return TenantGPUQuota.objects.all()
        except Exception as e:
            logger.exception("获取所有GPU配额失败: error={}".format(str(e)))
            raise


class ServiceGPURepository(object):
    """组件GPU配置数据访问"""

    def get_by_service_id(self, service_id):
        """
        根据服务ID获取GPU配置
        :param service_id: 服务ID
        :return: TenantServiceGPU对象或None
        """
        try:
            return TenantServiceGPU.objects.filter(service_id=service_id).first()
        except TenantServiceGPU.DoesNotExist:
            return None
        except Exception as e:
            logger.exception("获取组件GPU配置失败: service_id={}, error={}".format(service_id, str(e)))
            raise

    def get_by_tenant_id(self, tenant_id):
        """
        根据租户ID获取所有GPU配置
        :param tenant_id: 租户ID
        :return: QuerySet
        """
        try:
            # 需要通过service表关联查询
            from console.repositories.app import service_repo
            services = service_repo.get_services_by_tenant(tenant_id)
            service_ids = [s.service_id for s in services]
            return TenantServiceGPU.objects.filter(service_id__in=service_ids)
        except Exception as e:
            logger.exception("根据租户ID获取GPU配置失败: tenant_id={}, error={}".format(tenant_id, str(e)))
            raise

    def create_or_update(self, service_id, enable_gpu, gpu_count=0,
                        gpu_memory=0, gpu_cores=0, gpu_model_preference=''):
        """
        创建或更新组件GPU配置
        :param service_id: 服务ID
        :param enable_gpu: 是否启用GPU
        :param gpu_count: GPU卡数
        :param gpu_memory: GPU显存(MB)
        :param gpu_cores: GPU算力百分比
        :param gpu_model_preference: GPU型号偏好
        :return: TenantServiceGPU对象
        """
        try:
            config, created = TenantServiceGPU.objects.update_or_create(
                service_id=service_id,
                defaults={
                    'enable_gpu': enable_gpu,
                    'gpu_count': gpu_count,
                    'gpu_memory': gpu_memory,
                    'gpu_cores': gpu_cores,
                    'gpu_model_preference': gpu_model_preference or ''
                }
            )
            return config
        except Exception as e:
            logger.exception("创建或更新组件GPU配置失败: service_id={}, error={}".format(service_id, str(e)))
            raise

    def delete_by_service_id(self, service_id):
        """
        删除组件GPU配置
        :param service_id: 服务ID
        """
        try:
            TenantServiceGPU.objects.filter(service_id=service_id).delete()
        except Exception as e:
            logger.exception("删除组件GPU配置失败: service_id={}, error={}".format(service_id, str(e)))
            raise

    def get_enabled_gpu_services(self, tenant_id=None):
        """
        获取启用GPU的服务列表
        :param tenant_id: 租户ID（可选）
        :return: QuerySet
        """
        try:
            queryset = TenantServiceGPU.objects.filter(enable_gpu=True)
            if tenant_id:
                from console.repositories.app import service_repo
                services = service_repo.get_services_by_tenant(tenant_id)
                service_ids = [s.service_id for s in services]
                queryset = queryset.filter(service_id__in=service_ids)
            return queryset
        except Exception as e:
            logger.exception("获取启用GPU的服务失败: tenant_id={}, error={}".format(tenant_id, str(e)))
            raise


# 创建单例
gpu_quota_repo = GPUQuotaRepository()
service_gpu_repo = ServiceGPURepository()
