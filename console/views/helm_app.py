import json
from typing import Any

from rest_framework import status
from rest_framework.request import Request

from console.repositories.helm import helm_repo
from console.repositories.market_app_repo import rainbond_app_repo
from console.repositories.share_repo import share_repo
from console.services.helm_app_yaml import helm_app_service
from console.views.base import RegionTenantHeaderView, JWTAuthApiView
from www.models.main import HelmRepoInfo
from www.utils.crypt import make_uuid3
from www.utils.return_message import general_message
from rest_framework.response import Response


class HelmAppView(RegionTenantHeaderView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        检查helm应用
        """
        name = request.GET.get("name")
        repo_name = request.GET.get("repo_name")
        chart_name = request.GET.get("chart_name")
        version = request.GET.get("version")
        overrides: list = []
        # NOTE: GET params are Optional[str] but service expects str (systemic mismatch; backlog).
        _, data = helm_app_service.check_helm_app(name, repo_name, chart_name, version, overrides,  # type: ignore[arg-type]
                                                  self.region_name, self.tenant_name, self.tenant)
        result = general_message(200, "success", "获取成功", bean=data)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        生成helm应用模型
        """
        name = request.data.get("name")
        repo_name = request.data.get("repo_name")
        chart_name = request.data.get("chart_name")
        version = request.data.get("version")
        overrides = request.data.get("overrides", {})
        app_model_id = request.data.get("app_model_id")
        app_id = request.data.get("app_id")
        overrides_list = list()
        for key, value in overrides.items():
            overrides_list.append(key + "=" + value)
        # NOTE: request.data fields are Any|None but services expect str (systemic mismatch; backlog).
        cvdata = helm_app_service.yaml_conversion(name, repo_name, chart_name, version,  # type: ignore[arg-type]
                                                  overrides_list, self.region_name,
                                                  self.tenant_name, self.tenant, self.enterprise.enterprise_id,
                                                  self.region.region_id)
        helm_center_app = rainbond_app_repo.get_rainbond_app_by_app_id(app_model_id)  # type: ignore[arg-type]
        chart = repo_name + "/" + chart_name  # type: ignore[operator]
        helm_app_service.generate_template(cvdata, helm_center_app, version,  # type: ignore[arg-type]
                                           self.tenant, chart, self.region_name,
                                           self.enterprise.enterprise_id, self.user.user_id,
                                           overrides_list, app_id)  # type: ignore[arg-type]
        result = general_message(200, "success", "安装成功", bean="")
        return Response(result, status=status.HTTP_200_OK)


class HelmCenterApp(RegionTenantHeaderView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        生成helm应用模版
        """
        repo_name = request.data.get("repo_name")
        chart_name = request.data.get("chart_name")
        pic = request.data.get("pic", "")
        describe = request.data.get("describe", "")
        details = request.data.get("details", "This is a helm application from {}".format(repo_name))
        # NOTE: request.data fields are Any|None; string ops/args expect str (systemic mismatch; backlog).
        app_id = make_uuid3(repo_name + "/" + chart_name)  # type: ignore[operator]
        helm_center_app = rainbond_app_repo.get_rainbond_app_by_app_id(app_id)
        data = {"exist": True, "app_model_id": app_id}
        if not helm_center_app:
            center_app = {
                "app_id": app_id,
                "app_name": chart_name,
                "create_team": "",
                "source": "helm:" + repo_name,  # type: ignore[operator]
                "scope": "enterprise",
                "pic": pic,
                "describe": describe,
                "enterprise_id": self.enterprise.enterprise_id,
                "details": details
            }
            helm_app_service.create_helm_center_app(center_app, self.region_name)
            data["exist"] = False
            data["app_model_id"] = app_id
            result = general_message(200, "success", "创建成功", bean=json.dumps(data))
            return Response(result, status=status.HTTP_200_OK)
        result = general_message(200, "success", "模版已存在", bean=json.dumps(data))
        return Response(result, status=status.HTTP_200_OK)


class HelmChart(RegionTenantHeaderView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        获取chart包的一些信息
        """
        repo_name = request.GET.get("repo_name")
        chart_name = request.GET.get("chart_name")
        # highest 默认获取全部版本，传值获取最高版本
        highest = request.GET.get("highest", "")
        app_id = request.GET.get("app_id", "")
        # NOTE: GET params are Optional[str] but repo/service expect str (systemic mismatch; backlog).
        data = helm_repo.get_helm_repo_by_name(repo_name)  # type: ignore[arg-type]
        if not data:
            ret: dict = dict()
            ret["repo_exist"] = False
            result = general_message(200, "success", "查询成功", bean=ret)
            return Response(result, status=status.HTTP_200_OK)
        chart_information = helm_app_service.get_helm_chart_information(
            self.region_name, self.tenant_name, data["repo_url"],
            chart_name, data["username"], data["password"])  # type: ignore[arg-type]
        app = rainbond_app_repo.get_app_helm_overrides(
            app_id, make_uuid3(repo_name + "/" + chart_name)).last()  # type: ignore[operator]
        overrides_dict: Any = dict()
        if app:
            overrides = json.loads(app.overrides)
            overrides_dict = [{override.split('=')[0]: override.split('=')[1]} for override in overrides]
        ret = dict()
        ret["maintainer"] = self.user.real_name
        ret["email"] = self.user.email
        ret["phone"] = self.user.phone
        ret["repo_exist"] = True
        ret["overrides"] = overrides_dict
        if highest:
            chart_information = chart_information[0]
        ret["chart_information"] = chart_information
        result = general_message(200, "success", "查询成功", bean=ret)
        return Response(result, status=status.HTTP_200_OK)


class CommandInstallHelm(RegionTenantHeaderView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        命令安装helm应用
        """
        command = request.data.get("command")
        # NOTE: request.data fields are Any|None but service expects str (systemic mismatch; backlog).
        data = helm_app_service.parse_helm_command(command, self.region_name, self.tenant)  # type: ignore[arg-type]
        data['eid'] = self.enterprise.enterprise_id
        result = general_message(200, "success", "执行成功", bean=data)
        return Response(result, status=status.HTTP_200_OK)


class HelmList(RegionTenantHeaderView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        查询本地已经有的helm商店
        """
        data = HelmRepoInfo.objects.all().values()
        result = general_message(200, "success", "查询成功", list=data)
        return Response(result, status=status.HTTP_200_OK)


class HelmRepoAdd(RegionTenantHeaderView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        根据cmd 命令行 增加helm仓库
        """
        command = request.data.get("command")

        repo_name, repo_url, username, password, success = helm_app_service.parse_cmd_add_repo(command)  # type: ignore[arg-type]
        data = {"status": success, "repo_name": repo_name, "repo_url": repo_url, "username": username, "password": password}
        result = general_message(200, "success", "添加成功", bean=data)

        return Response(result, status=status.HTTP_200_OK)


class HelmRepo(JWTAuthApiView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        添加helm仓库
        """
        repo_name = request.data.get("repo_name")
        repo_url = request.data.get("repo_url")
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        # NOTE: request.data fields are Any|None but repo/service expect str (systemic mismatch; backlog).
        if helm_repo.get_helm_repo_by_name(repo_name):  # type: ignore[arg-type]
            result = general_message(200, "success", "仓库已存在", "")
            return Response(result, status=status.HTTP_200_OK)
        helm_app_service.add_helm_repo(repo_name, repo_url, username, password)  # type: ignore[arg-type]
        result = general_message(200, "success", "添加成功", "")
        return Response(result, status=status.HTTP_200_OK)

    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        更新helm仓库
        """
        repo_name = request.data.get("repo_name")
        repo_url = request.data.get("repo_url")
        helm_repo.update_helm_repo(repo_name, repo_url)  # type: ignore[arg-type]
        result = general_message(200, "success", "更新成功", "")
        return Response(result, status=status.HTTP_200_OK)

    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        删除helm仓库
        """
        repo_name = request.data.get("repo_name")
        rainbond_app_repo.delete_helm_shared_apps("helm:" + repo_name)  # type: ignore[operator]
        helm_repo.delete_helm_repo(repo_name)  # type: ignore[arg-type]
        result = general_message(200, "success", "删除成功", "")
        return Response(result, status=status.HTTP_200_OK)


class UploadHelmChart(RegionTenantHeaderView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        event_id = request.GET.get("event_id")
        # NOTE: GET event_id is Optional[str] but service expects str (systemic mismatch; backlog).
        data = helm_app_service.get_upload_chart_information(
            self.region_name, self.tenant_name, event_id)  # type: ignore[arg-type]
        result = general_message(200, "success", "获取成功", data)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        event_id = request.data.get("event_id")
        name = request.data.get("name")
        version = request.data.get("version")
        data = helm_app_service.check_upload_chart(
            self.region_name, self.tenant, event_id, name, version)  # type: ignore[arg-type]
        result = general_message(200, "success", "检测完成", data)
        return Response(result, status=status.HTTP_200_OK)


class UploadHelmChartValue(RegionTenantHeaderView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        event_id = request.GET.get("event_id")
        data = helm_app_service.get_upload_chart_value(
            self.region_name, self.tenant_name, event_id)  # type: ignore[arg-type]
        result = general_message(200, "success", "获取成功", data)
        return Response(result, status=status.HTTP_200_OK)


class UploadHelmChartValueResource(RegionTenantHeaderView):
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        event_id = request.GET.get("event_id")
        name = request.GET.get("name")
        version = request.GET.get("version")
        overrides: Any = request.GET.get("overrides", {})
        overrides_list: list = list()
        for key, value in overrides.items():
            overrides_list.append(key + "=" + value)
        data = helm_app_service.get_upload_chart_resource(
            self.region_name, self.tenant, event_id, name, version,  # type: ignore[arg-type]
            overrides_list)
        result = general_message(200, "success", "获取成功", bean=data)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        resource = request.data.get("resource")
        app_id = request.data.get("app_id")
        helm_app_service.import_upload_chart_resource(
            self.region_name, self.tenant, app_id, resource, self.user)  # type: ignore[arg-type]
        result = general_message(200, "success", "安装成功", "")
        return Response(result, status=status.HTTP_200_OK)
