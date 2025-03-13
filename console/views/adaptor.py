import base64
import json
import os
import tarfile
import tempfile

import requests
import yaml
from requests.auth import HTTPBasicAuth
from rest_framework import status

from console.repositories.helm import helm_repo, region_event
from console.views.base import JWTAuthApiView
from rest_framework.response import Response


class Appstores(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        appstores = helm_repo.get_all_repo()
        data = list()
        for appstore in appstores:
            data.append({
                "name": appstore.repo_name,
                "url": appstore.repo_url,
                "username": appstore.username,
                "password": appstore.password,
            })
        result = {"code": 200, "msg": "success", "msg_show": "查询成功", "data": data}
        return Response(result, status=result["code"])


class Appstore(JWTAuthApiView):
    def get(self, request, enterprise_id, name, *args, **kwargs):
        app_store = helm_repo.get_helm_repo_by_name(name)
        if not app_store:
            result = {"code": 400, "msg": "success", "msg_show": "查询成功"}
            return Response(result, status=result["code"])
        result = {"code": 200, "msg": "success", "msg_show": "查询成功"}
        return Response(result, status=result["code"])


class AppstoreCharts(JWTAuthApiView):
    def get(self, request, enterprise_id, name, *args, **kwargs):
        app_store = helm_repo.get_helm_repo_by_name(name)
        if app_store:
            helm_repo_url = app_store.get("repo_url")
            repo_index_url = f"{helm_repo_url.rstrip('/')}/index.yaml"
            response = requests.get(repo_index_url, auth=HTTPBasicAuth(app_store.get("username"), app_store.get("password")))
            if response.status_code == 200:
                index_data = yaml.safe_load(response.text)
                # 获取所有 chart 的信息
                charts_data = []
                charts = index_data.get('entries', {})
                for chart_name, versions in charts.items():
                    chart_info = {
                        "name": chart_name,
                        "versions": []
                    }
                    for version_info in versions:
                        version_data = {
                            "name": chart_name,
                            "home": version_info.get('home', ''),
                            "sources": version_info.get('sources', []),
                            "version": version_info.get('version', 'N/A'),
                            "description": version_info.get('description', 'No description available'),
                            "keywords": version_info.get('keywords', []),
                            "maintainers": version_info.get('maintainers', []),
                            "icon": version_info.get('icon', ''),
                            "apiVersion": version_info.get('apiVersion', ''),
                            "appVersion": version_info.get('appVersion', ''),
                            "urls": version_info.get('urls', []),
                            "created": version_info.get('created', ''),
                            "digest": version_info.get('digest', '')
                        }
                        chart_info["versions"].append(version_data)
                    charts_data.append(chart_info)
                result = {"code": 200, "msg": "success", "msg_show": "查询成功", "data": charts_data}
                return Response(result, status=result["code"])
            else:
                return Response({"code": response.status_code, "msg": "failed", "msg_show": "仓库访问失败"}, status=response.status_code)
        return Response({"code": 404, "msg": "not found", "msg_show": "未找到该应用商店"}, status=404)


class AppstoreChart(JWTAuthApiView):
    def get(self, request, enterprise_id, name, chart_name, version, *args, **kwargs):
        app_store = helm_repo.get_helm_repo_by_name(name)
        if not app_store:
            return Response({"code": 400, "msg": "bad request", "msg_show": "无此应用商店"}, status=400)
        chart_url = "{app_store_url}/charts/{chart_name}-{version}.tgz".format(app_store_url=app_store["repo_url"].rstrip("/"), chart_name=chart_name, version=version)
        try:
            # 下载 tgz 文件
            response = requests.get(chart_url, stream=True)
            response.raise_for_status()

            # 创建临时文件来保存下载的 .tgz 包
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tgz") as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            # 初始化返回数据结构
            readme_content = None
            questions_content = None
            values_content = {}

            # 读取 .tgz 文件并提取需要的文件内容
            with tarfile.open(temp_file_path, "r:gz") as tar:
                for member in tar.getmembers():
                    # 提取 README.md 并编码为 base64
                    if "README.md" in member.name and readme_content is None:
                        readme_file = tar.extractfile(member)
                        readme_content = base64.b64encode(readme_file.read()).decode("utf-8") if readme_file else None
                    # 提取 questions.yaml 并编码为 base64
                    elif "questions.yaml" in member.name and questions_content is None:
                        questions_file = tar.extractfile(member)
                        questions_content = base64.b64encode(questions_file.read()).decode(
                            "utf-8") if questions_file else None
                    # 提取所有 values.yaml 并编码为 base64
                    elif member.name.endswith("values.yaml"):
                        values_file = tar.extractfile(member)
                        values_content[member.name] = base64.b64encode(values_file.read()).decode(
                            "utf-8") if values_file else ""

            # 删除临时文件
            os.remove(temp_file_path)

            # 构造返回数据
            data = {
                "readme": readme_content or "",
                "questions": questions_content or "",
                "values": dict(reversed(list(values_content.items()))),
            }

            # 成功返回数据
            return Response({"code": 200, "msg": "success", "msg_show": "操作成功", "data": data})

        except requests.RequestException:
            return Response({"code": 500, "msg": "request failed", "msg_show": "请求失败，请检查网络连接"}, status=500)
        except tarfile.TarError:
            return Response({"code": 500, "msg": "invalid tgz", "msg_show": "无法解析 tgz 文件"}, status=500)


class HelmRegionInstall(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        """
        获取 Helm 安装区域事件信息
        """
        try:
            # 根据企业ID和任务类型查询事件
            events = region_event.list_event(eid=enterprise_id, task_id="helm_install_region")

            if events.exists():
                event = events.first()
                try:
                    # 反序列化事件消息
                    event_data = json.loads(event.message)
                    response_data = {
                        "create_status": True,
                        "token": event_data.get("token"),
                        "api_host": event_data.get("api_host")
                    }
                except json.JSONDecodeError as e:
                    return Response({"detail": "Error decoding event message"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                response_data = {"create_status": False}
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, enterprise_id, *args, **kwargs):
        """
        初始化 Helm 安装区域事件
        """
        try:
            token = request.data.get('token', "")
            api_host = request.data.get('api_host', "")
            event_data = {
                "token": token,
                "api_host": api_host,
            }
            # 创建新的事件
            message = json.dumps(event_data)
            event = {
                "task_id": "helm_install_region",
                "enterprise_id": enterprise_id,
                "message": message,
            }
            region_event.create_region_event(**event)

            response_data = {"create_status": True}
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, enterprise_id, *args, **kwargs):
        """
        删除 Helm 安装区域事件
        """
        try:
            # 删除事件
            region_event.delete_event(eid=enterprise_id, task_id="helm_install_region")
            return Response({"detail": "Event deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
