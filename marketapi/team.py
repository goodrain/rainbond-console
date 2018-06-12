# -*- coding: utf8 -*-
"""
  Created on 2018/6/11.
"""
import logging

from rest_framework import status

from base_view import EnterpriseMarketAPIView
from console.repositories.region_repo import region_repo
from console.services.enterprise_services import enterprise_services
from console.services.perm_services import perm_services
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.user_services import user_services

logger = logging.getLogger("default")


class InitTeamAndRegionView(EnterpriseMarketAPIView):
    def post(self, request, *args, **kwargs):
        """
        创建租户并开通数据中心
        ---
        parameters:
            - name: region_name
              description: 数据中心名称
              required: true
              type: string
              paramType: form
            - name: team_alias
              description: 团队名称
              required: true
              type: string
              paramType: form

        """
        try:
            team = None
            team_alias = request.data.get("team_alias", None)
            region_name = request.data.get("region_name", None)
            need_creare_team = False
            if not team_alias:
                need_creare_team = True
                team_alias = "{0}的团队".format(request.user.nick_name)
            else:
                team = team_services.get_team_by_team_alias(team_alias)
                if not team:
                    return self.error_response(code=status.HTTP_404_NOT_FOUND, msg="team is not found",
                                               msg_show="团队{0}不存在".format(team_alias))
            if not region_name:
                return self.error_response(code=status.HTTP_406_NOT_ACCEPTABLE, msg='region name is null!',
                                           msg_show="数据中心名称不能为空")
            region = region_repo.get_region_by_region_name(region_name)
            if not region:
                return self.error_response(code=status.HTTP_404_NOT_FOUND, msg="region is not found",
                                           msg_show="数据中心{0}不存在".format(region_name))
            enterprise = enterprise_services.get_enterprise_by_enterprise_id(request.user.enterprise_id)
            if not enterprise:
                return self.error_response(code=status.HTTP_404_NOT_FOUND, msg="enterprise is not found",
                                           msg_show="用户所在企业不存在")
            if need_creare_team:
                code, msg, team = team_services.create_team(request.user, enterprise, [region_name], team_alias)
                if not code:
                    return self.error_response(code=code, msg="create team error",
                                               msg_show="初始化团队失败")
                perm_info = {
                    "user_id": request.user.user_id,
                    "tenant_id": team.ID,
                    "identity": "owner",
                    "enterprise_id": enterprise.pk
                }
                perm_services.add_user_tenant_perm(perm_info)
                # 创建用户在企业的权限
                user_services.make_user_as_admin_for_enterprise(request.user.user_id, enterprise.enterprise_id)
                # 为团队开通默认数据中心并在数据中心创建租户
                code, msg, tenant_region = region_services.create_tenant_on_region(team.tenant_name, team.region)
                if code != 200:
                    if not code:
                        return self.error_response(code=code, msg="create tenant on region error",
                                                   msg_show="数据中心创建团队失败")

                request.user.is_active = True
                request.user.save()

                result = self.success_response(team.to_dict())
            else:
                code, msg, tenant_region = region_services.create_tenant_on_region(team.tenant_name, region_name)
                if code != 200:
                    if not code:
                        return self.error_response(code=code, msg="create tenant on region error",
                                                   msg_show="数据中心创建团队失败")
                request.user.is_active = True
                request.user.save()

                result = self.success_response(team.to_dict())
                
        except Exception as e:
            logger.exception(e)
            result = self.error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "system error", "系统异常")
        return result
