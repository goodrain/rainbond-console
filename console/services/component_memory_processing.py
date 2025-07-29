"""
该文件主要用于openapi调用，返回组件内存桑吉图数据，展示组件内存使用情况的层级关系。
"""
import logging
from functools import reduce

from console.repositories.app import service_repo
from console.services.region_services import region_services
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantRegionInfo, Tenants, ServiceGroup, TenantServiceInfo

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class Component_memory_processing(object):
    def __init__(self):
        self.region_list = list()
        self.tenant_list = list()
        self.component_list = list()

    def monitor_handle(self, *args):
        """
        构建组件内存监控数据结构
        
        参数:
        resource_type ：args[0] 资源类型级别
        resource_name ：args[1] 资源名称
        resource_id ：args[2] 资源唯一标识
        resource_memory ： args[3] 内存使用量
        resource_parent ： args[4] 资源的父级
        resource_namespace ： args[5] 资源的命名空间
        """
        return {
            "resource_type": args[0],
            "resource_name": args[1],
            "resource_id": args[2],
            "resource_memory": args[3],
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
                self.monitor_handle(0, [region["region_name"], region["region_alias"]], region["region_id"], 0, "nil", "nil"))

    def tenant_obtain_handle(self, enterprise_id):
        """
        获取企业下的所有租户信息
        """
        tenants = Tenants.objects.filter(enterprise_id=enterprise_id).all()
        for tenant in tenants:
            tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id).all()
            for tenant_region in tenant_regions:
                region_name = tenant_region.region_name
                self.tenant_list.append(
                    self.monitor_handle(1, [tenant.tenant_name, tenant.tenant_alias], tenant.tenant_id, 0, region_name, tenant.tenant_name))

    def component_memory_obtain_handle(self, enterprise_id):
        """
        获取组件内存使用信息
        """
        for tenant in self.tenant_list:
            tenant_id = tenant["resource_id"]
            region_name = tenant["resource_parent"]
            
            # 获取该租户在该区域的所有组件
            components = TenantServiceInfo.objects.filter(
                tenant_id=tenant_id,
                service_region=region_name
            ).exclude(service_source="market").all()
            
            for component in components:
                try:
                    # 通过API获取组件的内存使用情况
                    res, body = region_api.get_service_pods(region_name, tenant["resource_namespace"], component.service_alias, enterprise_id)
                    
                    if not body or "list" not in body:
                        continue
                        
                    total_memory = 0
                    pods = body.get("list", [])
                    
                    for pod in pods:
                        # 从pod信息中提取内存使用量
                        containers = pod.get("containers", [])
                        for container in containers:
                            memory_usage = container.get("memory", 0)
                            if isinstance(memory_usage, (int, float)):
                                total_memory += memory_usage
                            elif isinstance(memory_usage, str) and memory_usage.isdigit():
                                total_memory += int(memory_usage)
                    
                    # 只有内存使用量大于0的组件才加入桑吉图
                    if total_memory > 0:
                        self.component_list.append(
                            self.monitor_handle(
                                2, 
                                component.service_cname or component.service_alias, 
                                component.service_id, 
                                total_memory,
                                [tenant["resource_id"], tenant["resource_name"], tenant["resource_parent"]],
                                tenant["resource_namespace"]
                            )
                        )
                        
                except Exception as e:
                    logger.warning(f"获取组件 {component.service_alias} 内存信息失败: {e}")
                    continue

    def template_handle(self):
        """
        按照指定格式对数据进行排序并返回给前端
        """
        # 按内存使用量降序排序
        self.component_list = sorted(self.component_list, key=lambda x: x["resource_memory"], reverse=True)
        
        # 限制返回结果数量
        if len(self.component_list) > 30:
            self.component_list = self.component_list[:30]
            
        nodes = []
        links = []
        
        # 用于存储组件到租户和租户到区域的关系及内存值
        component_tenant_relations = {}
        tenant_region_relations = {}
        
        # 遍历组件列表，构建节点和链接数据
        for component in self.component_list:
            # 从组件数据中提取信息
            component_name = component["resource_name"]
            component_memory = component["resource_memory"]
            tenant_id = component["resource_parent"][0]
            tenant_name = component["resource_parent"][1]
            region_name = component["resource_parent"][2]
            
            # 添加组件节点
            nodes.append({"id": component_name, "level": 0})
            
            # 添加租户和区域节点
            nodes.append({"id": tenant_name, "level": 1})
            nodes.append({"id": region_name, "level": 2})
            
            # 添加组件到租户的链接
            links.append({"source": component_name, "target": tenant_name, "value": component_memory})
            
            # 累计租户的内存使用量
            if tenant_name in tenant_region_relations:
                tenant_region_relations[tenant_name] = (tenant_region_relations[tenant_name][0], 
                                                      tenant_region_relations[tenant_name][1] + component_memory)
            else:
                tenant_region_relations[tenant_name] = (region_name, component_memory)

        # 删除重复节点
        nodes = list({node["id"]: node for node in nodes}.values())
        
        # 添加租户到区域的链接
        for tenant_name, (region_name, total_memory) in tenant_region_relations.items():
            links.append({"source": tenant_name, "target": region_name, "value": total_memory})
            
        return nodes, links 