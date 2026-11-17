"""Recycle APIs with existing team/app read, create and delete permissions."""
from typing import Any, TYPE_CHECKING, cast
from rest_framework.response import Response

from console.services.component_recycle import ComponentRecycleService, RecycleError
from console.services.delivery_access import team_access
from console.services.delivery_manifest import DeliveryError
from console.services.operation_log import OperationType, operation_log_service
from console.utils.cache_decorators import never_cache
from console.views.base import JWTAuthApiView
from www.models.main import Tenants, TenantRegionInfo, TenantServiceInfo, ServiceGroupRelation
from www.utils.return_message import general_message

if TYPE_CHECKING:
    from rest_framework.request import Request


class ComponentRecycleAPI(JWTAuthApiView):
    def initial(self, request: "Request", *args: Any, **kwargs: Any) -> None:
        self.perform_authentication(request)
        self.check_permissions(request)
        super().initial(request, *args, **kwargs)
        self.recycle = ComponentRecycleService()

    def handle_exception(self, error: Exception) -> Response:
        if isinstance(error, DeliveryError):
            return Response(general_message(error.status, 'failed', str(error)), status=error.status)
        return super().handle_exception(error)

    def scope(self, request: "Request", team_name: str) -> tuple[Tenants, str]:
        region = request.GET.get('region_name') or request.META.get('HTTP_X_REGION_NAME')
        if not isinstance(region, str) or not region:
            raise RecycleError('请选择集群', 400)
        tenant = Tenants.objects.filter(tenant_name=team_name, enterprise_id=self.user.enterprise_id).first()
        if tenant is None or not TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, region_name=region).exists():
            raise RecycleError('团队或集群不存在', 404)
        return tenant, region

    def authorize(self, row: Any, team_name: str, code: int) -> None:
        app = self.recycle.app(row)
        team_access(self.user, team_name, code, app.ID if app else None, self.is_enterprise_admin)


class ComponentRecycleListView(ComponentRecycleAPI):
    @never_cache
    def get(self, request: "Request", team_name: str) -> Response:
        tenant, region = self.scope(request, team_name)
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except (ValueError, TypeError):
            raise RecycleError('页码无效', 400)
        rows = []
        for row in self.recycle.rows(tenant, region).iterator():
            try:
                self.authorize(row, team_name, 300002)
            except DeliveryError as error:
                if error.status == 403:
                    continue
                raise
            item = self.recycle.public(row)
            for key, code in (('can_restore', 300013), ('can_purge', 300004)):
                try:
                    self.authorize(row, team_name, code)
                    item[key] = bool(item['recovery_metadata_available'] and item['app_id']) if key == 'can_restore' else True
                except DeliveryError as error:
                    if error.status != 403:
                        raise
                    item[key] = False
            rows.append(item)
        return Response(general_message(200, 'success', '查询成功', list=rows[(page - 1) * 20:page * 20], total=len(rows)))


class ComponentRecycleRestoreView(ComponentRecycleAPI):
    @never_cache
    def post(self, request: "Request", team_name: str, service_id: str) -> Response:
        tenant, region = self.scope(request, team_name)
        try:
            row = self.recycle.get(tenant, region, service_id)
        except RecycleError as error:
            if error.status != 404:
                raise
            active = TenantServiceInfo.objects.filter(tenant_id=tenant.tenant_id, service_region=region,
                                                      service_id=service_id).first()
            relation = ServiceGroupRelation.objects.filter(tenant_id=tenant.tenant_id,
                                                           service_id=service_id,
                                                           region_name=region).first()
            if active is None or relation is None:
                raise error
            team_access(self.user, team_name, 300013, relation.group_id, self.is_enterprise_admin)
        else:
            self.authorize(row, team_name, 300013)
        result = self.recycle.restore(tenant, region, service_id)
        operation_log_service.create_log(self.user,
                                         OperationType.COMPONENT_MANAGE,
                                         '从回收站恢复了组件',
                                         enterprise_id=cast(str, tenant.enterprise_id),
                                         team_name=team_name,
                                         app_id=result.get('app_id', 0),
                                         service_alias=result['service_alias'])
        return Response(general_message(200, 'success', '已恢复组件，虚拟机保持关闭，请检查后启动', bean=result))


class ComponentRecyclePurgeView(ComponentRecycleAPI):
    @never_cache
    def delete(self, request: "Request", team_name: str, service_id: str) -> Response:
        tenant, region = self.scope(request, team_name)
        row = self.recycle.get(tenant, region, service_id)
        self.authorize(row, team_name, 300004)
        result = self.recycle.purge(tenant, region, service_id, self.user)
        operation_log_service.create_log(self.user,
                                         OperationType.COMPONENT_MANAGE,
                                         '永久删除了回收站组件',
                                         enterprise_id=cast(str, tenant.enterprise_id),
                                         team_name=team_name,
                                         service_alias=row.service_alias,
                                         service_cname=row.service_cname)
        return Response(general_message(200, 'success', '已永久删除，集群存储将在后台回收', bean=result))
