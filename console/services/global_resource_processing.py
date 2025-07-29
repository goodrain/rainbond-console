"""
该文件主要用于openapi调用，返回全局资源的之间的关系，资源信息概览，交由前端展示。
"""
import logging
from functools import reduce

from console.repositories.app import service_repo
from console.services.region_services import region_services
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantRegionInfo, Tenants, ServiceGroup, ServiceDomain, ServiceGroupRelation

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class Global_resource_processing(object):
    def __init__(self):
        self.region_list = list()
        self.tenant_list = list()
        self.app_dict = dict()
        self.host_list = list()

    def monitor_handle(self, *args):
        """
        构建资源监控数据结构
        
        参数:
        resource_type ：args[0] 资源类型级别
        resource_name ：args[1] 资源名称
        resource_id ：args[2] 资源唯一标识
        resource_requests ： args[3] 资源请求数量
        resource_parent ： args[4] 资源的父级
        resource_namespace ： args[5] 资源的命名空间
        """
        return {
            "resource_type": args[0],
            "resource_name": args[1],
            "resource_id": args[2],
            "resource_requests": args[3],
            "resource_parent": args[4],
            "resource_namespace": args[5]
        }

    def region_obtain_handle(self, enterprise_id):
        """
        从数据库获取集群信息
        """
        regions = region_services.get_enterprise_regions(enterprise_id, level="safe")
        for region in regions:
            self.region_list.append(
                self.monitor_handle(0, [region["region_name"], region["region_alias"]], region["region_id"], 200, "nil", "nil"))

    def tenant_obtain_handle(self, enterprise_id):
        """
        从数据库获取团队信息及其对应的父级
        """
        tenants = TenantRegionInfo.objects.filter(enterprise_id=enterprise_id)
        for region in self.region_list:
            ent_tenants = tenants.filter(region_name=region["resource_name"][0])
            for ent_tenant in ent_tenants:
                t = Tenants.objects.filter(tenant_id=ent_tenant.tenant_id)
                if not t:
                    continue
                self.tenant_list.append(
                    self.monitor_handle(1, t[0].tenant_alias, ent_tenant.tenant_id, 200, region["resource_name"],
                                        t[0].namespace))

    def app_obtain_handle(self):
        """
        从数据库获取应用信息及其对应的父级
        """
        apps = ServiceGroup.objects.filter()
        for tenant in self.tenant_list:
            ten_apps = apps.filter(tenant_id=tenant["resource_id"])
            for ten_app in ten_apps:
                self.app_dict.update({
                    ten_app.ID:
                    self.monitor_handle(2, ten_app.group_name, ten_app.ID, 200, tenant["resource_id"],
                                        tenant["resource_namespace"])
                })

    def host_obtain_handle(self):
        """
        通过请求区域端的代理接口，获取APISIX网关信息和请求流量，并将网关绑定到其父应用
        """
        time_range = "1h"  # 查询最近1小时的数据
        
        for tenant in self.tenant_list:
            # APISIX HTTP状态码指标查询
            # route的命名规则是: 命名空间_组件名称_xxx
            query = (
                "?query=sort_desc(sum(ceil(increase("
                + "apisix_http_status%7Broute%3D~%22{0}_.*%22%7D%5B{1}%5D)))"
                + "%20by%20(route))"
            )
            
            suffix = query.format(tenant["resource_namespace"], time_range)
            
            try:
                # 调用区域API获取域访问数据
                res, body = region_api.get_query_domain_access(
                    tenant["resource_parent"][0], 
                    tenant["resource_name"], 
                    suffix
                )
                # 确保返回了有效数据
                if not body or "data" not in body or "result" not in body["data"]:
                    logger.warning(f"无法获取租户 {tenant['resource_name']} 的网关访问数据")
                    continue
                    
                domains = body["data"]["result"]

                for domain in domains:
                    # 提取路由名称和带宽使用量
                    route = domain["metric"].get("route", "")
                    if not route:
                        continue
                    domain_route = domain["metric"].get("matched_host", "")
                    # 从路由名称中提取组件信息
                    # 实际格式例如: "zqhh_gr1a56e3-5000-zs6bcf8j-14.103.232.255.ip.goodrain.netp-ps-s_a4d2683f"
                    # 其中zqhh是命名空间，gr1a56e3是组件别名
                    
                    # 首先按第一个下划线分割获取命名空间
                    parts = route.split("_", 1)
                    if len(parts) < 2:
                        logger.debug(f"路由名称格式不正确，无法提取命名空间: {route}")
                        continue
                    
                    namespace = parts[0]
                    rest = parts[1]
                    
                    # 然后从剩余部分提取组件别名（到第一个连字符为止）
                    service_alias_parts = rest.split("-", 1)
                    service_alias = service_alias_parts[0]  # 组件的service_alias

                    # 获取HTTP请求数量
                    request_count = domain["value"][1]
                    # 跳过零请求的路由
                    if not request_count or int(float(request_count)) == 0:
                        continue
                    
                    # 查找对应的租户
                    tenant_obj = None
                    for t in self.tenant_list:
                        if t["resource_namespace"] == namespace:
                            tenant_obj = t
                            break
                            
                    if not tenant_obj:
                        logger.debug(f"找不到命名空间 {namespace} 对应的租户")
                        continue
                    
                    service_info = service_repo.get_service_by_service_alias(service_alias)
                    if not service_info:
                        logger.debug(f"找不到组件 {service_alias} 对应的服务")
                        continue
                        
                    host_service_id = service_info.service_id

                    # 查找服务对应的应用组
                    service_relations = ServiceGroupRelation.objects.filter(service_id=host_service_id)
                    if not service_relations.exists():
                        logger.debug(f"找不到服务 {host_service_id} 对应的应用组")
                        continue
                    app_id = service_relations[0].group_id
                    
                    # 添加到主机列表
                    self.host_list.append(
                        self.monitor_handle(
                            3, 
                            domain_route,  # 使用路由名称作为资源名称
                            service_info.ID,  # 使用服务ID作为资源ID
                            int(float(request_count)),  # 使用HTTP请求数量作为资源请求量
                            [app_id, tenant_obj["resource_name"], tenant_obj["resource_parent"][1]],
                            tenant_obj["resource_namespace"]
                        )
                    )
                    
            except Exception as e:
                logger.error(f"获取租户 {tenant['resource_name']} 的网关访问数据失败: {str(e)}")

    def template_handle(self):
        """
        按照指定格式对数据进行排序并返回给前端
        """
        # 降序排序，显示请求量最多的域名
        self.host_list = sorted(self.host_list, key=lambda x: x["resource_requests"], reverse=True)
        
        # 限制返回结果数量
        if len(self.host_list) > 20:
            self.host_list = self.host_list[:20]
            
        nodes = []
        links = []
        
        # 用于存储应用到租户和租户到区域的关系及值
        app_tenant_relations = {}
        tenant_region_relations = {}
        
        # 遍历主机列表，构建节点和链接数据
        for host in self.host_list:
            # 从主机数据中提取信息
            this_tenant_name = host["resource_parent"][1]
            this_region_name = host["resource_parent"][2]
            host_requests = host["resource_requests"]
            
            # 添加主机节点
            nodes.append({"id": host["resource_name"], "level": 0})
            
            # 获取应用信息
            this_app = self.app_dict.get(host["resource_parent"][0])
            if not this_app:
                logger.warning(f"找不到应用ID: {host['resource_parent'][0]}")
                continue
                
            # 构建应用名称
            this_app_name = f"{this_app['resource_name']}({this_app['resource_id']})"
            
            # 添加应用、租户和区域节点
            nodes.append({"id": this_app_name, "level": 1})
            nodes.append({"id": this_tenant_name, "level": 2})
            nodes.append({"id": this_region_name, "level": 3})
            
            # 添加主机到应用的链接
            links.append({"source": host["resource_name"], "target": this_app_name, "value": host_requests})
            
            # 累计应用到租户的值
            app_tenant_key = (this_app_name, this_tenant_name)
            if app_tenant_key in app_tenant_relations:
                app_tenant_relations[app_tenant_key] += int(host_requests)
            else:
                app_tenant_relations[app_tenant_key] = int(host_requests)
            
            # 累计租户到区域的值
            tenant_region_key = (this_tenant_name, this_region_name)
            if tenant_region_key in tenant_region_relations:
                tenant_region_relations[tenant_region_key] += int(host_requests)
            else:
                tenant_region_relations[tenant_region_key] = int(host_requests)

        # 删除重复节点
        nodes = list({node["id"]: node for node in nodes}.values())
        
        # 添加应用到租户的链接
        for (app, tenant), value in app_tenant_relations.items():
            links.append({"source": app, "target": tenant, "value": value})
            
        # 添加租户到区域的链接
        for (tenant, region), value in tenant_region_relations.items():
            links.append({"source": tenant, "target": region, "value": value})
            
        return nodes, links
