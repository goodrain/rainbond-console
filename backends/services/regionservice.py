# -*- coding: utf8 -*-

import datetime
import json
import logging

from backends.models.main import RegionClusterInfo, RegionConfig
from backends.services.httpclient import HttpInvokeApi
from backends.services.tenantservice import tenant_service
from www.apiclient.regionapi import RegionInvokeApi
from www.models.main import TenantServiceInfo, Tenants, TenantRegionInfo
from www.utils.crypt import make_uuid
from backends.services.exceptions import *
from django.db.models import Sum, F
from backends.services.configservice import config_service

region_api = RegionInvokeApi()
logger = logging.getLogger('default')
http_client = HttpInvokeApi()


class RegionService(object):
    def get_all_regions(self, get_enabled=False):
        if get_enabled:
            region_list = RegionConfig.objects.filter(status="1").order_by("ID")
        else:
            region_list = RegionConfig.objects.all().order_by("ID")
        return list(region_list)

    def get_tenant_resources(self, tenant_name, region_id, page_num, page_size):
        list = []
        total = 0
        if tenant_name:
            try:
                tenant = Tenants.objects.get(tenant_name=tenant_name)
            except Tenants.DoesNotExist as e:
                raise TenantNotExistError("租户{}不存在".format(tenant_name))
            if region_id:
                region = RegionConfig.objects.get(region_id=region_id)
                tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id,
                                                                     region_name=region.region_name)
                if not tenant_region_list:
                    raise ParamsError("租户{0}在数据中心{1}没有记录".format(tenant_name, region.region_alias))
            else:
                all_regions = self.get_all_regions(True)
                regions = [region.region_name for region in all_regions]
                tenant_region_list = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id,
                                                                     region_name__in=regions)

            for tenant_region in tenant_region_list:
                try:
                    tenant = Tenants.objects.get(tenant_id=tenant_region.tenant_id)
                except Exception as e:
                    logger.exception("tenant {0} is not found".format(tenant_region.tenant_id))
                    continue
                tenant_services = None
                try:
                    tenant_services = TenantServiceInfo.objects.all().values("tenant_id").annotate(
                        memory=Sum(F('min_node') * F('min_memory')), cpu=Sum("min_cpu")).get(
                        service_region=tenant_region.region_name, tenant_id=tenant_region.tenant_id)
                except TenantServiceInfo.DoesNotExist as e:
                    pass

                statics = {}
                statics["tenant_id"] = tenant.tenant_id
                statics["tenant_name"] = tenant.tenant_name
                if tenant_services:
                    statics["allocate_memory"] = tenant_services["memory"]
                else:
                    statics["allocate_memory"] = 0
                statics["total_memory"] = 0
                statics["region_name"] = tenant_region.region_name
                region_config_list = RegionConfig.objects.filter(region_name=tenant_region.region_name)
                if region_config_list:
                    region_name = region_config_list[0].region_alias
                    statics["region_alias"] = region_name
                else:
                    statics["region_alias"] = tenant_region.region_name

                tenant_region_map = tenant_service.get_tenant_region(tenant_region.tenant_id, tenant_region.region_name)
                statics.update(tenant_region_map)

                list.append(statics)
            return total, list
        else:
            start = page_size * (page_num - 1)
            end = page_size * page_num
            if region_id:
                region = RegionConfig.objects.get(region_id=region_id)
                enable_regions = [region.region_name]
                total, tenant_services = tenant_service.get_tenant_service(enable_regions, start, end)
            else:
                all_regions = self.get_all_regions(True)
                enable_regions = [r.region_name for r in all_regions]
                total, tenant_services = tenant_service.get_tenant_service(enable_regions, start, end)

            tenant_id_list = [ts["tenant_id"] for ts in tenant_services]
            tenants = Tenants.objects.filter(tenant_id__in=tenant_id_list)
            tenant_id_map = {tenant.tenant_id: tenant.tenant_name for tenant in tenants}
            for service in tenant_services:
                statics = {}
                region = service["service_region"]
                statics["tenant_name"] = tenant_id_map.get(service["tenant_id"])
                statics["tenant_id"] = service["tenant_id"]
                statics["allocate_memory"] = service["memory"]
                statics["total_memory"] = 0
                statics["region_name"] = region
                region_config_list = RegionConfig.objects.filter(region_name=region)
                if region_config_list:
                    region_name = region_config_list[0].region_alias
                    statics["region_alias"] = region_name
                else:
                    statics["region_alias"] = region
                tenant_region_map = tenant_service.get_tenant_region(service["tenant_id"], region)
                statics.update(tenant_region_map)
                list.append(statics)

            return total, list

    def add_region_cluster(self, region_id, cluster_id, cluster_name, cluster_alias, enable):
        if RegionClusterInfo.objects.filter(cluster_alias=cluster_alias).exists():
            raise ClusterExistError("集群别名{}已存在".format(cluster_alias))
        if RegionClusterInfo.objects.filter(cluster_name=cluster_name).exists():
            raise ClusterExistError("集群名{}已存在".format(cluster_name))
        create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cluster_info = RegionClusterInfo.objects.create(region_id=region_id,
                                                        cluster_id=cluster_id,
                                                        cluster_name=cluster_name,
                                                        cluster_alias=cluster_alias,
                                                        enable=enable,
                                                        create_time=create_time)
        return cluster_info

    def update_region_cluster(self, cluster_id, cluster_name, cluster_alias, enable):
        if not RegionClusterInfo.objects.filter(ID=cluster_id):
            raise ClusterNotExistError("集群不存在")
        cluster_config = RegionClusterInfo.objects.get(ID=cluster_id)
        cluster_config.cluster_name = cluster_name
        cluster_config.cluster_alias = cluster_alias
        cluster_config.enable = enable
        cluster_config.save()

    def add_region(self, region_id, region_name, region_alias, url, token, wsurl, httpdomain,
                                      tcpdomain, desc, scope):

        if not wsurl:
            return False, "数据中心websocket地址不能为空", None
        if not httpdomain:
            return False, "数据中心http应用访问根域名不能为空", None
        if not tcpdomain:
            return False, "数据中心tcp应用访问根域名不能为空", None
        if not scope:
            return False, "数据中心类型不能为空", None

        if RegionConfig.objects.filter(region_name=region_name).exists():
            return False, "数据中心名{}在云帮已存在".format(region_name), None
        if RegionConfig.objects.filter(region_alias=region_alias).exists():
            return False, "数据中心别名{}在云帮已存在".format(region_alias), None
        try:
            res, body = region_api.get_api_version(url, token, region_name)
            status = int(res.status)
            if status != 200:
                return False, "该数据中心云帮{0}无法访问".format(region_name), None
        except Exception as e:
            logger.exception(e)
            return False, "该数据中心云帮{0}无法访问".format(region_name), None

        create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        region_config = RegionConfig(region_id=region_id,
                                     region_name=region_name,
                                     region_alias=region_alias,
                                     wsurl=wsurl,
                                     httpdomain=httpdomain,
                                     tcpdomain=tcpdomain,
                                     desc=desc,
                                     scope=scope,
                                     url=url,
                                     create_time=create_time,
                                     status='2',
                                     token=token)
        region_config.save()
        return True, "数据中心添加成功",region_config

    def update_region(self, region_id, **kwargs):

        wsurl = kwargs.get("wsurl", None)
        httpdomain = kwargs.get("httpdomain", None)
        tcpdomain = kwargs.get("tcpdomain", None)
        scope = kwargs.get("scope", None)

        if wsurl is not None and wsurl == '':
            return False, u"数据中心websocket地址不能为空"
        if httpdomain is not None and httpdomain == '':
            return False, u"数据中心http应用访问根域名不能为空"
        if tcpdomain is not None and tcpdomain == '':
            return False, u"数据中心tcp应用访问根域名不能为空"
        if scope is not None and scope == '':
            return False, u"数据中心类型不能为空"

        if not RegionConfig.objects.filter(region_id=region_id).exists():
            return False, u"需要修改的数据中心在云帮不存在"
        region_config = RegionConfig.objects.get(region_id=region_id)
        region_name = kwargs.get("region_name", None)
        if region_name:
            kwargs.pop("region_name")
        region_alias = kwargs.get("region_alias", None)
        if region_alias:
            if RegionConfig.objects.filter(region_alias=region_alias).exclude(
                    region_id=region_config.region_id).exists():
                return False, u"数据中心别名{0}在云帮已存在".format(region_alias)

        for k, v in kwargs.items():
            setattr(region_config, k, v)
        region_config.save(update_fields=kwargs.keys())
        self.update_region_config()
        return True, "success"

    def region_status_mange(self, region_id, action):
        if not RegionConfig.objects.filter(region_id=region_id).exists():
            raise RegionNotExistError("数据中心不存在")
        region_config = RegionConfig.objects.get(region_id=region_id)
        if action == "online":
            res, body = region_api.get_api_version(region_config.url, region_config.token, region_config.region_name)
            logger.debug("body msg: {}".format(body))
            status = int(res.status)
            if status != 200:
                raise RegionUnreachableError("数据中心{0}不可达,无法上线".format(region_config.region_name))
            region_config.status = '1'
            region_config.save()
        elif action == "offline":
            region_config.status = '2'
            region_config.save()
        elif action == "maintain":
            region_config.status = '3'
            region_config.save()
        elif action == "cancel_maintain":
            region_config.status = '1'
            region_config.save()

        self.update_region_config()

        return region_config

    def get_region(self, region_id):
        if not RegionConfig.objects.filter(region_id=region_id).exists():
            raise RegionNotExistError("数据中心不存在")
        region_config = RegionConfig.objects.get(region_id=region_id)
        return region_config

    def get_all_region_resource(self, region_list):
        region_resource_list = []
        for region in region_list:

            region_tenant_num = TenantRegionInfo.objects.filter(region_name=region.region_name).count()
            region_resource = {}
            region_resource["region_id"] = region.region_id
            region_resource["region_alias"] = region.region_alias
            region_resource["region_name"] = region.region_name
            region_resource["status"] = region.status
            # 初始化数据
            region_resource["total_memory"] = 0
            region_resource["left_memory"] = 0
            region_resource["disk"] = 0
            region_resource["net"] = 0
            clusters = self.get_region_clusters(region.region_id)
            cluster_num = len(clusters)
            region_resource["cluster_num"] = cluster_num
            region_resource["tenant_num"] = region_tenant_num
            region_resource["node_num"] = 0
            # 如果数据中心在线
            if region.status == '1':
                try:
                    resource = self.get_region_resource(region)
                    region_resource.update(resource)
                    result = http_client.get_region_resources()
                    resource_bean = result["bean"]
                    # 已用内存 单位 G
                    used_memory = round(resource_bean.get("mem", 0) / 1024.0, 2)
                    used_cpu = resource_bean.get("cpu", 0)
                    region_resource["left_memory"] = region_resource["total_memory"] - used_memory
                    region_resource["used_cpu"] = used_cpu
                    region_resource["left_cpu"] = region_resource["total_cpu"] - used_cpu
                except http_client.CallApiError as e:
                    logger.exception("get region {0} error !".format(region.region_alias))
                    region_resource["ok"] = "failure"
                except Exception as e:
                    logger.exception(e)
                    region_resource["ok"] = "failure"

            region_resource_list.append(region_resource)
        return region_resource_list

    def get_region_resource(self, region):
        http_client.update_client(region)
        region_resource = {}
        region_resource["disk"] = 0
        region_resource["net"] = 0
        region_resource["node_num"] = 0

        total_memory = 0
        total_cpu = 0

        res, body = http_client.get_region_nodes(None)
        result = body["body"]
        node_list = result["list"]
        for node in node_list:
            # 只计算可调度的tree节点内存
            if node["role"] == "tree" and not node["unschedulable"]:
                total_memory += node["available_memory"]
                total_cpu += node["available_cpu"]
        region_resource["node_num"] = len(node_list)
        region_resource["total_memory"] = total_memory
        region_resource["total_cpu"] = total_cpu * 1000
        region_resource["left_memory"] = 0
        return region_resource

    def get_region_clusters(self, region_id):
        cluster_list = RegionClusterInfo.objects.filter(region_id=region_id)
        return list(cluster_list)

    def get_region_clusters_resources(self, region_id):
        cluster_list = self.get_region_clusters(region_id)
        resource_list = []
        for cluster in cluster_list:

            # TODO 集群目前和数据中心一致
            resource = {}
            region = RegionConfig.objects.get(region_id=region_id)
            try:
                resource = self.get_region_resource(region)
                resource["status"] = "success"
            except Exception as e:
                logger.debug(e)
                resource["status"] = "failure"
                resource["node_num"] = 0

            resource["region_id"] = region_id
            resource["region_name"] = region.region_name
            resource["region_alias"] = region.region_alias
            resource["cluster_id"] = cluster.ID
            resource["cluster_name"] = cluster.cluster_name
            resource["cluster_alias"] = cluster.cluster_alias
            resource["enable"] = cluster.enable
            resource["disk"] = 0
            resource["net"] = 0

            resource_list.append(resource)
        return resource_list

    def get_real_region_tenant_resource(self, region, tenant_ids):

        statics_list = []
        tenant_name_list = Tenants.objects.filter(tenant_id__in=tenant_ids).values_list("tenant_name", flat=True)
        try:
            result = region_api.get_region_tenants_resources(region, {"tenant_name": list(tenant_name_list)})
            tenant_memory_map = result.get("list")
            if tenant_memory_map:
                for res in tenant_memory_map:
                    statics = {}
                    statics.update(res)
                    statics["region_name"] = region
                    statics_list.append(statics)
        except Exception as e:
            logger.exception(e)
        return statics_list

    def generate_region_config(self):
        # 查询已上线的数据中心配置
        region_config_list = []
        regions = RegionConfig.objects.filter(status='1')
        for region in regions:
            config_map = {}
            config_map["region_name"] = region.region_name
            config_map["region_alias"] = region.region_alias
            config_map["url"] = region.url
            config_map["token"] = region.token
            config_map["region_name"] = region.region_name
            config_map["enable"] = True
            region_config_list.append(config_map)
        json_data = json.dumps(region_config_list)
        return json_data

    def update_region_config(self):
        region_json_data = self.generate_region_config()
        if not config_service.get_config_by_key("REGION_SERVICE_API"):
            config_service.add_config("REGION_SERVICE_API", region_json_data, 'json', "数据中心配置")
        else:
            config_service.update_config("REGION_SERVICE_API", region_json_data)

    def delete_region_by_region_id(self, region_id):
        RegionConfig.objects.filter(region_id=region_id).delete()
        RegionClusterInfo.objects.filter(region_id=region_id).delete()

region_service = RegionService()
