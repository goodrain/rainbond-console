from console.views.base import JWTAuthApiView
from rest_framework.response import Response
from console.services.team_services import TeamService
from www.utils.return_message import general_message


class UserTeamDetailsView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        获取用户创建的团队详情
        ---
        parameters:
            []
        """
        try:
            team_service = TeamService()
            region_list = team_service.get_user_team_details(self.user)
            
            result = general_message(
                200,
                "success",
                "查询成功",
                bean={
                    "regions": region_list
                })
            return Response(result, status=result["code"])
            
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=500) 