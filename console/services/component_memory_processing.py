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
        logger.info(f"开始获取企业 {enterprise_id} 的集群信息")
        try:
            regions = region_services.get_enterprise_regions(enterprise_id, level="safe")
            logger.info(f"成功获取到 {len(regions) if regions else 0} 个集群")
            
            for region in regions:
                region_data = self.monitor_handle(0, [region["region_name"], region["region_alias"]], region["region_id"], 0, "nil", "nil")
                self.region_list.append(region_data)
                
            logger.info(f"集群信息获取完成，共 {len(self.region_list)} 个集群")
        except Exception as e:
            logger.error(f"获取集群信息失败: {e}")
            raise

    def tenant_obtain_handle(self, enterprise_id):
        """
        获取企业下的所有租户信息
        """
        logger.info(f"开始获取企业 {enterprise_id} 的租户信息")
        try:
            tenants = Tenants.objects.filter(enterprise_id=enterprise_id).all()
            logger.info(f"查询到 {len(tenants)} 个租户")
            
            for tenant in tenants:
                tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id).all()
                
                for tenant_region in tenant_regions:
                    region_name = tenant_region.region_name
                    tenant_data = self.monitor_handle(1, [tenant.tenant_name, tenant.tenant_alias], tenant.tenant_id, 0, region_name, tenant.tenant_name)
                    self.tenant_list.append(tenant_data)
                    
            logger.info(f"租户信息获取完成，共 {len(self.tenant_list)} 个租户区域关系")
        except Exception as e:
            logger.error(f"获取租户信息失败: {e}")
            raise

    def component_memory_obtain_handle(self, enterprise_id):
        """
        获取组件内存使用信息
        """
        logger.info(f"开始获取企业 {enterprise_id} 的组件内存使用信息")
        total_components_processed = 0
        successful_components = 0
        
        for tenant in self.tenant_list:
            tenant_id = tenant["resource_id"]
            region_name = tenant["resource_parent"]
            tenant_name = tenant["resource_name"][0] if isinstance(tenant["resource_name"], list) else tenant["resource_name"]
            
            logger.info(f"处理租户 {tenant_name} 在区域 {region_name} 的组件")
            
            # 获取该租户在该区域的所有组件
            components = TenantServiceInfo.objects.filter(
                tenant_id=tenant_id,
                service_region=region_name
            ).exclude(service_source="market").all()
            
            logger.info(f"租户 {tenant_name} 在区域 {region_name} 有 {len(components)} 个组件")
            
            for component in components:
                total_components_processed += 1
                
                try:
                    # 通过API获取组件的内存使用情况
                    body = region_api.get_service_pods(region_name, tenant["resource_namespace"], component.service_alias, enterprise_id)
                    
                    if not body:
                        logger.warning(f"组件 {component.service_alias} 返回空响应")
                        continue
                        
                    if "bean" not in body or not body["bean"]:
                        logger.warning(f"组件 {component.service_alias} 响应中缺少 'bean' 字段或为空")
                        continue
                        
                    bean_data = body["bean"]
                    
                    # 获取新旧Pod数据
                    all_pods = []
                    if "new_pods" in bean_data and bean_data["new_pods"]:
                        all_pods.extend(bean_data["new_pods"])
                    if "old_pods" in bean_data and bean_data["old_pods"]:
                        all_pods.extend(bean_data["old_pods"])
                    
                    if not all_pods:
                        continue
                        
                    total_memory = 0
                    
                    for i, pod in enumerate(all_pods):
                        # 从pod信息中提取内存使用量
                        containers = pod.get("container", {})
                        
                        for container_name, container_info in containers.items():
                            if container_name == "POD":  # 跳过POD容器
                                continue
                                
                            memory_usage = container_info.get("memory_usage", 0)
                            
                            # 内存单位通常是字节，需要转换
                            if isinstance(memory_usage, (int, float)) and memory_usage > 0:
                                # 转换为MB
                                memory_mb = float(memory_usage) / 1024 / 1024
                                total_memory += memory_mb
                            elif isinstance(memory_usage, str) and memory_usage.replace('.', '').isdigit():
                                memory_mb = float(memory_usage) / 1024 / 1024
                                total_memory += memory_mb
                    
                    # 只有内存使用量大于0的组件才加入桑吉图
                    if total_memory > 0:
                        component_data = self.monitor_handle(
                            2, 
                            component.service_cname or component.service_alias, 
                            component.service_id, 
                            total_memory,
                            [tenant["resource_id"], tenant["resource_name"], tenant["resource_parent"]],
                            tenant["resource_namespace"]
                        )
                        self.component_list.append(component_data)
                        successful_components += 1
                        logger.info(f"成功添加组件: {component.service_cname or component.service_alias}, 内存: {total_memory:.2f} MB")
                        
                except Exception as e:
                    logger.warning(f"获取组件 {component.service_alias} 内存信息失败: {e}")
                    continue
        
        logger.info(f"组件内存信息获取完成，共处理 {total_components_processed} 个组件，成功获取 {successful_components} 个组件的内存信息")

    def template_handle(self):
        """
        按照指定格式对数据进行排序并返回给前端
        """
        logger.info(f"开始处理模板数据，当前有 {len(self.component_list)} 个组件")
        
        # 按内存使用量降序排序
        self.component_list = sorted(self.component_list, key=lambda x: x["resource_memory"], reverse=True)
        
        # 限制返回结果数量
        original_count = len(self.component_list)
        if len(self.component_list) > 30:
            self.component_list = self.component_list[:30]
            logger.info(f"限制返回结果数量：从 {original_count} 个减少到 30 个")
            
        nodes = []
        links = []
        
        # 用于存储组件到租户和租户到区域的关系及内存值
        component_tenant_relations = {}
        tenant_region_relations = {}
        
        # 遍历组件列表，构建节点和链接数据
        for i, component in enumerate(self.component_list):
            # 从组件数据中提取信息
            component_name = component["resource_name"]
            component_memory = component["resource_memory"]
            tenant_id = component["resource_parent"][0]
            tenant_name_list = component["resource_parent"][1]
            region_name = component["resource_parent"][2]
            
            # 处理租户名称（可能是列表格式）
            if isinstance(tenant_name_list, list):
                tenant_name = tenant_name_list[0]  # 取实际的租户名称
                tenant_alias = tenant_name_list[1] if len(tenant_name_list) > 1 else tenant_name
            else:
                tenant_name = tenant_name_list
                tenant_alias = tenant_name_list
            
            # 添加组件节点
            nodes.append({"id": component_name, "level": 0})
            
            # 添加租户和区域节点（使用别名作为显示名称）
            nodes.append({"id": tenant_alias, "level": 1})
            nodes.append({"id": region_name, "level": 2})
            
            # 添加组件到租户的链接
            links.append({"source": component_name, "target": tenant_alias, "value": component_memory})
            
            # 累计租户的内存使用量（使用tenant_alias作为键）
            if tenant_alias in tenant_region_relations:
                tenant_region_relations[tenant_alias] = (tenant_region_relations[tenant_alias][0], 
                                                      tenant_region_relations[tenant_alias][1] + component_memory)
            else:
                tenant_region_relations[tenant_alias] = (region_name, component_memory)

        # 删除重复节点
        nodes = list({node["id"]: node for node in nodes}.values())
        
        # 添加租户到区域的链接
        for tenant_alias, (region_name, total_memory) in tenant_region_relations.items():
            links.append({"source": tenant_alias, "target": region_name, "value": total_memory})
            
        logger.info(f"模板数据处理完成，返回 {len(nodes)} 个节点和 {len(links)} 个链接")
        return nodes, links 