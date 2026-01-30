# -*- coding: utf8 -*-
"""
Gray release service for application-level canary deployments
"""
import logging
import traceback

from console.exception.main import ServiceHandleException
from console.models.main import GrayReleaseStatus
from console.repositories.app_config import domain_repo
from console.repositories.gray_release_repo import gray_release_repo
from console.services.app_actions import app_manage_service
from console.services.app_config.domain_service import DomainService
from console.services.app import app_market_service
from console.services.group_service import group_service
from console.services.market_app_service import market_app_service
from django.db import transaction
from django.forms.models import model_to_dict
from www.models.main import ServiceDomain, TenantServiceInfo
from www.utils.crypt import make_uuid

logger = logging.getLogger("default")


class GrayReleaseService(object):
    """Service for managing application-level gray releases"""

    def __init__(self):
        self.domain_service = DomainService()
        self.app_manage = app_manage_service

    def validate_gray_ratio(self, gray_ratio):
        """Validate gray ratio is between 0 and 100"""
        if not isinstance(gray_ratio, int):
            raise ServiceHandleException(
                msg="gray_ratio must be integer",
                msg_show="灰度比例必须为整数",
                status_code=400
            )
        if gray_ratio < 0 or gray_ratio > 100:
            raise ServiceHandleException(
                msg="gray_ratio must be between 0 and 100",
                msg_show="灰度比例必须在0-100之间",
                status_code=400
            )

    def _delete_new_service_domains(self, team, region_name, new_service_ids):
        """
        Delete domains (ApisixRoutes) automatically created for new services during gray release
        删除灰度发布时为新服务自动创建的域名
        """
        try:
            from www.apiclient.regionapi import RegionInvokeApi
            from www.models.main import TenantServicesPort
            from console.repositories.region_repo import region_repo

            region_api = RegionInvokeApi()
            region = region_repo.get_region_by_region_name(region_name)
            if not region:
                logger.error(f"[GrayRelease] Region not found: {region_name}")
                return

            logger.info(f"[GrayRelease] Checking for auto-created domains for {len(new_service_ids)} new services")

            # 获取新服务对象
            new_services = []
            for service_id in new_service_ids:
                service = TenantServiceInfo.objects.filter(
                    tenant_id=team.tenant_id,
                    service_id=service_id
                ).first()
                if service:
                    new_services.append(service)

            # 获取所有路由
            try:
                response = region_api.get_api_gateway(region, team, None)  # 获取全部路由
                routes = response.get("list", [])
                logger.info(f"[GrayRelease] Found {len(routes)} total routes")

                # 查找新服务的路由
                deleted_count = 0
                for route in routes:
                    backends = route.get("backends", [])
                    route_name = route.get("name", "")

                    # 检查是否是新服务的路由
                    if len(backends) != 1:
                        continue  # 跳过多 backend 的路由

                    backend_service_name = backends[0].get("serviceName", "")
                    if not backend_service_name:
                        continue

                    # 检查这个 backend 是否属于新服务
                    for new_service in new_services:
                        # 查找该服务的端口
                        ports = TenantServicesPort.objects.filter(
                            tenant_id=team.tenant_id,
                            service_id=new_service.service_id,
                            is_outer_service=True
                        )

                        for port in ports:
                            if port.k8s_service_name == backend_service_name:
                                # 找到了新服务的路由，删除它
                                logger.info(f"[GrayRelease] Found auto-created route for new service {new_service.service_alias}: {route_name}")
                                logger.info(f"[GrayRelease] Backend: {backend_service_name}")

                                # 从 route_name 中提取 region_app_id (格式: region_app_id|actual_name|...)
                                region_app_id = ""
                                if "|" in route_name:
                                    parts = route_name.split("|", 1)
                                    if len(parts) >= 1:
                                        region_app_id = parts[0]

                                try:
                                    logger.info(f"[GrayRelease] Deleting route: {route_name}")
                                    region_api.delete_gateway_http_route(
                                        region,
                                        team.tenant_name,
                                        team.namespace,
                                        route_name,
                                        region_app_id
                                    )
                                    deleted_count += 1
                                    logger.info(f"[GrayRelease] Successfully deleted route: {route_name}")
                                except Exception as e:
                                    logger.error(f"[GrayRelease] Failed to delete route {route_name}: {e}")
                                    import traceback
                                    logger.error(f"[GrayRelease] Traceback: {traceback.format_exc()}")

                logger.info(f"[GrayRelease] Deleted {deleted_count} auto-created routes")

            except Exception as e:
                import traceback
                logger.error(f"[GrayRelease] Failed to get routes: {e}")
                logger.error(f"[GrayRelease] Traceback: {traceback.format_exc()}")

        except Exception as e:
            import traceback
            logger.error(f"[GrayRelease] Failed to delete new service domains: {e}")
            logger.error(f"[GrayRelease] Traceback: {traceback.format_exc()}")
            # 不抛出异常，因为这不是关键步骤

    def _update_apisix_route_weights(self, team, region, app, domain,
                                     original_service, new_service,
                                     original_weight, new_weight, is_full_release=False):
        """
        Update ApisixRoute to configure weighted backends for gray release
        更新 ApisixRoute 配置，为灰度发布设置权重后端

        Args:
            is_full_release: If True, only use new backend (full release)
        """
        try:
            from www.apiclient.regionapi import RegionInvokeApi
            from www.models.main import TenantServicesPort

            region_api = RegionInvokeApi()

            logger.info(f"[GrayRelease] Updating ApisixRoute for weighted traffic distribution")

            # 获取新服务的端口信息
            new_port = TenantServicesPort.objects.filter(
                tenant_id=team.tenant_id,
                service_id=new_service.service_id,
                is_outer_service=True  # 只查找对外服务的端口
            ).first()

            if not new_port:
                logger.error(f"[GrayRelease] No outer port found for new service: {new_service.service_id}")
                raise ServiceHandleException(
                    msg="new service has no outer port",
                    msg_show="新服务没有对外端口",
                    status_code=400
                )

            # 构建新的 backends 配置（包含权重）
            new_backends = []

            # 添加新服务 backend (总是添加，权重为 new_weight)
            if new_weight > 0:
                new_backends.append({
                    "serviceName": new_port.k8s_service_name,
                    "servicePort": new_port.container_port,
                    "weight": new_weight
                })
                logger.info(f"[GrayRelease] Added new backend: {new_port.k8s_service_name}:{new_port.container_port} (weight={new_weight})")

            # 如果不是全量发布，添加原始服务 backend
            if not is_full_release and original_weight > 0:
                # 获取原始服务的端口信息
                original_port = TenantServicesPort.objects.filter(
                    tenant_id=team.tenant_id,
                    service_id=original_service.service_id,
                    is_outer_service=True,
                    container_port=new_port.container_port  # 端口要一致
                ).first()

                if original_port:
                    new_backends.append({
                        "serviceName": original_port.k8s_service_name,
                        "servicePort": original_port.container_port,
                        "weight": original_weight
                    })
                    logger.info(f"[GrayRelease] Added original backend: {original_port.k8s_service_name}:{original_port.container_port} (weight={original_weight})")
                else:
                    logger.warning(f"[GrayRelease] Original service port not found, skipping original backend: {original_service.service_id}")

                raise ServiceHandleException(
                    msg="route name not found",
                    msg_show="路由名称未找到",
                    status_code=500
                )

            # 按 | 分割，取中间部分
            name_parts = original_name.split('|')
            if len(name_parts) != 3:
                logger.error(f"[GrayRelease] Invalid original_name format: {original_name}")
                raise ServiceHandleException(
                    msg="invalid route name format",
                    msg_show="路由名称格式错误",
                    status_code=500
                )

            region_app_id = name_parts[0]
            route_name = name_parts[1]  # 中间部分是实际的路由名称
            service_alias_suffix = name_parts[2]

            logger.info(f"[GrayRelease] Parsed original_name: region_app_id={region_app_id}, route_name={route_name}, suffix={service_alias_suffix}")
            logger.info(f"[GrayRelease] Updating route: {route_name}")

            # 使用 console API 更新域名权重
            try:
                from www.apiclient.regionapi import RegionInvokeApi
                from console.repositories.region_app import region_app_repo
                region_api = RegionInvokeApi()

                logger.info(f"[GrayRelease] Updating route via console API")
                logger.info(f"[GrayRelease] Route name: {route_name}")

                # 获取 region_app_id (需要转换回内部 app_id)
                # 从 domain 中获取，或者使用解析出的 region_app_id

                # 构建更新请求体
                # 需要包含完整的路由配置
                match_config = domain.get("match", {})
                print(team.namespace)
                update_body = {
                    "namespace": team.namespace,
                    "name": route_name,  # 使用从 original_name 解析出的路由名称
                    "app_id": region_app_id,  # 使用从 original_name 解析出的区域应用ID
                    "section_name": domain.get("section_name", "default"),
                    "gateway_name": domain.get("gateway_name", "default"),
                    "gateway_namespace": domain.get("gateway_namespace", "rbd-system"),
                    "hosts": match_config.get("hosts", []),  # 从 match 中提取 hosts
                    "rules": domain.get("rules", []),  # 路由规则
                    "backends": new_backends,  # 更新为加权的 backends
                    "plugins": domain.get("plugins", []),
                    "websocket": domain.get("websocket", False),
                    "authentication": domain.get("authentication", {})
                }

                logger.info(f"[GrayRelease] Update body: {update_body}")
                logger.info(f"[GrayRelease] New backends: {new_backends}")

                # 调用 RegionAPI 更新路由 - 使用正确的 ApisixRoute 接口
                # 构建请求路径 - 添加 appID 查询参数
                path = f"/api-gateway/v1/{team.tenant_name}/routes/http?appID={app.app_id}"
                # 构建请求体 - 使用后端期望的格式
                put_body = {
                    "name": route_name,
                    "app_id": region_app_id,
                    "namespace": team.namespace,
                    "section_name": domain.get("section_name", "default"),
                    "gateway_name": domain.get("gateway_name", "default"),
                    "gateway_namespace": domain.get("gateway_namespace", "rbd-system"),
                    "match": match_config,
                    "rules": domain.get("rules", []),
                    "backends": new_backends,
                    "plugins": domain.get("plugins", []),
                    "websocket": domain.get("websocket", False),
                    "authentication": domain.get("authentication", {})
                }

                logger.info(f"[GrayRelease] Updating ApisixRoute via API: {path}")
                logger.info(f"[GrayRelease] Request body: {put_body}")

                # 使用 api_gateway_post_proxy 方法调用后端 API (POST 方法)
                result = region_api.api_gateway_post_proxy(
                    region,
                    team.tenant_name,
                    path,
                    put_body,
                    app.app_id
                )

                logger.info(f"[GrayRelease] Successfully updated route via console API")
                logger.info(f"[GrayRelease] Result: {result}")

            except Exception as e:
                import traceback
                logger.error(f"[GrayRelease] Failed to update route via console API: {e}")
                logger.error(f"[GrayRelease] Traceback: {traceback.format_exc()}")
                logger.warning(f"[GrayRelease] Route update failed, please update manually")
                logger.info(f"[GrayRelease] Manual update: Edit ApisixRoute {route_name} in namespace {team.namespace}")
                logger.info(f"[GrayRelease] Set backends to: {new_backends}")
                # 不抛出异常，允许继续执行
                logger.warning(f"[GrayRelease] Continuing without automatic route update")

        except ServiceHandleException:
            raise
        except Exception as e:
            logger.exception(f"[GrayRelease] Failed to update ApisixRoute weights: {e}")
            raise ServiceHandleException(
                msg=f"failed to update apisix route: {str(e)}",
                msg_show=f"更新网关路由失败: {str(e)}",
                status_code=500
            )

    def get_domain_by_name(self, team, region, app_id, domain_name):
        """
        Get domain from API Gateway by domain_name
        域名数据不入库，需要从 API 网关获取
        """
        try:
            from www.apiclient.regionapi import RegionInvokeApi
            region_api = RegionInvokeApi()

            logger.info(f"[GrayRelease] Getting domain from API Gateway: domain={domain_name}, app_id={app_id}, team={team.tenant_name}")

            # 调用 API 网关获取路由列表
            response = region_api.get_api_gateway(region, team, app_id)
            domains = response.get("list", [])

            logger.info(f"[GrayRelease] API Gateway returned {len(domains)} routes")

            # 查找匹配的域名
            matched_domains = []
            all_hosts = []  # 用于错误消息
            for domain in domains:
                # 真正的域名在 match.hosts 字段中
                match_info = domain.get("match", {})
                hosts = match_info.get("hosts", [])
                all_hosts.extend(hosts)

                # 检查是否有匹配的域名
                if domain_name in hosts:
                    matched_domains.append(domain)
                    logger.info(f"[GrayRelease] Found matching domain: {domain_name} in route {domain.get('name')}")

            if not matched_domains:
                logger.error(f"[GrayRelease] Domain not found: {domain_name}. Available domains: {all_hosts}")
                raise ServiceHandleException(
                    msg="domain not found in api gateway",
                    msg_show=f"API网关中未找到域名: {domain_name}。当前应用可用域名: {', '.join(all_hosts) if all_hosts else '无'}",
                    status_code=404
                )

            if len(matched_domains) > 1:
                logger.error(f"[GrayRelease] Domain bound to multiple services: {domain_name}")
                raise ServiceHandleException(
                    msg="domain bound to multiple services",
                    msg_show="域名绑定到多个服务，无法进行灰度发布",
                    status_code=400
                )

            logger.info(f"[GrayRelease] Successfully found domain: {domain_name}")
            return matched_domains[0]

        except Exception as e:
            if isinstance(e, ServiceHandleException):
                raise e
            logger.exception(f"[GrayRelease] Failed to get domain from API gateway: {e}")
            raise ServiceHandleException(
                msg=f"failed to get domain: {str(e)}",
                msg_show=f"获取域名失败: {str(e)}",
                status_code=500
            )

    def validate_app(self, team, region_name, app):
        """Validate application exists and belongs to team"""
        if not app:
            raise ServiceHandleException(
                msg="app not found",
                msg_show="应用不存在",
                status_code=404
            )
        if app.tenant_id != team.tenant_id:
            raise ServiceHandleException(
                msg="app does not belong to this team",
                msg_show="应用不属于该团队",
                status_code=403
            )
        logger.info("Validated app {0} with ID {1}".format(app.group_name, app.ID))

    def install_template_to_app(self, team, region_name, user, app, template_id, market_name, install_from_cloud):
        """Install application template to the original app (for gray release, skip domain creation)"""
        try:
            if install_from_cloud:
                # Install from cloud market
                if not market_name:
                    raise ServiceHandleException(
                        msg="market_name is required when install_from_cloud is True",
                        msg_show="从云端安装时必须指定市场名称",
                        status_code=400
                    )

                # Get market and app version info
                market = app_market_service.get_app_market_by_name(team.enterprise_id, market_name)
                if not market:
                    raise ServiceHandleException(
                        msg="market not found",
                        msg_show="应用市场不存在",
                        status_code=404
                    )

                app_model, app_version_info = app_market_service.cloud_app_model_to_db_model(
                    market, template_id, "", for_install=True
                )

                if not app_model:
                    raise ServiceHandleException(
                        msg="template not found",
                        msg_show="应用模板不存在",
                        status_code=404
                    )

                # Install the template to the original app
                # For gray release: skip_create_domain=True to avoid creating duplicate domains
                market_app_service.install_service(
                    team, region_name, user, app.ID, app_model, app_version_info,
                    is_deploy=True, install_from_cloud=True, market_name=market_name,
                    skip_create_domain=True  # Gray release: don't create new domains
                )
            else:
                # Install from local app model
                from console.repositories.market_app_repo import rainbond_app_repo

                # Get app model by template_id (which is app_model_key in local storage)
                app_model = rainbond_app_repo.get_rainbond_app_by_app_id(template_id)
                if not app_model:
                    raise ServiceHandleException(
                        msg="template not found",
                        msg_show="应用模板不存在",
                        status_code=404
                    )

                # Get app version (use the latest version)
                app_versions = rainbond_app_repo.get_rainbond_app_versions(template_id)
                if not app_versions:
                    raise ServiceHandleException(
                        msg="template version not found",
                        msg_show="应用模板版本不存在",
                        status_code=404
                    )
                app_version_info = app_versions[0]

                # Install from local template to the original app
                # For gray release: skip_create_domain=True to avoid creating duplicate domains
                market_app_service.install_service(
                    team, region_name, user, app.ID, app_model, app_version_info,
                    is_deploy=True, install_from_cloud=False,
                    skip_create_domain=True  # Gray release: don't create new domains
                )

            logger.info("Installed template {0} to app {1}".format(template_id, app.group_name))
        except ServiceHandleException:
            raise
        except Exception as e:
            logger.error("Failed to install template to app: {0}".format(traceback.format_exc()))
            raise ServiceHandleException(
                msg="failed to install template: {0}".format(str(e)),
                msg_show="安装应用模板失败",
                status_code=500
            )

    def setup_domain_weights(self, team, region, app, domain_name, gray_ratio):
        """Setup domain weights for gray release - all services in the same app"""
        try:
            logger.info("[GrayRelease] Starting setup_domain_weights: app_id={0}, domain={1}, gray_ratio={2}%".format(
                app.ID, domain_name, gray_ratio))

            # Get domain from API Gateway
            domain = self.get_domain_by_name(team, region, app.ID, domain_name)

            # Get service from backend configuration
            backends = domain.get("backends", [])
            logger.info(f"[GrayRelease] Found {len(backends)} backends for domain")
            if not backends:
                logger.error(f"[GrayRelease] No backend service found for domain: {domain_name}")
                raise ServiceHandleException(
                    msg="no backend service found for domain",
                    msg_show="域名未配置后端服务",
                    status_code=400
                )

            # Get k8s service name from first backend
            k8s_service_name = backends[0].get("serviceName", "")
            logger.info(f"[GrayRelease] k8s_service_name: {k8s_service_name}")
            if not k8s_service_name:
                logger.error(f"[GrayRelease] Backend service name is empty")
                raise ServiceHandleException(
                    msg="backend service name is empty",
                    msg_show="后端服务名称为空",
                    status_code=400
                )

            # k8s_service_name 存储在端口表中，需要通过端口查找组件
            from console.repositories.app_config import port_repo
            from www.models.main import TenantServicesPort

            logger.info(f"[GrayRelease] Searching for port with k8s_service_name: {k8s_service_name}")

            # 查找对应的端口记录
            port = TenantServicesPort.objects.filter(
                tenant_id=team.tenant_id,
                k8s_service_name=k8s_service_name
            ).first()

            if not port:
                logger.error(f"[GrayRelease] Port not found for k8s service: {k8s_service_name}")
                raise ServiceHandleException(
                    msg=f"port not found for k8s service: {k8s_service_name}",
                    msg_show=f"未找到对应的端口配置: {k8s_service_name}",
                    status_code=404
                )

            logger.info(f"[GrayRelease] Found port: service_id={port.service_id}, container_port={port.container_port}")

            # 通过端口的 service_id 获取组件
            logger.info(f"[GrayRelease] Looking for original service: service_id={port.service_id}")
            original_service = TenantServiceInfo.objects.filter(
                tenant_id=team.tenant_id,
                service_id=port.service_id
            ).first()
            if not original_service:
                logger.error(f"[GrayRelease] Original service not found: {port.service_id}")
                raise ServiceHandleException(
                    msg=f"original service not found: {port.service_id}",
                    msg_show=f"未找到对应的组件: {port.service_id}",
                    status_code=404
                )

            logger.info(f"[GrayRelease] Found original service: {original_service.service_cname} ({original_service.service_alias})")

            # Verify the service belongs to the app
            service_group_relations = group_service.get_group_services(app.ID)
            service_ids = [s.service_id for s in service_group_relations]
            logger.info(f"[GrayRelease] App has {len(service_ids)} services")
            if original_service.service_id not in service_ids:
                logger.error(f"[GrayRelease] Domain does not belong to the app: service_id={original_service.service_id} not in app services")
                raise ServiceHandleException(
                    msg="domain does not belong to the app",
                    msg_show="域名不属于该应用",
                    status_code=400
                )

            # Get the service_cname to find the new service version
            service_cname = original_service.service_cname
            logger.info(f"[GrayRelease] Searching for new version service with same service_cname: {service_cname}")

            # Find the new service version in the same app by service_cname
            # The new service will have the same service_cname but different service_id
            new_service = None
            for svc in service_group_relations:
                if svc.service_id == original_service.service_id:
                    continue  # Skip the original service
                svc_obj = TenantServiceInfo.objects.filter(
                    tenant_id=team.tenant_id,
                    service_id=svc.service_id
                ).first()
                if svc_obj:
                    logger.info(f"[GrayRelease] Checking service: {svc_obj.service_cname} (service_id={svc_obj.service_id})")
                    if svc_obj.service_cname == service_cname:
                        new_service = svc_obj
                        logger.info(f"[GrayRelease] Found matching new version service: {new_service.service_alias}")
                        break

            if not new_service:
                logger.error(f"[GrayRelease] New service version not found. service_cname={service_cname}, checked {len(service_group_relations)} services")
                raise ServiceHandleException(
                    msg="new service version not found in app",
                    msg_show=f"应用中未找到新版本服务（service_cname={service_cname}）。请确保已安装新版本并且新旧版本的组件名称相同。",
                    status_code=404
                )

            # Calculate weights
            original_weight = 100 - gray_ratio
            new_weight = gray_ratio

            logger.info("[GrayRelease] Setting up gray release weights: original={0}%, new={1}%".format(
                original_weight, new_weight))
            logger.info("[GrayRelease] Original service: {0} ({1}, service_id={2})".format(
                original_service.service_cname, original_service.service_alias, original_service.service_id))
            logger.info("[GrayRelease] New service: {0} ({1}, service_id={2})".format(
                new_service.service_cname, new_service.service_alias, new_service.service_id))

            # 更新 ApisixRoute 配置权重
            self._update_apisix_route_weights(
                team, region, app, domain,
                original_service, new_service,
                original_weight, new_weight
            )

            logger.info("[GrayRelease] Successfully completed setup_domain_weights")

            return {
                "original_service_id": original_service.service_id,
                "original_service_cname": original_service.service_cname,
                "original_weight": original_weight,
                "new_service_id": new_service.service_id,
                "new_service_cname": new_service.service_cname,
                "new_weight": new_weight
            }

        except ServiceHandleException:
            raise
        except Exception as e:
            import traceback
            stack_trace = traceback.format_exc()
            logger.error("[GrayRelease] Failed to setup domain weights: {0}".format(stack_trace))
            logger.error("[GrayRelease] Context: app_id={0}, domain_name={1}, gray_ratio={2}".format(
                app.ID, domain_name, gray_ratio))
            raise ServiceHandleException(
                msg="failed to setup domain weights: {0}".format(str(e)),
                msg_show="设置域名权重失败: {0}".format(str(e)),
                status_code=500
            )

    def start_new_services(self, team, region_name, app, user, service_ids):
        """Start newly installed services in app"""
        try:
            for service_id in service_ids:
                service = TenantServiceInfo.objects.filter(
                    tenant_id=team.tenant_id,
                    service_id=service_id
                ).first()
                if service:
                    self.app_manage.start(team, service, user, None)
                    logger.info("Started new service {0}".format(service.service_cname))

        except Exception as e:
            logger.error("Failed to start new services: {0}".format(traceback.format_exc()))
            # Don't raise exception here, just log it
            # The services will be started eventually

    @transaction.atomic
    def create_gray_release(self, team, region_name, user, app, template_id, domain_name, gray_ratio,
                           market_name=None, install_from_cloud=False):
        """
        Create a gray release for an application

        Args:
            team: Team object
            region_name: Region name
            user: User object
            app: Application object
            template_id: Application template ID
            domain_name: Domain name for gray release
            gray_ratio: Gray ratio (0-100)
            market_name: Market name (optional, required if install_from_cloud is True)
            install_from_cloud: Whether to install from cloud market

        Returns:
            dict: Gray release information
        """
        try:
            # Validate gray ratio
            self.validate_gray_ratio(gray_ratio)

            # Step 1: Validate app
            logger.info("Validating app {0}".format(app.group_name))
            self.validate_app(team, region_name, app)

            # Get existing service IDs before installation
            existing_services = group_service.get_group_services(app.ID)
            existing_service_ids = set(s.service_id for s in existing_services)

            # Step 2: Install template to the app
            logger.info("Installing template {0} to app".format(template_id))
            self.install_template_to_app(
                team, region_name, user, app,
                template_id, market_name, install_from_cloud
            )

            # Get newly installed service IDs
            all_services = group_service.get_group_services(app.ID)
            new_service_ids = [s.service_id for s in all_services if s.service_id not in existing_service_ids]

            logger.info(f"[GrayRelease] Installed {len(new_service_ids)} new services")

            # Step 2.5: Delete domains created for new services (since skip_create_domain doesn't always work)
            logger.info("[GrayRelease] Checking and deleting auto-created domains for new services")
            self._delete_new_service_domains(team, region_name, new_service_ids)

            # Step 3: Setup domain weights
            logger.info("Setting up domain weights for gray release")

            # Get region object from region_name
            from console.repositories.region_repo import region_repo
            region = region_repo.get_region_by_region_name(region_name)
            if not region:
                raise ServiceHandleException(
                    msg="region not found",
                    msg_show="数据中心不存在",
                    status_code=404
                )

            weight_info = self.setup_domain_weights(
                team, region, app,
                domain_name, gray_ratio
            )

            # Step 4: Start newly installed services
            logger.info("Starting newly installed services")
            self.start_new_services(team, region_name, app, user, new_service_ids)

            # Step 5: Create gray release record
            logger.info("Creating gray release record")
            original_service = TenantServiceInfo.objects.filter(
                tenant_id=team.tenant_id,
                service_id=weight_info["original_service_id"]
            ).first()
            gray_service = TenantServiceInfo.objects.filter(
                tenant_id=team.tenant_id,
                service_id=weight_info["new_service_id"]
            ).first()

            # Get upgrade_group_id for both services
            original_group_id = original_service.tenant_service_group_id if original_service else None
            gray_group_id = gray_service.tenant_service_group_id if gray_service else None

            # Build service mappings: collect all services from both groups and match by service_cname
            logger.info("Building service mappings between original and gray groups")
            original_group_services = group_service.get_group_services(original_group_id)
            gray_group_services = group_service.get_group_services(gray_group_id)

            # Create a map of service_cname to service for both groups
            original_services_map = {}
            for svc in original_group_services:
                svc_obj = TenantServiceInfo.objects.filter(
                    tenant_id=team.tenant_id,
                    service_id=svc.service_id
                ).first()
                if svc_obj:
                    original_services_map[svc_obj.service_cname] = {
                        'service_id': svc_obj.service_id,
                        'service_cname': svc_obj.service_cname,
                        'service_alias': svc_obj.service_alias
                    }

            gray_services_map = {}
            for svc in gray_group_services:
                svc_obj = TenantServiceInfo.objects.filter(
                    tenant_id=team.tenant_id,
                    service_id=svc.service_id
                ).first()
                if svc_obj:
                    gray_services_map[svc_obj.service_cname] = {
                        'service_id': svc_obj.service_id,
                        'service_cname': svc_obj.service_cname,
                        'service_alias': svc_obj.service_alias
                    }

            # Match services by service_cname
            service_mappings = []
            for service_cname, original_svc in original_services_map.items():
                if service_cname in gray_services_map:
                    gray_svc = gray_services_map[service_cname]
                    service_mappings.append({
                        'original_service_id': original_svc['service_id'],
                        'original_service_cname': original_svc['service_cname'],
                        'original_service_alias': original_svc['service_alias'],
                        'gray_service_id': gray_svc['service_id'],
                        'gray_service_cname': gray_svc['service_cname'],
                        'gray_service_alias': gray_svc['service_alias']
                    })
                    logger.info(f"Service mapping: {original_svc['service_cname']} -> "
                               f"original={original_svc['service_id']}, gray={gray_svc['service_id']}")

            import json
            service_mappings_json = json.dumps(service_mappings)

            # Get template info from market_app_service
            template_version = None
            template_name = None
            try:
                from console.repositories.app import service_source_repo
                source = service_source_repo.get_service_source(
                    team.tenant_id,
                    gray_service.service_id
                )
                if source:
                    template_version = source.version
                    # Get template name from rainbond_app
                    from console.repositories.market_app_repo import rainbond_app_repo
                    app_model, _ = rainbond_app_repo.get_rainbond_app_and_version(
                        team.enterprise_id, template_id, template_version
                    )
                    if app_model:
                        template_name = app_model.app_name
            except Exception as e:
                logger.warning(f"Failed to get template info: {e}")
                template_version = "unknown"
                template_name = "unknown"

            gray_release_record = gray_release_repo.create(
                tenant_id=team.tenant_id,
                region_name=region_name,
                app_id=app.ID,
                app_name=app.group_name,
                template_id=template_id,
                template_name=template_name or "unknown",
                template_version=template_version or "unknown",
                original_upgrade_group_id=original_group_id,
                gray_upgrade_group_id=gray_group_id,
                original_service_id=weight_info["original_service_id"],
                original_service_cname=weight_info["original_service_cname"],
                gray_service_id=weight_info["new_service_id"],
                gray_service_cname=weight_info["new_service_cname"],
                service_mappings=service_mappings_json,
                domain_name=domain_name,
                gray_ratio=gray_ratio,
                status=GrayReleaseStatus.ACTIVE
            )

            logger.info(f"Gray release record created: ID={gray_release_record.ID}, "
                       f"service_mappings count={len(service_mappings)}")

            return {
                "app_id": app.ID,
                "app_name": app.group_name,
                "original_service_id": weight_info["original_service_id"],
                "original_service_cname": weight_info["original_service_cname"],
                "original_weight": weight_info["original_weight"],
                "new_service_id": weight_info["new_service_id"],
                "new_service_cname": weight_info["new_service_cname"],
                "new_weight": weight_info["new_weight"],
                "domain_name": domain_name,
                "gray_ratio": gray_ratio,
                "gray_release_record_id": gray_release_record.ID
            }

        except ServiceHandleException:
            raise
        except Exception as e:
            logger.error("Failed to create gray release: {0}".format(traceback.format_exc()))
            raise ServiceHandleException(
                msg="failed to create gray release: {0}".format(str(e)),
                msg_show="创建灰度发布失败",
                status_code=500
            )

    def update_gray_ratio_by_record(self, team, region_name, user, app, record, new_gray_ratio, is_full_release=False):
        """
        Update gray ratio using gray release record

        Args:
            team: Team object
            region_name: Region name
            user: User object
            app: Application object
            record: GrayReleaseRecord object
            new_gray_ratio: New gray ratio (0-100)
            is_full_release: Whether this is a full release (gray_ratio=100)

        Returns:
            dict: Updated gray release information
        """
        try:
            # Validate gray ratio
            self.validate_gray_ratio(new_gray_ratio)

            # Get services from record
            original_service = TenantServiceInfo.objects.filter(
                tenant_id=team.tenant_id,
                service_id=record.original_service_id
            ).first()

            new_service = TenantServiceInfo.objects.filter(
                tenant_id=team.tenant_id,
                service_id=record.gray_service_id
            ).first()

            if not original_service or not new_service:
                raise ServiceHandleException(
                    msg="services not found in record",
                    msg_show="灰度发布记录中的服务不存在",
                    status_code=404
                )

            # Calculate new weights
            original_weight = 100 - new_gray_ratio
            new_weight = new_gray_ratio

            logger.info(f"Updating gray ratio via record: original={original_weight}%, new={new_weight}%")

            if is_full_release:
                logger.info(f"[GrayRelease] Full release detected, will only use new backend")

            # Get region object first
            from console.repositories.region_repo import region_repo
            region = region_repo.get_region_by_region_name(region_name)
            if not region:
                raise ServiceHandleException(
                    msg="region not found",
                    msg_show="数据中心不存在",
                    status_code=404
                )

            # Get domain configuration from API Gateway
            # Domain configuration is not stored in database, need to get from API Gateway
            domain = self.get_domain_by_name(team, region, app.ID, record.domain_name)

            logger.info(f"[GrayRelease] Got domain configuration: {domain.get('name')}")

            # Update ApisixRoute weights
            self._update_apisix_route_weights(
                team, region, app, domain,
                original_service, new_service,
                original_weight, new_weight,
                is_full_release=is_full_release
            )

            # Update record
            gray_release_repo.update_gray_ratio(record, new_gray_ratio)

            return {
                "app_id": app.ID,
                "app_name": app.group_name,
                "original_service_id": original_service.service_id,
                "original_service_cname": original_service.service_cname,
                "original_weight": original_weight,
                "new_service_id": new_service.service_id,
                "new_service_cname": new_service.service_cname,
                "new_weight": new_weight,
                "domain_name": record.domain_name,
                "gray_ratio": new_gray_ratio,
                "original_deleted": is_full_release and new_gray_ratio == 100
            }

        except ServiceHandleException:
            raise
        except Exception as e:
            logger.error("Failed to update gray ratio: {0}".format(traceback.format_exc()))
            raise ServiceHandleException(
                msg="failed to update gray ratio: {0}".format(str(e)),
                msg_show="更新灰度比例失败",
                status_code=500
            )

    def update_gray_ratio(self, team, region_name, user, app, domain_name, gray_ratio):
        """
        Update gray ratio for an existing gray release

        Args:
            team: Team object
            region_name: Region name
            user: User object
            app: Application object
            domain_name: Domain name for traffic splitting
            gray_ratio: New gray ratio (0-100)

        Returns:
            dict: Updated gray release information
        """
        try:
            # Validate gray ratio
            self.validate_gray_ratio(gray_ratio)

            # Get all domains with this domain name for the app
            domains = ServiceDomain.objects.filter(
                domain_name=domain_name,
                tenant_id=team.tenant_id
            )

            # Get all services in the app
            app_services = group_service.get_group_services(app.ID)
            app_service_ids = [s.service_id for s in app_services]

            # Filter domains belonging to this app
            app_domains = [d for d in domains if d.service_id in app_service_ids]

            if len(app_domains) < 2:
                raise ServiceHandleException(
                    msg="need at least 2 services with the same domain for gray release",
                    msg_show="灰度发布需要至少2个服务绑定同一域名",
                    status_code=400
                )

            # Find the two services with the same service_cname (original and new version)
            service_cname_map = {}
            for domain in app_domains:
                service = TenantServiceInfo.objects.filter(
                    tenant_id=team.tenant_id,
                    service_id=domain.service_id
                ).first()
                if service:
                    if service.service_cname not in service_cname_map:
                        service_cname_map[service.service_cname] = []
                    service_cname_map[service.service_cname].append((service, domain))

            # Find the service_cname that has exactly 2 services (original and new)
            gray_service_pair = None
            for service_cname, pair in service_cname_map.items():
                if len(pair) == 2:
                    gray_service_pair = pair
                    break

            if not gray_service_pair:
                raise ServiceHandleException(
                    msg="no gray release service pair found",
                    msg_show="未找到灰度发布服务对",
                    status_code=404
                )

            # Sort by create_time to determine original and new
            gray_service_pair.sort(key=lambda x: x[0].create_time)
            original_service, original_domain = gray_service_pair[0]
            new_service, new_domain = gray_service_pair[1]

            # Calculate new weights
            original_weight = 100 - gray_ratio
            new_weight = gray_ratio

            # Update domain weights in database
            original_domain.the_weight = original_weight
            original_domain.save()

            new_domain.the_weight = new_weight
            new_domain.save()

            logger.info("Updated weights: original={0}, new={1}".format(original_weight, new_weight))

            # Call region API to update APISIX routes
            try:
                # Prepare data for original service domain
                original_domain_data = {
                    "domain_name": original_domain.domain_name,
                    "container_port": original_domain.container_port,
                    "protocol": original_domain.protocol,
                    "certificate_id": original_domain.certificate_id,
                    "domain_type": original_domain.domain_type,
                    "the_weight": original_weight,
                    "http_rule_id": original_domain.http_rule_id,
                    "is_outer_service": original_domain.is_outer_service,
                    "auto_ssl": original_domain.auto_ssl,
                    "path_rewrite": original_domain.path_rewrite if hasattr(original_domain, 'path_rewrite') else False,
                    "rewrites": original_domain.rewrites if hasattr(original_domain, 'rewrites') else [],
                    "rule_extensions": original_domain.rule_extensions if original_domain.rule_extensions else [],
                }

                # Prepare data for new service domain
                new_domain_data = {
                    "domain_name": new_domain.domain_name,
                    "container_port": new_domain.container_port,
                    "protocol": new_domain.protocol,
                    "certificate_id": new_domain.certificate_id,
                    "domain_type": new_domain.domain_type,
                    "the_weight": new_weight,
                    "http_rule_id": new_domain.http_rule_id,
                    "is_outer_service": new_domain.is_outer_service,
                    "auto_ssl": new_domain.auto_ssl,
                    "path_rewrite": new_domain.path_rewrite if hasattr(new_domain, 'path_rewrite') else False,
                    "rewrites": new_domain.rewrites if hasattr(new_domain, 'rewrites') else [],
                    "rule_extensions": new_domain.rule_extensions if new_domain.rule_extensions else [],
                }

                # Update original service domain in region
                self.domain_service.bind_httpdomain(team, user, original_service, original_domain_data)

                # Update new service domain in region
                self.domain_service.bind_httpdomain(team, user, new_service, new_domain_data)

                logger.info("Successfully updated APISIX routes for domain {0}".format(domain_name))
            except Exception as e:
                logger.error("Failed to update APISIX routes: {0}".format(traceback.format_exc()))
                raise ServiceHandleException(
                    msg="failed to update APISIX routes: {0}".format(str(e)),
                    msg_show="更新APISIX路由失败",
                    status_code=500
                )

            # Update gray release record
            record = gray_release_repo.get_active_record_by_domain(
                team.tenant_id, app.ID, domain_name
            )
            if record:
                gray_release_repo.update_gray_ratio(record, gray_ratio)
                logger.info(f"Updated gray release record: ID={record.ID}, gray_ratio={gray_ratio}")
            else:
                logger.warning(f"Gray release record not found for domain {domain_name}")

            return {
                "app_id": app.ID,
                "app_name": app.group_name,
                "original_service_id": original_service.service_id,
                "original_service_cname": original_service.service_cname,
                "original_weight": original_weight,
                "new_service_id": new_service.service_id,
                "new_service_cname": new_service.service_cname,
                "new_weight": new_weight,
                "domain_name": domain_name,
                "gray_ratio": gray_ratio
            }

        except ServiceHandleException:
            raise
        except Exception as e:
            logger.error("Failed to update gray ratio: {0}".format(traceback.format_exc()))
            raise ServiceHandleException(
                msg="failed to update gray ratio: {0}".format(str(e)),
                msg_show="更新灰度比例失败",
                status_code=500
            )


gray_release_service = GrayReleaseService()
