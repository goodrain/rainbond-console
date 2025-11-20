# -*- coding: utf8 -*-
"""
  Created by leon on 18/1/5.
"""
import json
import logging
import os

from console.exception.bcode import ErrK8sComponentNameExists
from console.exception.main import (AccountOverdueException, ResourceNotEnoughException)
from console.repositories.app import service_webhooks_repo
from console.repositories.oauth_repo import oauth_repo, oauth_user_repo
from console.services.app import app_service, package_upload_service
from console.services.app_config import compile_env_service
from console.services.app_import_and_export_service import import_service
from console.services.group_service import group_service
from console.services.operation_log import operation_log_service
from console.utils.oauth.oauth_types import get_oauth_instance
from console.views.app_config.base import AppBaseView
from console.views.base import RegionTenantHeaderView, JWTAuthApiView, ApplicationView
from django.views.decorators.cache import never_cache
from rest_framework.response import Response

from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import ServiceGroup
from www.utils.crypt import make_uuid
from www.utils.return_message import general_message

logger = logging.getLogger("default")
region_api = RegionInvokeApi()


class SourceCodeCreateView(ApplicationView):
    @never_cache
    def post(self, request, *args, **kwargs):
        """
        源码创建组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组id
              required: true
              type: string
              paramType: form
            - name: code_from
              description: 组件代码来源
              required: true
              type: string
              paramType: form
            - name: service_cname
              description: 组件名称
              required: true
              type: string
              paramType: form
            - name: git_url
              description: git地址
              required: false
              type: string
              paramType: form
            - name: git_project_id
              description: 代码ID
              required: false
              type: string
              paramType: form
            - name: code_version
              description: 代码版本
              required: false
              type: string
              paramType: form
            - name: username
              description: 私有云用户名称
              required: false
              type: string
              paramType: form
            - name: password
              description: 私有云账户密码
              required: false
              type: string
              paramType: form
            - name: server_type
              description: 仓库类型git或svn
              required: false
              type: string
              paramType: form

        """

        group_id = request.data.get("group_id", -1)
        service_code_from = request.data.get("code_from", None)
        service_cname = request.data.get("service_cname", None)
        service_code_clone_url = request.data.get("git_url", None)
        git_password = request.data.get("password", None)
        git_user_name = request.data.get("username", None)
        service_code_id = request.data.get("git_project_id", None)
        service_code_version = request.data.get("code_version", "master")
        is_oauth = request.data.get("is_oauth", False)
        check_uuid = request.data.get("check_uuid")
        event_id = request.data.get("event_id")
        server_type = request.data.get("server_type", "git")
        user_id = request.user.user_id
        oauth_service_id = request.data.get("service_id")
        git_full_name = request.data.get("full_name")
        is_demo = request.data.get("is_demo", False)
        arch = request.data.get("arch", "amd64")
        git_service = None
        open_webhook = False
        k8s_component_name = request.data.get("k8s_component_name", "")
        host = os.environ.get('DEFAULT_DOMAIN', "http://" + request.get_host())
        if k8s_component_name and app_service.is_k8s_component_name_duplicate(self.app_id, k8s_component_name):
            if is_demo:
                k8s_component_name = k8s_component_name + "-" + make_uuid()[:6]
            else:
                raise ErrK8sComponentNameExists
        if is_oauth:
            open_webhook = request.data.get("open_webhook", False)
            try:
                oauth_service = oauth_repo.get_oauth_services_by_service_id(service_id=oauth_service_id)
                oauth_user = oauth_user_repo.get_user_oauth_by_user_id(service_id=oauth_service_id, user_id=user_id)
            except Exception as e:
                logger.debug(e)
                rst = {"data": {"bean": None}, "status": 400, "msg_show": "未找到OAuth服务, 请检查该服务是否存在且属于开启状态"}
                return Response(rst, status=200)
            try:
                git_service = get_oauth_instance(oauth_service.oauth_type, oauth_service, oauth_user)
            except Exception as e:
                logger.debug(e)
                rst = {"data": {"bean": None}, "status": 400, "msg_show": "未找到OAuth服务"}
                return Response(rst, status=200)
            if not git_service.is_git_oauth():
                rst = {"data": {"bean": None}, "status": 400, "msg_show": "该OAuth服务不是代码仓库类型"}
                return Response(rst, status=200)

            service_code_from = "oauth_" + oauth_service.oauth_type
        try:
            if not service_code_clone_url:
                return Response(general_message(400, "code url is null", "仓库地址未指明"), status=400)
            if not service_code_from:
                return Response(general_message(400, "params error", "参数service_code_from未指明"), status=400)
            if not server_type:
                return Response(general_message(400, "params error", "仓库类型未指明"), status=400)
            # 创建源码组件
            if service_code_clone_url:
                service_code_clone_url = service_code_clone_url.strip()
            code, msg_show, new_service = app_service.create_source_code_app(
                self.response_region,
                self.tenant,
                self.user,
                service_code_from,
                service_cname,
                service_code_clone_url,
                service_code_id,
                service_code_version,
                server_type,
                check_uuid,
                event_id,
                oauth_service_id,
                git_full_name,
                k8s_component_name=k8s_component_name,
                arch=arch)
            if code != 200:
                return Response(general_message(code, "service create fail", msg_show), status=code)
            # 添加username,password信息
            if git_password or git_user_name:
                app_service.create_service_source_info(self.tenant, new_service, git_user_name, git_password)

            # 自动添加hook
            if open_webhook and is_oauth and not new_service.open_webhooks:
                service_webhook = service_webhooks_repo.create_service_webhooks(new_service.service_id, "code_webhooks")
                service_webhook.state = True
                service_webhook.deploy_keyword = "deploy"
                service_webhook.save()
                try:
                    git_service.create_hook(host, git_full_name, endpoint='console/webhooks/' + new_service.service_id)
                    new_service.open_webhooks = True
                except Exception as e:
                    logger.exception(e)
                    new_service.open_webhooks = False
                new_service.save()
            code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, self.app_id,
                                                                new_service.service_id)

            if code != 200:
                logger.debug("service.create", msg_show)
            bean = new_service.to_dict()
            result = general_message(200, "success", "创建成功", bean=bean)
            new_information = json.dumps({
                "应用名称": self.app.group_name,
                "组件名称": service_cname,
                "组件英文名称": k8s_component_name,
                "仓库地址": service_code_clone_url,
                "代码版本": service_code_version
            },
                ensure_ascii=False)
            component = operation_log_service.process_component_name(new_service.service_cname, self.region_name,
                                                                     self.tenant_name, new_service.service_alias)
            comment = "在应用{app}中创建了组件 ".format(
                app=operation_log_service.process_app_name(self.app.group_name, self.region_name, self.tenant_name,
                                                           self.app.app_id)) + component
            operation_log_service.create_app_log(ctx=self, comment=comment, format_app=False,
                                                 new_information=new_information)
        except ResourceNotEnoughException as re:
            raise re
        except AccountOverdueException as re:
            logger.exception(re)
            return Response(general_message(10410, "resource is not enough", re.message), status=412)
        return Response(result, status=result["code"])


class AppCompileEnvView(AppBaseView):
    @never_cache
    def get(self, request, *args, **kwargs):
        """
        获取组件运行环境信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path

        """
        compile_env = compile_env_service.get_service_compile_env(self.service)
        bean = dict()
        selected_dependency = []
        if compile_env:
            check_dependency = json.loads(compile_env.check_dependency)
            user_dependency = {}
            if compile_env.user_dependency:
                user_dependency = json.loads(compile_env.user_dependency)
                selected_dependency = [key.replace("ext-", "") for key in list(user_dependency.get("dependencies", {}).keys())]
            bean["check_dependency"] = check_dependency
            bean["user_dependency"] = user_dependency
            bean["service_id"] = compile_env.service_id
            bean["selected_dependency"] = selected_dependency
        result = general_message(200, "success", "查询编译环境成功", bean=bean)
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, *args, **kwargs):
        """
        修改组件运行环境信息
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 组件别名
              required: true
              type: string
              paramType: path
            - name: service_runtimes
              description: 组件运行版本，如php5.5等
              required: false
              type: string
              paramType: form
            - name: service_server
              description: 组件使用的服务器，如tomcat,apache,nginx等
              required: false
              type: string
              paramType: form
            - name: service_dependency
              description: 组件依赖，如php-mysql扩展等
              required: false
              type: string
              paramType: form

        """
        service_runtimes = request.data.get("service_runtimes", "")
        service_server = request.data.get("service_server", "")
        service_dependency = request.data.get("service_dependency", "")
        checkJson = {}
        checkJson["language"] = self.service.language
        checkJson["runtimes"] = service_runtimes
        checkJson["procfile"] = service_server
        if service_dependency != "":
            dps = service_dependency.split(",")
            d = {}
            for dp in dps:
                if dp is not None and dp != "":
                    d["ext-" + dp] = "*"
            checkJson["dependencies"] = d
        else:
            checkJson["dependencies"] = {}
        update_params = {"user_dependency": json.dumps(checkJson)}
        compile_env = compile_env_service.update_service_compile_env(self.service, **update_params)
        bean = dict()
        if compile_env:
            check_dependency = json.loads(compile_env.check_dependency)
            user_dependency = {}
            if compile_env.user_dependency:
                user_dependency = json.loads(compile_env.user_dependency)
            bean["check_dependency"] = check_dependency
            bean["user_dependency"] = user_dependency
            bean["service_id"] = compile_env.service_id

        result = general_message(200, "success", "操作成功", bean=bean)
        return Response(result, status=result["code"])


class PackageCreateView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, tenantName, *args, **kwargs):
        """
        本地文件创建组件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 组id
              required: true
              type: string
              paramType: form
            - name: code_from
              description: 组件代码来源
              required: true
              type: string
              paramType: form
            - name: service_cname
              description: 组件名称
              required: true
              type: string
              paramType: form
        """
        group_id = request.data.get("group_id", -1)
        region = request.data.get("region")
        event_id = request.data.get("event_id")
        service_cname = request.data.get("service_cname", None)
        k8s_component_name = request.data.get("k8s_component_name", "")
        arch = request.data.get("arch", "amd64")
        if k8s_component_name and app_service.is_k8s_component_name_duplicate(group_id, k8s_component_name):
            raise ErrK8sComponentNameExists
        try:
            pkg_record = package_upload_service.get_upload_record(self.team_name, region, event_id)
            pkg_create_time = pkg_record.create_time
            # 创建信息
            ts = app_service.create_package_upload_info(region, self.tenant, self.user, service_cname, k8s_component_name,
                                                        event_id, pkg_create_time, arch)
            # 更新状态
            update_record = {
                "status": "finished",
                "component_id": ts.service_id,
            }
            package_upload_service.update_upload_record(tenantName, event_id, **update_record)
            code, msg_show = group_service.add_service_to_group(self.tenant, self.response_region, group_id, ts.service_id)
            if code != 200:
                logger.debug("service.create", msg_show)
            bean = ts.to_dict()
            result = general_message(200, "success", "操作成功", bean=bean)
            return Response(result, status=result["code"])
        except Exception as e:
            logger.exception(e)
        result = general_message(200, "failed", "操作失败", bean={})
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, tenantName, *args, **kwargs):
        """
        构建源修改
        """
        event_id = request.data.get("event_id")
        service_id = request.data.get("service_id", "")
        region = request.data.get("region", "")
        try:
            pkg_record = package_upload_service.get_upload_record(self.team_name, region, event_id)
            pkg_create_time = pkg_record.create_time
            app_service.change_package_upload_info(service_id, event_id, pkg_create_time)
            update_record = {
                "status": "finished",
                "component_id": service_id,
            }
            package_upload_service.update_upload_record(tenantName, event_id, **update_record)
            result = general_message(200, "success", "上传成功")
            return Response(result, status=result["code"])
        except Exception as e:
            logger.exception(e)
        result = general_message(500, "faild", "上传失败")
        return Response(result, status=result["code"])


class PackageUploadRecordView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, tenantName, *args, **kwargs):
        """
        查询上传结果
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: region
              description: 集群
              required: true
              type: string
              paramType: form
        """
        region = request.GET.get("region", None)
        event_id = request.GET.get("event_id", None)
        try:
            res, body = region_api.get_upload_file_dir(region, tenantName, event_id)
            packages = body["bean"].get("packages", [])
            packages = packages if packages else []
            bean = dict()
            packages_name = []
            for package in packages:
                packages_name.append(package)
            bean["package_name"] = packages_name
            data = {"source_dir": packages_name}
            package_upload_service.update_upload_record(tenantName, event_id, **data)
            result = general_message(200, "success", "上传成功", bean=bean)
            return Response(result, status=result["code"])
        except Exception as e:
            logger.exception(e)
        result = general_message(200, "", "")
        return Response(result, status=result["code"])

    @never_cache
    def post(self, request, tenantName, *args, **kwargs):
        """
        保存上传记录
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: region
              description: 集群
              required: true
              type: string
              paramType: form
        """
        region = request.data.get("region", "")
        component_id = request.data.get("component_id", "")
        event_id = make_uuid()
        record_info = {
            "event_id": event_id,
            "status": "unfinished",
            "source_dir": "",
            "team_name": tenantName,
            "region": region,
            "component_id": component_id
        }
        region_api.create_upload_file_dir(region, tenantName, event_id)
        try:
            upload_record = package_upload_service.create_upload_record(**record_info)
            upload_url = import_service.get_upload_package_url(region, event_id)
            bean = dict()
            bean["event_id"] = upload_record.event_id
            bean["status"] = upload_record.status
            bean["team_name"] = upload_record.team_name
            bean["region"] = upload_record.region
            bean["upload_url"] = upload_url
            result = general_message(200, "success", "操作成功", bean=bean)
            return Response(result, status=result["code"])
        except Exception as e:
            logger.exception(e)
        result = general_message(500, "failed", "操作失败")
        return Response(result, status=result["code"])

    @never_cache
    def put(self, request, tenantName, *args, **kwargs):
        """
        修改上传记录
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: region
              description: 集群
              required: true
              type: string
              paramType: form
        """
        event_id = request.data.get("event_id")
        update_record = {"status": "finished"}
        try:
            package_upload_service.update_upload_record(tenantName, event_id, **update_record)
            result = general_message(200, "success", "操作成功", bean={"res": "ok"})
            return Response(result, status=result["code"])
        except Exception as e:
            logger.exception(e)
        result = general_message(500, "failed", "操作失败")
        return Response(result, status=result["code"])


class UploadRecordLastView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, tenantName, *args, **kwargs):
        """
        查询上次上传记录
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: region
              description: 集群
              required: true
              type: string
              paramType: form
        """
        region = request.GET.get("region", None)
        component_id = request.GET.get("component_id", None)
        try:
            records = package_upload_service.get_last_upload_record(tenantName, region, component_id)
            bean = dict()
            if records.source_dir != "":
                dir_list = eval(records.source_dir)
                bean["source_dir"] = dir_list
                bean["event_id"] = records.event_id
            result = general_message(200, "success", "操作成功", bean=bean)
            return Response(result, status=result["code"])
        except Exception as e:
            logger.exception(e)
        result = general_message(200, "success", "暂无记录", bean={})
        return Response(result, status=result["code"])


class TarImageLoadView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, tenantName, *args, **kwargs):
        """
        开始解析tar包镜像(异步任务)
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: event_id
              description: 上传事件ID
              required: true
              type: string
              paramType: form
            - name: region
              description: 集群
              required: true
              type: string
              paramType: form
        """
        event_id = request.data.get("event_id", None)
        region = request.data.get("region", None)

        if not event_id:
            return Response(general_message(400, "event_id is required", "事件ID不能为空"), status=400)
        if not region:
            return Response(general_message(400, "region is required", "集群不能为空"), status=400)

        try:
            # 1. 获取上传的tar文件路径
            res, body = region_api.get_upload_file_dir(region, tenantName, event_id)
            if res.status != 200:
                logger.info("-------------{}".format(res))
                return Response(general_message(500, "failed to get upload files", "获取上传文件失败"), status=500)

            packages = body.get("bean", {}).get("packages", [])
            if not packages or len(packages) == 0:
                return Response(general_message(400, "no tar file found", "未找到上传的tar文件"), status=400)

            if len(packages) > 1:
                return Response(general_message(400, "multiple files found", "镜像文件数超出限制,请确认上传文件数是否为1"), status=400)

            tar_file = packages[0]

            # 2. 验证文件格式
            if not (tar_file.endswith(".tar") or tar_file.endswith(".tar.gz")):
                return Response(general_message(400, "invalid file format", "文件格式不正确,请确认上传的文件格式是否为.tar或.tar.gz"), status=400)

            # 3. 调用region API开始异步解析tar包
            load_data = {
                "event_id": event_id,
                "tar_file_path": tar_file
            }

            res, body = region_api.load_tar_image(region, tenantName, load_data)

            if res.status != 200:
                error_msg = body.get("msg", "启动解析任务失败")
                return Response(general_message(500, "load task failed", error_msg), status=500)

            # 4. 返回任务ID,用于后续查询
            result_bean = {
                "event_id": event_id,
                "load_id": body.get("bean", {}).get("load_id"),  # 用于查询解析结果的ID
                "status": "loading"  # loading, success, failure
            }

            logger.info(f"Started tar image load task, event_id: {event_id}, load_id: {result_bean['load_id']}")

            return Response(general_message(200, "success", "开始解析tar包", bean=result_bean), status=200)

        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, "internal error", f"启动解析任务失败: {str(e)}"), status=500)


class TarImageLoadResultView(RegionTenantHeaderView):
    @never_cache
    def get(self, request, tenantName, load_id, *args, **kwargs):
        """
        查询tar包解析结果(包含镜像信息)
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: load_id
              description: 解析任务ID
              required: true
              type: string
              paramType: path
            - name: region
              description: 集群
              required: true
              type: string
              paramType: query
        """
        region = request.GET.get("region", None)

        if not region:
            return Response(general_message(400, "region is required", "集群不能为空"), status=400)

        try:
            # 调用region API查询解析结果
            res, body = region_api.get_tar_load_result(region, tenantName, load_id)

            if res.status != 200:
                error_msg = body.get("msg", "查询解析结果失败")
                return Response(general_message(500, "query failed", error_msg), status=500)

            result = body.get("bean", {})

            # 返回解析状态和镜像列表(如果解析完成)
            result_bean = {
                "load_id": load_id,
                "status": result.get("status"),  # loading, success, failure
                "message": result.get("message", "")  # 错误信息或提示
            }

            # 如果解析成功，返回镜像信息
            if result.get("status") == "success":
                result_bean["images"] = result.get("images", [])  # 原始镜像列表
                result_bean["metadata"] = result.get("metadata", {})  # 镜像元数据
                result_bean["target_images"] = result.get("target_images", {})  # 镜像元数据

            return Response(general_message(200, "success", "查询成功", bean=result_bean), status=200)

        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, "internal error", f"查询解析结果失败: {str(e)}"), status=500)


class TarImageImportView(RegionTenantHeaderView):
    @never_cache
    def post(self, request, tenantName, *args, **kwargs):
        """
        确认导入镜像到镜像仓库(同步执行)
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: load_id
              description: 解析任务ID
              required: true
              type: string
              paramType: form
            - name: region
              description: 集群
              required: true
              type: string
              paramType: form
            - name: images
              description: 要导入的镜像列表(镜像名数组)
              required: true
              type: array
              paramType: form
            - name: namespace
              description: 命名空间
              required: false
              type: string
              paramType: form
        """
        load_id = request.data.get("load_id", None)
        region = request.data.get("region", None)
        images = request.data.get("images", [])  # 用户选择的镜像列表
        namespace = request.data.get("namespace", tenantName)

        if not load_id:
            return Response(general_message(400, "load_id is required", "解析任务ID不能为空"), status=400)
        if not region:
            return Response(general_message(400, "region is required", "集群不能为空"), status=400)
        if not images or len(images) == 0:
            return Response(general_message(400, "images is required", "请选择要导入的镜像"), status=400)

        try:
            # 调用region API确认导入镜像
            import_data = {
                "load_id": load_id,
                "images": images,
                "namespace": namespace
            }

            res, body = region_api.import_tar_images(region, tenantName, import_data)

            if res.status != 200:
                error_msg = body.get("msg", "导入镜像失败")
                return Response(general_message(500, "import failed", error_msg), status=500)

            result = body.get("bean", {})

            # 返回导入结果
            result_bean = {
                "imported_images": result.get("imported_images", []),  # 成功导入的镜像
                "failed_images": result.get("failed_images", []),  # 失败的镜像
                "message": result.get("message", "导入完成")
            }

            logger.info(f"Imported tar images, load_id: {load_id}, success: {len(result_bean['imported_images'])}, failed: {len(result_bean['failed_images'])}")

            return Response(general_message(200, "success", "导入完成", bean=result_bean), status=200)

        except Exception as e:
            logger.exception(e)
            return Response(general_message(500, "internal error", f"导入镜像失败: {str(e)}"), status=500)
