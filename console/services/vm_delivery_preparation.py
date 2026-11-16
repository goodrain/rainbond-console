"""Prepare VM artifacts before handing an immutable version to normal delivery."""
import copy
import time
import uuid
from django.db import transaction
from console.services.delivery_manifest import (DeliveryError, baseline, digest, freeze_manifest, prepare, retain_artifacts)
from console.services.delivery_templates import actor


def is_vm(component):
    return bool(component.get('vm') or component.get('extend_method') == 'vm' or component.get('service_source') == 'vm_run')


def captured_component(component, result):
    component['share_image'] = result['image_name']
    component['image'] = result['image_name']
    component['git_url'] = ''
    vm = component.setdefault('vm', {})
    root = next((copy.deepcopy(disk) for disk in vm.get('disk_layout', []) if disk.get('disk_role') == 'root'), {
        'disk_key': 'disk',
        'volume_name': 'disk',
        'disk_role': 'root',
        'device_type': 'disk',
        'order_index': 0
    })
    root.update(image=result['image_name'], source_type='http-artifact', format='raw.gz', checksum='')
    if result.get('request_size'):
        root['request_size'] = result['request_size']
    for field in ('source_uri', 'download_url', 'image_url'):
        root.pop(field, None)
    vm.update(disk_layout=[root], boot_source_format='raw.gz', boot_mode=result.get('boot_mode') or vm.get('boot_mode', ''))
    # Installation prefers pre-existing attributes over the vm block. Remove the
    # original import definitions so the captured disk is the sole authority.
    component['component_k8s_attributes'] = [
        attribute for attribute in component.get('component_k8s_attributes', [])
        if attribute.get('name') not in ('vm_disk_imports', 'vm_disk_layout', 'vm_boot_source_format', 'vm_boot_mode')
    ]
    if component.get('service_volume_map_list'):
        component['service_volume_map_list'] = [
            volume for volume in component['service_volume_map_list']
            if volume.get('volume_name') == (root.get('volume_name') or 'disk')
        ]
        if result.get('capacity_gib'):
            for volume in component['service_volume_map_list']:
                volume['volume_capacity'] = result['capacity_gib']


class VMDeliveryPreparation:
    """Each tick does one bounded Region request, outside database transactions."""
    def __init__(self, service):
        self.service, self.m = service, service.m

    def submit(self, user, scope, data, request_id):
        self.service._identity(user, scope)
        key = 'vm-prepare:' + str(user.user_id) + ':' + str(request_id or uuid.uuid4())
        if len(key) > 128:
            raise DeliveryError('请求标识过长')
        fingerprint = digest(data)
        existing = self.m.DeliveryTask.objects.filter(request_key=key, template__in=self.service.repo.templates(scope)).first()
        if existing:
            if existing.payload.get('request_digest') != fingerprint:
                raise DeliveryError('此请求标识已用于不同的交付内容', 409)
            return existing
        source, _ = self.service.gateway.source(scope)
        with transaction.atomic():
            template = self.service.repo.templates(scope).select_for_update().first()
            if not template:
                raise DeliveryError('请先创建应用模板', 409)
            existing = self.m.DeliveryTask.objects.filter(request_key=key, template=template).first()
            if existing:
                if existing.payload.get('request_digest') != fingerprint:
                    raise DeliveryError('此请求标识已用于不同的交付内容', 409)
                return existing
            payload = {
                **data, 'template_name': template.name,
                'logo': template.logo,
                'template_description': template.description,
                'template_details': template.details
            }
            manifest = prepare(source, payload, template.id.hex)
            if not any(is_vm(component) for component in manifest['apps']):
                raise DeliveryError('此准备任务仅适用于包含虚拟机的交付版本')
            self._reserve(template, manifest['group_version'])
            ordinary = {
                'apps': [component for component in manifest['apps'] if not is_vm(component)],
                'plugins': manifest.get('plugins', [])
            }
            retain_artifacts(ordinary)
            manifest = freeze_manifest(manifest)
            manifest['delivery_source_region'] = scope['region_name']
            task = self.m.DeliveryTask.objects.create(template=template,
                                                      kind='vm_prepare',
                                                      actor_id=user.user_id,
                                                      actor_name=actor(user),
                                                      request_key=key,
                                                      payload={
                                                          'manifest': manifest,
                                                          'baseline': baseline(source),
                                                          'request_digest': fingerprint,
                                                          'deadline': int(time.time()) + 2 * 60 * 60
                                                      })
            for component in manifest['apps']:
                if is_vm(component):
                    self.m.DeliveryTaskItem.objects.create(task=task,
                                                           key=component['service_id'],
                                                           component=component,
                                                           result={'capture_id': 'delivery-' + uuid.uuid4().hex})
        return task

    def _reserve(self, template, version):
        if template.tasks.filter(kind='vm_prepare', status__in=['queued', 'running']).exists():
            raise DeliveryError('已有虚拟机镜像正在准备，请等待完成或取消后重试', 409)
        if template.versions.filter(version=version).exists() or any(
                task.payload.get('manifest', {}).get('group_version') == version
                for task in template.tasks.filter(kind='vm_prepare').exclude(status='cancelled')):
            raise DeliveryError('此版本号已存在或正在准备，请使用其他版本号', 409)

    def status(self, scope, task_id):
        task = self.service.repo.task(scope, task_id)
        if task.kind != 'vm_prepare':
            raise DeliveryError('任务类型无效', 409)
        return self.data(task)

    @staticmethod
    def data(task):
        return {
            'id':
            str(task.id),
            'status':
            task.status,
            'version_id':
            str(task.version_id or ''),
            'error':
            task.error,
            'version':
            task.payload['manifest']['group_version'],
            'components': [{
                'service_id': item.key,
                'name': item.component.get('service_cname', item.key),
                'status': item.status,
                'error': item.error
            } for item in task.items.order_by('key')]
        }

    def cancel(self, scope, task_id):
        with transaction.atomic():
            task = self.service.repo.task(scope, task_id)
            task = self.m.DeliveryTask.objects.select_for_update().get(pk=task.id)
            if task.kind != 'vm_prepare' or task.version_id:
                raise DeliveryError('此准备任务不能取消', 409)
            if task.status == 'cancelled':
                return task
            task.payload['stop_as'] = 'cancelled'
            task.status = 'running'
            task.save(update_fields=['payload', 'status', 'updated_at'])
        return task

    def retry(self, scope, task_id):
        with transaction.atomic():
            task = self.service.repo.task(scope, task_id)
            task = self.m.DeliveryTask.objects.select_for_update().get(pk=task.id)
            if task.kind != 'vm_prepare' or task.status != 'failed' or task.version_id:
                raise DeliveryError('此准备任务不能重试', 409)
            for item in task.items.exclude(status='success'):
                item.status, item.error = 'queued', ''
                item.result = {'capture_id': 'delivery-' + uuid.uuid4().hex}
                item.save()
            for field in ('stop_as', 'lease', 'lease_until'):
                task.payload.pop(field, None)
            task.payload['deadline'] = int(time.time()) + 2 * 60 * 60
            task.status, task.error = 'queued', ''
            task.save()
        return task

    def advance(self, task_id):
        lease = uuid.uuid4().hex
        with transaction.atomic():
            task = self.m.DeliveryTask.objects.select_for_update().select_related('template').get(pk=task_id)
            if task.kind != 'vm_prepare' or task.status not in ('queued', 'running'):
                return
            if task.payload.get('lease_until', 0) > time.time():
                return
            task.payload.update(lease=lease, lease_until=int(time.time()) + 60)
            task.status = 'running'
            if task.payload['deadline'] < time.time():
                task.payload['stop_as'] = 'failed'
                task.error = '虚拟机镜像准备超时，清理完成后可重试'
            task.save(update_fields=['payload', 'status', 'error', 'updated_at'])
        item = None
        try:
            if task.payload.get('stop_as'):
                item = task.items.exclude(result__released=True).order_by('key').first()
                if item:
                    self._release(task, item)
            else:
                item = task.items.exclude(status='success').order_by('key').first()
                if item:
                    self._step(task, item)
        except Exception as error:
            # Transport failures may follow a successful remote write. Retain
            # capture identity and release its readers before reporting failure.
            if item:
                item.error = item.error or (error.message if isinstance(error, DeliveryError) else '虚拟机镜像准备失败，请查看组件事件；清理后可重试')
                item.result['outcome'] = 'failed'
                item.status = 'releasing'
                self._persist(task, item)
        with transaction.atomic():
            live = self.m.DeliveryTask.objects.select_for_update().select_related('template').get(pk=task.id)
            if live.payload.get('lease') != lease:
                return
            live.payload.pop('lease', None)
            live.payload.pop('lease_until', None)
            if not live.payload.get('stop_as') and live.items.filter(status='failed').exists():
                live.payload['stop_as'] = 'failed'
                live.error = '虚拟机镜像准备失败'
            if live.payload.get('stop_as'):
                if not live.items.exclude(result__released=True).exists():
                    live.status = live.payload['stop_as']
            elif not live.items.exclude(status='success').exists():
                self._finalize(live)
            live.save()

    def _step(self, task, item):
        action = {
            'queued': 'prepare',
            'exporting': 'status',
            'ready': 'image',
            'building': 'status',
            'releasing': 'release'
        }.get(item.status)
        if not action:
            raise DeliveryError('虚拟机准备任务状态无效', 409)
        if action == 'release':
            self._release(task, item)
            return
        result = self.service.gateway.vm_capture(task, item, action)
        if result.get('capture_id') != item.result['capture_id']:
            raise DeliveryError('数据中心返回的镜像任务不匹配', 502)
        # Public artifact identity only. Never persist transport URLs or credentials.
        fields = ('image_name', 'event_id', 'share_id', 'boot_mode', 'request_size', 'capacity_gib')
        item.result.update({key: result[key] for key in fields if result.get(key)})
        item.event_id = item.result.get('event_id', '')
        phase = result.get('phase')
        if phase in ('success', 'failed'):
            if phase == 'success' and not item.result.get('image_name'):
                raise DeliveryError('数据中心未返回交付镜像', 502)
            item.result['outcome'] = phase
            item.status = 'releasing'
            if phase == 'failed':
                item.error = '系统盘镜像制作失败，请查看组件事件'
        elif phase in ('exporting', 'ready', 'building'):
            item.status = phase
        else:
            raise DeliveryError('数据中心未返回有效准备状态', 502)
        self._persist(task, item)

    def _release(self, task, item):
        result = self.service.gateway.vm_capture(task, item, 'release')
        if result.get('phase') == 'released':
            item.result['released'] = True
            item.status = 'success' if item.result.get('outcome') == 'success' else 'failed'
            self._persist(task, item)

    def _persist(self, task, item):
        """A late worker cannot overwrite a retried attempt or a newer lease."""
        with transaction.atomic():
            live = self.m.DeliveryTask.objects.select_for_update().get(pk=task.id)
            if live.payload.get('lease') != task.payload.get('lease') or live.status not in ('queued', 'running'):
                return False
            row = self.m.DeliveryTaskItem.objects.select_for_update().get(pk=item.id)
            if row.result.get('capture_id') != item.result.get('capture_id'):
                return False
            row.result, row.status, row.error, row.event_id = item.result, item.status, item.error, item.event_id
            row.save()
        return True

    def _finalize(self, task):
        self.m.DeliveryTemplate.objects.select_for_update().get(pk=task.template_id)
        if task.version_id:
            task.status = 'succeeded'
            return
        manifest = copy.deepcopy(task.payload['manifest'])
        results = {item.key: item.result for item in task.items.all()}
        for component in manifest['apps']:
            if is_vm(component):
                captured_component(component, results[component['service_id']])
        if task.template.versions.filter(version=manifest['group_version']).exists():
            task.status, task.error = 'failed', '版本号已存在，请重新创建版本'
            return
        task.version = self.m.DeliveryTemplateVersion.objects.create(template=task.template,
                                                                     version=manifest['group_version'],
                                                                     description=manifest['annotations']['version_info'],
                                                                     manifest=manifest,
                                                                     source_baseline=task.payload['baseline'],
                                                                     digest=digest(manifest),
                                                                     sync_id=task.id,
                                                                     creator_id=task.actor_id,
                                                                     creator_name=task.actor_name)
        task.status = 'succeeded'
