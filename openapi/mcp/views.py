import time

from rest_framework.response import Response
from rest_framework import status as http_status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from console.repositories.group import group_repo
from console.repositories.service_repo import service_repo
from console.services.app import app_service, port_service
from console.services.app_actions import app_manage_service
from console.services.app_check_service import app_check_service
from console.services.app_config.arch_service import arch_service
from console.services.app_config import env_var_service
from console.services.app_config import volume_service
from console.services.app_config import domain_service
from console.services.region_services import region_services
from console.services.team_services import team_services
from console.services.group_service import group_service
from console.services.app_config.component_logs import component_log_service
from default_region import make_uuid
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.return_message import general_message
from openapi.views.base import BaseOpenAPIView
from console.exception.main import ServiceHandleException
from .serializers import (
    RegionSerializer,
    TeamSerializer,
    AppSerializer,
    ComponentBaseSerializer,
    ComponentStatusSerializer,
    ComponentLogSerializer,
    CreateAppRequestSerializer,
    CreateAppResponseSerializer,
    CreateComponentRequestSerializer,
    AddPortRequestSerializer,
    PortBaseSerializer,
    ComponentDetailSerializer,
)

region_api = RegionInvokeApi()


class McpRegionsView(BaseOpenAPIView):
    """
    集群管理接口
    
    提供集群相关的操作接口，包括：
    - 获取企业下的集群列表
    """
    @swagger_auto_schema(
        operation_description="获取集群列表",
        responses={
            200: openapi.Response('获取成功', RegionSerializer(many=True)),
            500: openapi.Response('内部错误'),
        },
        tags=['集群管理']
    )
    def get(self, request):
        """获取集群列表"""
        try:
            # 获取企业下的所有集群
            regions = region_services.get_enterprise_regions(self.enterprise.enterprise_id)
            serializer = RegionSerializer(regions, many=True)
            result = general_message(200, "success", "获取成功", list=serializer.data)
            return Response(result, status=http_status.HTTP_200_OK)
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


class McpTeamsView(BaseOpenAPIView):
    """
    团队管理接口
    
    提供团队相关的操作接口，包括：
    - 获取企业下的团队列表
    - 支持按团队名称搜索
    """
    @swagger_auto_schema(
        operation_description="获取团队列表",
        manual_parameters=[
            openapi.Parameter('name', openapi.IN_QUERY, description='团队名称搜索', type=openapi.TYPE_STRING, required=False),
        ],
        responses={
            200: openapi.Response('获取成功', TeamSerializer(many=True)),
            500: openapi.Response('内部错误'),
        },
        tags=['团队管理']
    )
    def get(self, request):
        """获取团队列表"""
        try:
            teams = team_services.list_user_teams(
                enterprise_id=self.enterprise.enterprise_id,
                user=request.user,
                name=request.GET.get('name', None)
            )
            serializer = TeamSerializer(teams, many=True)
            result = general_message(200, "success", "获取成功", list=serializer.data)
            return Response(result, status=http_status.HTTP_200_OK)
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


class McpAppsView(BaseOpenAPIView):
    """
    应用列表管理接口
    
    提供团队下应用相关的操作接口，包括：
    - 获取团队下的应用列表
    - 支持按区域筛选应用
    """
    @swagger_auto_schema(
        operation_description="获取团队下的应用列表",
        responses={
            200: openapi.Response('获取成功', AppSerializer(many=True)),
            404: openapi.Response('团队不存在'),
            500: openapi.Response('内部错误'),
        },
        tags=['应用管理']
    )
    def get(self, request, team_alias, region_name):
        """获取团队下的应用列表"""
        try:
            team = team_services.get_team_by_team_alias(team_alias)
            if not team:
                return Response(general_message(404, "team not found", "团队不存在"), status=http_status.HTTP_404_NOT_FOUND)
            
            apps = group_service.get_tenant_groups_by_region(team, region_name)
            serializer = AppSerializer(apps, many=True)
            result = general_message(200, "success", "获取成功", list=serializer.data)
            return Response(result, status=http_status.HTTP_200_OK)
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


class McpAppView(BaseOpenAPIView):
    """
    应用管理接口
    
    提供应用相关的操作接口，包括：
    - 创建新的应用
    - 支持设置应用名称、英文标识等信息
    """
    @swagger_auto_schema(
        operation_description="创建应用",
        request_body=CreateAppRequestSerializer,
        responses={
            200: CreateAppResponseSerializer,
            404: openapi.Response('团队不存在'),
            400: openapi.Response('参数错误'),
            500: openapi.Response('内部错误'),
        },
        tags=['应用管理']
    )
    def post(self, request, team_alias, region_name):
        """创建应用"""
        try:
            team = team_services.get_team_by_team_alias(team_alias)
            if not team:
                return Response(general_message(404, "team not found", "团队不存在"), status=http_status.HTTP_404_NOT_FOUND)

            # 验证请求参数
            serializer = CreateAppRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(general_message(400, "params error", "参数错误"), status=http_status.HTTP_400_BAD_REQUEST)

            # 创建应用
            app = group_service.create_app(
                tenant=team,
                region_name=region_name,
                app_name=serializer.validated_data["app_name"],
                username=request.user.get_username(),
                k8s_app=serializer.validated_data.get("app_name", ""),
                eid=self.enterprise.enterprise_id
            )

            # 序列化响应数据
            response_serializer = CreateAppResponseSerializer({
                "bean": app,
                "code": 200,
                "msg": "success",
                "msg_show": "创建成功"
            })
            return Response(response_serializer.data, status=http_status.HTTP_200_OK)
        except ServiceHandleException as e:
            return Response(general_message(e.status_code, e.msg, e.msg_show), status=e.status_code)
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


class McpComponentsView(BaseOpenAPIView):
    """
    组件列表管理接口
    
    提供应用下组件相关的操作接口，包括：
    - 获取应用下的组件列表
    - 支持查看组件的基本信息（如内存、CPU等资源配置）
    """
    @swagger_auto_schema(
        operation_description="获取应用下的组件列表",
        responses={
            200: openapi.Response('获取成功', ComponentBaseSerializer(many=True)),
            404: openapi.Response('团队不存在'),
            500: openapi.Response('内部错误'),
        },
        tags=['组件管理']
    )
    def get(self, request, team_alias, app_id):
        """获取应用下的组件列表"""
        try:
            team = team_services.get_team_by_team_alias(team_alias)
            if not team:
                return Response(general_message(404, "team not found", "团队不存在"), status=http_status.HTTP_404_NOT_FOUND)
            app = group_repo.get_app_by_pk(app_id)

            components = service_repo.get_group_service_by_group_id(
                group_id=app_id,
                region_name=app.region_name,
                team_id=team.tenant_id,
                team_name=team.tenant_name,
                enterprise_id=team.enterprise_id
            )
            serializer = ComponentBaseSerializer(components, many=True)
            result = general_message(200, "success", "获取成功", list=serializer.data)
            return Response(result, status=http_status.HTTP_200_OK)
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


class McpComponentView(BaseOpenAPIView):
    """
    组件管理接口
    
    提供组件创建相关的操作接口，包括：
    - 基于源码创建组件
    - 自动进行代码检测
    - 支持自动构建和部署
    """
    @swagger_auto_schema(
        operation_description="创建组件",
        request_body=CreateComponentRequestSerializer,
        responses={
            200: ComponentBaseSerializer,
            404: openapi.Response('团队或应用不存在'),
            400: openapi.Response('参数错误'),
            500: openapi.Response('内部错误'),
        },
        tags=['组件管理']
    )
    def post(self, request, team_alias, app_id):
        """创建组件"""
        try:
            # 获取团队信息
            team = team_services.get_team_by_team_alias(team_alias)
            if not team:
                return Response(general_message(404, "team not found", "团队不存在"), status=http_status.HTTP_404_NOT_FOUND)

            # 获取应用信息
            app = group_repo.get_app_by_pk(app_id)
            if not app:
                return Response(general_message(404, "app not found", "应用不存在"), status=http_status.HTTP_404_NOT_FOUND)

            # 验证请求参数
            serializer = CreateComponentRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(general_message(400, "params error", "参数错误"), status=http_status.HTTP_400_BAD_REQUEST)

            # 1. 创建组件
            service_cname = serializer.validated_data["service_cname"]
            repo_url = serializer.validated_data["repo_url"]
            branch = serializer.validated_data["branch"]
            username = serializer.validated_data.get("username", "")
            password = serializer.validated_data.get("password", "")

            # 校验组件英文名称
            if app_service.is_k8s_component_name_duplicate(app_id, service_cname):
                return Response(general_message(400, "component name exists", "组件英文名称已存在"), status=http_status.HTTP_400_BAD_REQUEST)

            code, msg_show, component = app_service.create_source_code_app(
                region=app.region_name,
                tenant=team,
                user=self.user,
                service_code_from="gitlab_manual",
                service_cname=service_cname,
                service_code_clone_url=repo_url,
                service_code_id="",
                service_code_version=branch,
                server_type="git",
                k8s_component_name=service_cname,
                check_uuid=None,
                event_id=make_uuid(),
                oauth_service_id=None,
                git_full_name=None
            )
            
            if code != 200:
                return Response(general_message(code, "create failed", msg_show), status=code)

            # 添加组件到应用
            code, msg_show = group_service.add_service_to_group(
                team,
                app.region_name,
                app_id,
                component.service_id
            )
            if code != 200:
                return Response(general_message(code, "add to app failed", msg_show), status=code)

            if username or password:
                app_service.create_service_source_info(team, component, username, password)

            # 2. 开始代码检测
            code, msg, check_info = app_check_service.check_service(team, component, False, "", self.user)
            if code != 200:
                return Response(general_message(code, "check failed", msg), status=code)

            try:
                # 3. 循环获取检测结果
                max_retries = 30  # 最大重试次数
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        check_uuid = check_info.get("check_uuid")
                        res, body = region_api.get_service_check_info(app.region_name, team.tenant_name, check_uuid)
                        bean = body["bean"]
                        if not bean["check_status"]:
                            bean["check_status"] = "checking"
                        bean["check_status"] = bean["check_status"].lower()
                        status = bean.get("check_status", "")
                        if status == "checking" or status == "":
                            time.sleep(2)  # 等待2秒后重试
                            retry_count += 1
                            continue
                        elif status == "success":
                            if bean["service_info"] and len(bean["service_info"]) < 2:
                                app_check_service.save_service_check_info(team, app.ID, component, bean)
                            app_check_service.wrap_service_check_info(component, bean)
                            break
                        else:
                            return Response(general_message(500, "check failed", "代码检测失败"), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
                    except region_api.CallApiError:
                        time.sleep(2)  # 如果API调用失败，等待2秒后重试
                        retry_count += 1
                        continue

                if retry_count >= max_retries:
                    return Response(general_message(500, "check timeout", "代码检测超时"), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

                # 4. 开始构建
                app_service.create_region_service(team, component, self.user.nick_name)
                arch_service.update_affinity_by_arch(component.arch, team, app.region_name, component)

                app_manage_service.deploy(team, component, self.user)

                # 返回组件信息
                result = {
                    "service_id": component.service_id,
                    "service_cname": component.service_cname,
                    "update_time": component.update_time,
                }
                
                return Response(general_message(200, "success", "创建成功", bean=result), status=http_status.HTTP_200_OK)
            except region_api.CallApiError as e:
                print(e)
                return Response(general_message(500, "region error", "集群接口调用失败"), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
            except ServiceHandleException as e:
                return Response(general_message(e.status_code, e.msg, e.msg_show), status=e.status_code)
            except Exception as e:
                print(e)
                return Response(general_message(500, "error", "创建失败"), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


class McpComponentDetailView(BaseOpenAPIView):
    """
    组件详情管理接口
    
    提供组件详细信息的操作接口，包括：
    - 获取组件的运行状态
    - 查看组件的详细配置信息
    - 查看组件的运行实例（Pod）信息
    """
    
    def _get_team_and_component(self, team_alias, component_id):
        """获取团队和组件信息"""
        team = team_services.get_team_by_team_alias(team_alias)
        if not team:
            return None, None, Response(
                general_message(404, "team not found", "团队不存在"), 
                status=http_status.HTTP_404_NOT_FOUND
            )
        
        component = service_repo.get_service_by_tenant_and_alias(team.tenant_id, service_id=component_id)
        if not component:
            return team, None, Response(
                general_message(404, "component not found", "组件不存在"), 
                status=http_status.HTTP_404_NOT_FOUND
            )
        
        return team, component, None
    
    def _get_component_status(self, component, team):
        """获取组件状态"""
        try:
            status_info = region_api.check_service_status(
                component.service_region,
                team.tenant_name,
                component.service_alias,
                team.enterprise_id
            )
            return status_info.get("bean", {}).get("status_cn", "未知")
        except Exception as e:
            print(f"获取组件状态失败：{e}")
            return "未知"
    
    def _build_access_url(self, domain):
        """构建访问 URL"""
        if hasattr(domain, 'domain_name'):  # HTTP 域名
            protocol = "https" if domain.certificate_id > 0 else "http"
            url = f"{protocol}://{domain.domain_name}"
            if hasattr(domain, 'domain_path') and domain.domain_path and domain.domain_path != "/":
                url += domain.domain_path
            return url
        else:  # TCP 域名
            return domain.end_point
    
    def _merge_access_urls_to_ports(self, ports, http_domains, tcp_domains):
        """将访问地址信息合并到端口中"""
        # 创建端口到域名的映射，提高查询效率
        http_domain_map = {}
        tcp_domain_map = {}
        
        for domain in http_domains:
            port = domain.container_port
            if port not in http_domain_map:
                http_domain_map[port] = []
            http_domain_map[port].append(domain)
        
        for domain in tcp_domains:
            port = domain.container_port
            if port not in tcp_domain_map:
                tcp_domain_map[port] = []
            tcp_domain_map[port].append(domain)
        
        # 构建端口列表
        port_list = []
        for port in ports:
            port_info = {
                "container_port": port.container_port,
                "protocol": port.protocol,
                "is_outer_service": port.is_outer_service,
                "is_inner_service": port.is_inner_service,
                "access_urls": []
            }
            
            # 添加该端口的所有访问地址
            port_number = port.container_port
            
            # 添加 HTTP 访问地址
            for domain in http_domain_map.get(port_number, []):
                port_info["access_urls"].append(self._build_access_url(domain))
            
            # 添加 TCP 访问地址
            for domain in tcp_domain_map.get(port_number, []):
                port_info["access_urls"].append(self._build_access_url(domain))
            
            port_list.append(port_info)
        
        return port_list
    
    @swagger_auto_schema(
        operation_description="获取组件详情",
        responses={
            200: openapi.Response('获取成功', ComponentDetailSerializer),
            404: openapi.Response('团队或组件不存在'),
            500: openapi.Response('内部错误'),
        },
        tags=['组件管理']
    )
    def get(self, request, team_alias, app_id, component_id):
        """获取组件详情"""
        try:
            # 获取团队和组件信息
            team, component, error_response = self._get_team_and_component(team_alias, component_id)
            if error_response:
                return error_response

            # 获取组件状态
            status_cn = self._get_component_status(component, team)

            # 并行获取组件相关信息
            ports = port_service.get_service_ports(component)
            env_vars = env_var_service.get_service_inner_env(component)
            volumes = volume_service.get_service_volumes(team, component)
            http_domains = domain_service.get_http_ruls_by_service_ids([component.service_id])
            tcp_domains = domain_service.get_tcp_rules_by_service_ids(component.service_region, [component.service_id])

            # 合并访问地址到端口信息
            port_list = self._merge_access_urls_to_ports(ports, http_domains, tcp_domains)

            # 构建响应数据
            result = {
                "service_id": component.service_id,
                "service_cname": component.service_cname,
                "service_alias": component.service_alias,
                "update_time": component.update_time,
                "min_memory": component.min_memory,
                "min_cpu": component.min_cpu,
                "status_cn": status_cn,
                "ports": port_list,
                "envs": env_vars,
                "volumes": volumes
            }
            
            serializer = ComponentDetailSerializer(result)
            return Response(general_message(200, "success", "获取成功", bean=serializer.data), status=http_status.HTTP_200_OK)
            
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


class McpComponentLogsView(BaseOpenAPIView):
    """
    组件日志管理接口
    
    提供组件日志相关的操作接口，包括：
    - 获取组件容器的运行日志
    - 支持实时日志流式输出
    - 支持指定Pod和容器查看日志
    - 支持日志跟随（follow）模式
    """
    @swagger_auto_schema(
        operation_description="获取组件日志",
        manual_parameters=[
            openapi.Parameter('pod_name', openapi.IN_QUERY, description='Pod名称', type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('container_name', openapi.IN_QUERY, description='容器名称', type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('follow', openapi.IN_QUERY, description='是否跟随日志', type=openapi.TYPE_BOOLEAN, required=False),
        ],
        responses={
            200: openapi.Response('获取成功', ComponentLogSerializer),
            404: openapi.Response('团队或组件不存在'),
            400: openapi.Response('参数错误'),
            500: openapi.Response('内部错误'),
        },
        tags=['组件管理']
    )
    def get(self, request, team_alias, app_id, component_id):
        """获取组件日志"""
        try:
            team = team_services.get_team_by_team_alias(team_alias)
            if not team:
                return Response(general_message(404, "team not found", "团队不存在"), status=http_status.HTTP_404_NOT_FOUND)
            
            component = service_repo.get_service_by_tenant_and_alias(team.tenant_id, service_id=component_id)
            if not component:
                return Response(general_message(404, "component not found", "组件不存在"), status=http_status.HTTP_404_NOT_FOUND)
            
            pod_name = request.GET.get('pod_name')
            container_name = request.GET.get('container_name')
            follow = request.GET.get('follow', False)
            
            if not pod_name or not container_name:
                return Response(general_message(400, "params error", "缺少必要参数"), status=http_status.HTTP_400_BAD_REQUEST)
            
            log_stream = component_log_service.get_component_log_stream(
                tenant_name=team.tenant_name,
                region_name=component.service_region,
                service_alias=component.service_alias,
                pod_name=pod_name,
                container_name=container_name,
                follow=follow
            )
            
            return Response(log_stream, status=http_status.HTTP_200_OK)
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


class McpComponentPortsView(BaseOpenAPIView):
    """
    组件端口管理接口
    
    提供组件端口相关的操作接口，包括：
    - 获取组件的端口列表
    - 添加组件端口
    """
    @swagger_auto_schema(
        operation_description="获取组件端口列表",
        responses={
            200: openapi.Response('获取成功', PortBaseSerializer(many=True)),
            404: openapi.Response('团队或组件不存在'),
            500: openapi.Response('内部错误'),
        },
        tags=['组件管理']
    )
    def get(self, request, team_alias, app_id, component_id):
        """获取组件端口列表"""
        try:
            team = team_services.get_team_by_team_alias(team_alias)
            if not team:
                return Response(general_message(404, "team not found", "团队不存在"), status=http_status.HTTP_404_NOT_FOUND)
            
            component = service_repo.get_service_by_tenant_and_alias(team.tenant_id, service_id=component_id)
            if not component:
                return Response(general_message(404, "component not found", "组件不存在"), status=http_status.HTTP_404_NOT_FOUND)

            ports = port_service.get_service_ports(component)
            serializer = PortBaseSerializer(ports, many=True)
            result = general_message(200, "success", "获取成功", list=serializer.data)
            return Response(result, status=http_status.HTTP_200_OK)
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description="添加组件端口",
        request_body=AddPortRequestSerializer,
        responses={
            200: openapi.Response('添加成功', PortBaseSerializer),
            400: openapi.Response('参数错误'),
            404: openapi.Response('团队或组件不存在'),
            500: openapi.Response('内部错误'),
        },
        tags=['组件管理']
    )
    def post(self, request, team_alias, app_id, component_id):
        """添加组件端口"""
        try:
            team = team_services.get_team_by_team_alias(team_alias)
            if not team:
                return Response(general_message(404, "team not found", "团队不存在"), status=http_status.HTTP_404_NOT_FOUND)
            
            component = service_repo.get_service_by_tenant_and_alias(team.tenant_id, service_id=component_id)
            if not component:
                return Response(general_message(404, "component not found", "组件不存在"), status=http_status.HTTP_404_NOT_FOUND)

            # 验证请求参数
            serializer = AddPortRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(general_message(400, "params error", "参数错误"), status=http_status.HTTP_400_BAD_REQUEST)

            # 添加端口
            port = serializer.validated_data["port"]
            protocol = serializer.validated_data["protocol"]
            is_outer_service = serializer.validated_data.get("is_outer_service", False)

            # 检查端口是否已存在
            ports = port_service.get_service_ports(component)
            if any(p.container_port == port for p in ports):
                return Response(general_message(400, "port exists", "端口已存在"), status=http_status.HTTP_400_BAD_REQUEST)

            # 添加端口
            code, msg, new_port_obj = port_service.add_service_port(
                team,
                component,
                port,
                protocol,
                port_alias=None,
                is_inner_service=True,
                is_outer_service=False  # 先创建端口，然后再开启对外服务
            )

            if code != 200:
                return Response(general_message(code, "add port failed", msg), status=code)

            # 如果需要开启对外服务，调用相应的方法
            if is_outer_service:
                from console.repositories.region_repo import region_repo
                from console.repositories.group import group_repo
                
                region = region_repo.get_region_by_region_name(component.service_region)
                app = group_repo.get_app_by_pk(app_id)
                
                # 获取刚添加的端口对象
                deal_port = port_service.get_service_port_by_port(component, port)
                if not deal_port:
                    return Response(general_message(500, "get port failed", "获取端口信息失败"), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # 调用默认开启对外服务的方法
                code, msg = port_service.defalut_open_outer(team, component, region, deal_port, app)
                if code != 200:
                    return Response(general_message(code, "open outer failed", msg), status=code)

            # 获取新添加的端口信息
            ports = port_service.get_service_ports(component)
            new_port = next((p for p in ports if p.container_port == port), None)
            if not new_port:
                return Response(general_message(500, "get port failed", "获取端口信息失败"), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

            serializer = PortBaseSerializer(new_port)
            result = general_message(200, "success", "端口添加成功", bean=serializer.data)
            return Response(result, status=http_status.HTTP_200_OK)
        except region_api.CallApiError as e:
            return Response(general_message(500, "region error", "集群接口调用失败"), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response(general_message(500, "error", str(e)), status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
