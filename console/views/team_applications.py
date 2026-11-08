"""Authenticated application endpoints; user identity and admin rights are server-derived."""
from rest_framework import serializers
from rest_framework.response import Response
from console.views.base import JWTAuthApiView
from console.services.team_applications import ApplicationError, team_application_service
from www.utils.return_message import general_message


class TeamApplicationBaseView(JWTAuthApiView):
    def initial(self, request, *args, **kwargs):
        self.perform_authentication(request)
        self.check_permissions(request)
        super().initial(request, *args, **kwargs)


class TeamApplicationsView(TeamApplicationBaseView):
    def get(self, request, enterprise_id, **kwargs):
        try:
            rows = team_application_service.list(self.user, enterprise_id, request.GET.get("scope", "mine"),
                                                 self.is_enterprise_admin)
            page = max(1, int(request.GET.get("page", 1)))
            size = min(100, max(1, int(request.GET.get("page_size", 100))))
            total = rows.count()
            return Response(general_message(200, "success", "获取成功", bean={
                "list": [row.public() for row in rows[(page - 1) * size:page * size]], "total": total}))
        except ApplicationError as error:
            return Response(general_message(error.status, "failed", error.message), status=error.status)
        except ValueError:
            return Response(general_message(400, "failed", "分页参数无效"), status=400)

    def post(self, request, enterprise_id, **kwargs):
        try:
            row = team_application_service.submit(self.user, enterprise_id, request.data)
            return Response(general_message(200, "success", "申请已提交", bean=row.public()), status=201)
        except ApplicationError as error:
            return Response(general_message(error.status, "failed", error.message), status=error.status)
        except serializers.ValidationError as error:
            return Response(general_message(400, "failed", "请检查团队信息和资源额度", bean=error.detail), status=400)


class TeamApplicationReviewView(TeamApplicationBaseView):
    def post(self, request, enterprise_id, request_id, **kwargs):
        try:
            row = team_application_service.review(self.user, enterprise_id, request_id, request.data, self.is_enterprise_admin)
            return Response(general_message(200, "success", "审核结果已保存", bean=row.public()))
        except ApplicationError as error:
            return Response(general_message(error.status, "failed", error.message), status=error.status)
        except serializers.ValidationError as error:
            return Response(general_message(400, "failed", "请检查审核意见，驳回必须填写原因", bean=error.detail), status=400)
