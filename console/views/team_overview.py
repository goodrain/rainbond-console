from console.views.base import JWTAuthApiView
from rest_framework.response import Response
from console.exception.main import ServiceHandleException
from console.models.main import RegionConfig
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
            # 获取所有启用状态的集群
            regions = RegionConfig.objects.filter(status='1')
            
            region_list = [{
                "region_name": region.region_name,
                "region_alias": region.region_alias,
                "namespaces": []
            } for region in regions]
            
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