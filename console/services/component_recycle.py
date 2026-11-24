"""Team/region-scoped recovery of the same component and its retained storage."""
from django.db import IntegrityError, transaction

from console.models.main import ServiceRecycleBin, ServiceRelationRecycleBin
from console.services.delivery_manifest import DeliveryError
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroup, ServiceGroupRelation, TenantServiceInfo, TenantServiceRelation


class RecycleError(DeliveryError):
    pass


class ComponentRecycleService:
    def __init__(self, region_api=None):
        self.region = region_api or RegionInvokeApi()

    def rows(self, tenant, region):
        return ServiceRecycleBin.objects.filter(tenant_id=tenant.tenant_id, service_region=region).order_by('-ID')

    def get(self, tenant, region, service_id, lock=False):
        rows = self.rows(tenant, region)
        if lock:
            rows = rows.select_for_update()
        row = rows.filter(service_id=service_id).first()
        if row is None:
            raise RecycleError('回收记录不存在', 404)
        return row

    def app(self, row):
        metadata = row.recovery_metadata if isinstance(row.recovery_metadata, dict) else {}
        app_id = metadata.get('app_id')
        if app_id is None:
            relation = ServiceGroupRelation.objects.filter(tenant_id=row.tenant_id,
                                                           region_name=row.service_region,
                                                           service_id=row.service_id).first()
            app_id = relation.group_id if relation else None
        return ServiceGroup.objects.filter(ID=app_id, tenant_id=row.tenant_id, region_name=row.service_region).first()

    def public(self, row):
        app = self.app(row)
        return {
            'service_id': row.service_id,
            'service_alias': row.service_alias,
            'service_cname': row.service_cname,
            'service_region': row.service_region,
            'extend_method': row.extend_method,
            'app_id': app.ID if app else None,
            'app_name': app.group_name if app else '',
            'recycled_at': row.update_time.isoformat(),
            'recovery_metadata_available': bool(row.recovery_metadata)
        }

    def _fields(self, row, require_snapshot=True):
        metadata = row.recovery_metadata if isinstance(row.recovery_metadata, dict) else {}
        source = metadata.get('service')
        if not isinstance(source, dict):
            if require_snapshot:
                raise RecycleError('旧回收记录缺少完整配置，无法保证原虚拟机和磁盘恢复', 409)
            source = row.to_dict()
        names = {field.attname for field in TenantServiceInfo._meta.concrete_fields if not field.primary_key}
        data = {key: value for key, value in source.items() if key in names}
        for key in ('service_id', 'tenant_id', 'service_alias', 'service_region'):
            if data.get(key) != getattr(row, key):
                raise RecycleError('回收记录身份不一致，已保留原数据', 409)
        return data

    def _validate_vm(self, tenant, row):
        try:
            response, body = self.region.get_vm_recycle_recovery(row.service_region, tenant.tenant_name, row.service_alias)
        except self.region.CallApiError as error:
            raise RecycleError('集群无法确认原虚拟机和磁盘，回收记录已保留', 409) from error
        bean = body.get('bean', {}) if isinstance(body, dict) else {}
        if not isinstance(bean, dict):
            raise RecycleError('集群返回的磁盘信息无效，回收记录已保留', 409)
        disks = bean.get('disks')
        if (response.status != 200 or bean.get('service_id') != row.service_id or bean.get('storage_ready') is not True
                or not bean.get('vm_uid') or not isinstance(disks, list) or not disks
                or any(not isinstance(disk, dict) or not disk.get('disk_key') or not disk.get('pvc_uid')
                       for disk in disks) or len({disk['disk_key']
                                                  for disk in disks}) != len(disks)):
            raise RecycleError('原虚拟机或磁盘未就绪，不能恢复；不会创建空盘替代', 409)
        return bean

    def capture_vm(self, tenant, service):
        return self._validate_vm(tenant, service)

    @transaction.atomic
    def restore(self, tenant, region, service_id):
        active = TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id, service_region=region,
                                                  service_id=service_id).first()
        if active and not self.rows(tenant, region).filter(service_id=service_id).exists():
            return {'service_id': active.service_id, 'service_alias': active.service_alias}
        row = self.get(tenant, region, service_id, lock=True)
        app = self.app(row)
        if app is None:
            raise RecycleError('原应用不存在，无法恢复到原位置；回收记录已保留', 409)
        data = self._fields(row)
        if row.recovery_metadata.get('app_k8s_name') != app.k8s_app:
            raise RecycleError('原应用标识已变化，回收记录已保留', 409)
        if TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id, service_alias=row.service_alias).exists():
            raise RecycleError('组件名称已被占用，回收记录已保留', 409)
        if row.extend_method == 'vm' and row.create_status == 'complete':
            observed = self._validate_vm(tenant, row)
            saved = row.recovery_metadata.get('vm', {})
            if not isinstance(saved, dict):
                raise RecycleError('原虚拟机记录无效，回收记录已保留', 409)
            saved_disks = {d.get('disk_key'): d.get('pvc_uid') for d in saved.get('disks', []) if isinstance(d, dict)}
            actual_disks = {d.get('disk_key'): d.get('pvc_uid') for d in observed['disks']}
            if (saved.get('vm_uid') != observed['vm_uid'] or not saved_disks or saved_disks != actual_disks
                    or observed.get('k8s_component_name') != data.get('k8s_component_name')
                    or observed.get('vm_name') != '{}-{}'.format(app.k8s_app, data.get('k8s_component_name'))):
                raise RecycleError('原虚拟机或磁盘身份已变化，回收记录已保留', 409)
        try:
            restored = TenantServiceInfo.objects.create(**data)
        except IntegrityError as error:
            raise RecycleError('组件身份冲突，回收记录已保留', 409) from error
        relation, _ = ServiceGroupRelation.objects.get_or_create(tenant_id=tenant.tenant_id,
                                                                 region_name=region,
                                                                 service_id=service_id,
                                                                 defaults={'group_id': app.ID})
        if relation.group_id != app.ID:
            raise RecycleError('原应用关系已变化，回收记录已保留', 409)
        relations = ServiceRelationRecycleBin.objects.select_for_update().filter(tenant_id=tenant.tenant_id,
                                                                                 service_id=service_id)
        for relation in relations:
            if TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id,
                                                service_region=region,
                                                service_id=relation.dep_service_id).exists():
                TenantServiceRelation.objects.get_or_create(tenant_id=tenant.tenant_id,
                                                            service_id=service_id,
                                                            dep_service_id=relation.dep_service_id,
                                                            defaults={
                                                                'dep_service_type': relation.dep_service_type,
                                                                'dep_order': relation.dep_order
                                                            })
        relations.delete()
        row.delete()
        return {'service_id': restored.service_id, 'service_alias': restored.service_alias, 'app_id': app.ID}

    @transaction.atomic
    def purge(self, tenant, region, service_id, user):
        from console.services.app_actions.app_manage import AppManageService

        row = self.get(tenant, region, service_id, lock=True)
        if TenantServiceInfo.objects.filter(service_id=service_id).exists():
            raise RecycleError('组件已恢复或状态冲突，请刷新后重试', 409)
        if row.create_status == 'complete':
            try:
                remote = self.region.get_service_info(region, tenant.tenant_name, row.service_alias)
                if not isinstance(remote, dict) or remote.get('bean', {}).get('serviceId') != service_id:
                    raise RecycleError('集群组件身份与回收记录不一致，已停止删除', 409)
                status = self.region.check_service_status(region, tenant.tenant_name, row.service_alias, tenant.enterprise_id)
                if not isinstance(status, dict) or status.get('bean',
                                                              {}).get('cur_status') not in ('closed', 'stopped', 'undeploy'):
                    raise RecycleError('组件未确认关闭，不能永久删除', 409)
            except self.region.CallApiError as error:
                if error.status != 404:
                    raise RecycleError('无法核对集群状态，回收记录已保留', 502) from error
        # Reuse the normal deletion checks and cleanup in this transaction. The
        # temporary active row is not visible to other requests before commit.
        service = TenantServiceInfo.objects.create(**self._fields(row, require_snapshot=False))
        code, message = AppManageService().delete(user, tenant, service, is_force=True)
        if code != 200:
            raise RecycleError(message, code if 400 <= code < 600 else 409)
        ServiceRelationRecycleBin.objects.filter(tenant_id=tenant.tenant_id, service_id=service_id).delete()
        row.delete()
        return {'service_id': service_id, 'deleted': True}
