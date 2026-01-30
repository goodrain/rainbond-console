# -*- coding: utf-8 -*-
"""
Gray release record repository
"""
from django.db.models import Q
from console.models.main import GrayReleaseRecord, GrayReleaseStatus


class GrayReleaseRepo(object):
    """灰度发布记录仓储"""

    def create(self, **kwargs):
        """创建灰度发布记录"""
        return GrayReleaseRecord.objects.create(**kwargs)

    def get_by_id(self, record_id):
        """根据ID获取记录"""
        try:
            return GrayReleaseRecord.objects.get(ID=record_id)
        except GrayReleaseRecord.DoesNotExist:
            return None

    def get_active_record_by_app_and_template(self, tenant_id, app_id, template_id):
        """获取指定应用和模板的活跃灰度记录"""
        return GrayReleaseRecord.objects.filter(
            tenant_id=tenant_id,
            app_id=app_id,
            template_id=template_id,
            status=GrayReleaseStatus.ACTIVE
        ).first()

    def get_active_record_by_domain(self, tenant_id, app_id, domain_name):
        """根据域名获取活跃的灰度记录"""
        return GrayReleaseRecord.objects.filter(
            tenant_id=tenant_id,
            app_id=app_id,
            domain_name=domain_name,
            status=GrayReleaseStatus.ACTIVE
        ).first()

    def list_by_app(self, tenant_id, app_id, status=None):
        """获取应用的灰度发布记录列表"""
        q = Q(tenant_id=tenant_id, app_id=app_id)
        if status:
            q &= Q(status=status)
        return GrayReleaseRecord.objects.filter(q).order_by('-create_time')

    def list_by_tenant(self, tenant_id, status=None):
        """获取租户的灰度发布记录列表"""
        q = Q(tenant_id=tenant_id)
        if status:
            q &= Q(status=status)
        return GrayReleaseRecord.objects.filter(q).order_by('-create_time')

    def update_gray_ratio(self, record, gray_ratio):
        """更新灰度比例"""
        record.gray_ratio = gray_ratio
        record.save()
        return record

    def update_status(self, record, status):
        """更新状态"""
        record.status = status
        record.save()
        return record

    def delete_by_app(self, tenant_id, app_id):
        """删除应用的所有灰度记录"""
        GrayReleaseRecord.objects.filter(
            tenant_id=tenant_id,
            app_id=app_id
        ).delete()

    def get_gray_info_by_upgrade_group(self, tenant_id, app_id, upgrade_group_id):
        """根据 upgrade_group_id 获取灰度信息

        Returns:
            dict: 包含灰度信息的字典，如果该服务组不属于灰度发布则返回 None
                - is_gray_release: bool
                - gray_release_type: 'original' 或 'gray'
                - record: GrayReleaseRecord 对象
        """
        # 查找该 upgrade_group_id 是否是原始服务组
        record = GrayReleaseRecord.objects.filter(
            tenant_id=tenant_id,
            app_id=app_id,
            original_upgrade_group_id=upgrade_group_id,
            status=GrayReleaseStatus.ACTIVE
        ).first()

        if record:
            return {
                'is_gray_release': True,
                'gray_release_type': 'original',
                'record': record
            }

        # 查找该 upgrade_group_id 是否是灰度服务组
        record = GrayReleaseRecord.objects.filter(
            tenant_id=tenant_id,
            app_id=app_id,
            gray_upgrade_group_id=upgrade_group_id,
            status=GrayReleaseStatus.ACTIVE
        ).first()

        if record:
            return {
                'is_gray_release': True,
                'gray_release_type': 'gray',
                'record': record
            }

        return None

    def get_service_mapping_by_service_id(self, tenant_id, service_id):
        """根据服务ID获取其在灰度发布中的映射关系

        Returns:
            dict: 包含服务映射信息的字典，如果该服务不属于灰度发布则返回 None
                - is_gray_release: bool
                - gray_release_type: 'original' 或 'gray'
                - paired_service_id: 配对的服务ID
                - service_cname: 服务名称
                - record: GrayReleaseRecord 对象
        """
        import json
        import logging
        logger = logging.getLogger('default')

        # 查找所有活跃的灰度发布记录
        records = GrayReleaseRecord.objects.filter(
            tenant_id=tenant_id,
            status=GrayReleaseStatus.ACTIVE
        )

        for record in records:
            if not record.service_mappings:
                continue

            try:
                service_mappings = json.loads(record.service_mappings)
                for mapping in service_mappings:
                    # 检查是否是原始服务
                    if mapping['original_service_id'] == service_id:
                        return {
                            'is_gray_release': True,
                            'gray_release_type': 'original',
                            'paired_service_id': mapping['gray_service_id'],
                            'service_cname': mapping['original_service_cname'],
                            'record': record
                        }
                    # 检查是否是灰度服务
                    elif mapping['gray_service_id'] == service_id:
                        return {
                            'is_gray_release': True,
                            'gray_release_type': 'gray',
                            'paired_service_id': mapping['original_service_id'],
                            'service_cname': mapping['gray_service_cname'],
                            'record': record
                        }
            except Exception as e:
                logger.warning(f"Failed to parse service_mappings for record {record.ID}: {e}")
                continue

        return None


gray_release_repo = GrayReleaseRepo()
