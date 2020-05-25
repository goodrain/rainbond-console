# -*- coding: utf-8 -*-
import logging

from rest_framework.response import Response

from console.exception.exceptions import ParamsError
from console.exception.exceptions import UserNotExistError
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.views.base import RegionTenantHeaderView

from www.models.main import Tenants
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class TeamAddUserView(RegionTenantHeaderView):
    def post(self, request, team_name, *args, **kwargs):
        """
        团队中添加新用户给用户分配一个角色
        ---
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: user_ids
              description: 添加成员id 格式 {'user_ids':'1,2'}
              required: true
              type: string
              paramType: body
            - name: role_ids
              description: 选择角色 格式{"role_ids": "1,2,3"}
              required: true
              type: string
              paramType: body
        """
        try:
            user_ids = request.data.get('user_ids', None)
            role_ids = request.data.get('role_ids', None)
            if not user_ids:
                raise ParamsError("用户名为空")
            if not role_ids:
                raise ParamsError("角色ID为空")
            try:
                user_ids = [int(user_id) for user_id in user_ids.split(",")]
                role_ids = [int(user_id) for user_id in role_ids.split(",")]
            except Exception as e:
                code = 400
                logger.exception(e)
                result = general_message(code, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=code)

            user_id = team_services.user_is_exist_in_team(user_list=user_ids, tenant_name=team_name)
            if user_id:
                user_obj = user_services.get_user_by_user_id(user_id=user_id)
                code = 400
                result = general_message(code, "user already exist", "用户{}已经存在".format(user_obj.nick_name))
                return Response(result, status=code)

            code = 200
            team = team_services.get_tenant(tenant_name=team_name)

            team_services.add_user_role_to_team(tenant=team, user_ids=user_ids, role_ids=role_ids)
            result = general_message(code, "success", "用户添加到{}成功".format(team_name))

        except ParamsError as e:
            logging.exception(e)
            code = 400
            result = general_message(code, "params is empty", e.message)
        except UserNotExistError as e:
            code = 400
            result = general_message(code, "user not exist", e.message)
        except Tenants.DoesNotExist as e:
            code = 400
            logger.exception(e)
            result = general_message(code, "tenant not exist", "{}团队不存在".format(team_name))
        return Response(result, status=code)
