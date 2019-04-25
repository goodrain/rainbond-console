# coding: utf-8
"""升级从云市安装的应用"""
from console.repositories.market_app_repo import rainbond_app_repo
from console.services.group_service import group_service
from console.utils.response import MessageResponse
from console.views.base import RegionTenantHeaderView


class AppView(RegionTenantHeaderView):
    def get(self, request, group_id, *args, **kwargs):
        """查询当前组下的云市应用"""
        group = group_service.get_group_or_404(self.tenant, self.response_region, int(group_id))

        service_group_keys = group_service.get_group_service_sources(group.ID).values_list('group_key', flat=True)

        def yield_app_info():
            for group_key in set(service_group_keys):
                app_qs = rainbond_app_repo.get_market_app_qs_by_key(group_key=group_key)
                app = app_qs.first()
                group_version_list = app_qs.values_list('version', flat=True)
                yield {
                    'can_upgrade': '',
                    'not_upgrade_record_id': '',
                    'group_version_list': group_version_list,
                    'group_key': app.group_key,
                    'group_name': app.group_name,
                    'share_user': app.share_user,
                    'share_team': app.share_team,
                    'tenant_service_group_id': app.tenant_service_group_id,
                    'pic': app.pic,
                    'source': app.source,
                    'describe': app.describe,
                    'enterprise_id': app.enterprise_id,
                    'is_official': app.is_official,
                    'details': app.details,
                    'min_memory': group_service.group_service(app.app_template),
                }

        return MessageResponse(msg="success", list=[app_info for app_info in yield_app_info()])
