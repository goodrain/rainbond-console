import json

from rest_framework import status

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
    def get(self, request, *args, **kwargs):
        """
        检查helm应用
        """
        name = request.GET.get("name")
        repo_name = request.GET.get("repo_name")
        chart_name = request.GET.get("chart_name")
        version = request.GET.get("version")
        overrides = []
        _, data = helm_app_service.check_helm_app(name, repo_name, chart_name, version, overrides, self.region_name,
                                                  self.tenant_name, self.tenant)
        result = general_message(200, "success", "获取成功", bean=data)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
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
        cvdata = helm_app_service.yaml_conversion(name, repo_name, chart_name, version, overrides_list,
                                                  self.region_name,
                                                  self.tenant_name, self.tenant, self.enterprise.enterprise_id,
                                                  self.region.region_id)
        helm_center_app = rainbond_app_repo.get_rainbond_app_qs_by_key(self.enterprise.enterprise_id, app_model_id)
        chart = repo_name + "/" + chart_name
        helm_app_service.generate_template(cvdata, helm_center_app, version, self.tenant, chart, self.region_name,
                                           self.enterprise.enterprise_id, self.user.user_id, overrides_list, app_id)
        result = general_message(200, "success", "安装成功", bean="")
        return Response(result, status=status.HTTP_200_OK)


class HelmCenterApp(RegionTenantHeaderView):
    def post(self, request, *args, **kwargs):
        """
        生成helm应用模版
        """
        repo_name = request.data.get("repo_name")
        chart_name = request.data.get("chart_name")
        pic = request.data.get("pic", "")
        describe = request.data.get("describe", "")
        details = request.data.get("details", "This is a helm application from {}".format(repo_name))
        app_id = make_uuid3(repo_name + "/" + chart_name)
        helm_center_app = rainbond_app_repo.get_rainbond_app_qs_by_key(self.enterprise.enterprise_id, app_id)
        data = {"exist": True, "app_model_id": app_id}
        if not helm_center_app:
            center_app = {
                "app_id": app_id,
                "app_name": chart_name,
                "create_team": "",
                "source": "helm:" + repo_name,
                "scope": "enterprise",
                "pic": pic,
                "describe": describe,
                "enterprise_id": self.enterprise.enterprise_id,
                "details": details
            }
            helm_app_service.create_helm_center_app(**center_app)
            data["exist"] = False
            data["app_model_id"] = app_id
            result = general_message(200, "success", "创建成功", bean=json.dumps(data))
            return Response(result, status=status.HTTP_200_OK)
        result = general_message(200, "success", "模版已存在", bean=json.dumps(data))
        return Response(result, status=status.HTTP_200_OK)


class HelmChart(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        获取chart包的一些信息
        """
        repo_name = request.GET.get("repo_name")
        chart_name = request.GET.get("chart_name")
        # highest 默认获取全部版本，传值获取最高版本
        highest = request.GET.get("highest", "")
        app_id = request.GET.get("app_id", "")
        data = helm_repo.get_helm_repo_by_name(repo_name)
        if not data:
            ret = dict()
            ret["repo_exist"] = False
            result = general_message(200, "success", "查询成功", bean=ret)
            return Response(result, status=status.HTTP_200_OK)
        chart_information = helm_app_service.get_helm_chart_information(self.region_name, self.tenant_name,
                                                                        data["repo_url"],
                                                                        chart_name)
        app = rainbond_app_repo.get_app_helm_overrides(app_id, make_uuid3(repo_name + "/" + chart_name)).last()
        overrides_dict = dict()
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
    def post(self, request, *args, **kwargs):
        """
        命令安装helm应用
        """
        command = request.data.get("command")
        data = helm_app_service.parse_helm_command(command, self.region_name, self.tenant)
        data['eid'] = self.enterprise.enterprise_id
        result = general_message(200, "success", "执行成功", bean=data)
        return Response(result, status=status.HTTP_200_OK)


class HelmList(RegionTenantHeaderView):
    def get(self, request, *args, **kwargs):
        """
        查询本地已经有的helm商店
        """
        data = HelmRepoInfo.objects.all().values()
        result = general_message(200, "success", "查询成功", list=data)
        return Response(result, status=status.HTTP_200_OK)


class HelmRepoAdd(RegionTenantHeaderView):
    def post(self, request, *args, **kwargs):
        """
        根据cmd 命令行 增加helm仓库
        """
        command = request.data.get("command")

        repo_name, repo_url, username, password, success = helm_app_service.parse_cmd_add_repo(command)
        data = {
            "status": success,
            "repo_name": repo_name,
            "repo_url": repo_url,
            "username": username,
            "password": password
        }
        result = general_message(200, "success", "添加成功", bean=data)

        return Response(result, status=status.HTTP_200_OK)


class HelmRepo(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        """
        添加helm仓库
        """
        repo_name = request.data.get("repo_name")
        repo_url = request.data.get("repo_url")
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        if helm_repo.get_helm_repo_by_name(repo_name):
            result = general_message(200, "success", "仓库已存在", "")
            return Response(result, status=status.HTTP_200_OK)
        helm_app_service.add_helm_repo(repo_name, repo_url, username, password)
        result = general_message(200, "success", "添加成功", "")
        return Response(result, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        """
        更新helm仓库
        """
        repo_name = request.data.get("repo_name")
        repo_url = request.data.get("repo_url")
        helm_repo.update_helm_repo(repo_name, repo_url)
        result = general_message(200, "success", "更新成功", "")
        return Response(result, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """
        删除helm仓库
        """
        repo_name = request.data.get("repo_name")
        share_repo.delete_helm_shared_apps("helm:" + repo_name)
        helm_repo.delete_helm_repo(repo_name)
        result = general_message(200, "success", "删除成功", "")
        return Response(result, status=status.HTTP_200_OK)
