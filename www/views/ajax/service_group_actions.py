# -*- coding: utf8 -*-

import logging

from django.conf import settings
from django.http import JsonResponse

from www.apiclient.regionapi import RegionInvokeApi
from www.models import ServiceGroupRelation, \
    TenantServiceInfo, \
    TenantServiceRelation, \
    ServiceGroup, TenantServicesPort, ServiceDomain
from www.views import AuthedView

logger = logging.getLogger('default')
region_api = RegionInvokeApi()


class TopologicalGraphView(AuthedView):

    def get(self, request, group_id, *args, **kwargs):
        """根据group的id获取group的详细信息"""
        # group_id = request.GET.get("group_id", None)
        result = {}
        logger.debug("query topological graph from:{0}".format(group_id))
        try:
            if group_id is None or not group_id.isdigit():
                result["status"] = 501
                result["msg"] = "group id is missing or not digit!"
                return JsonResponse(result, status=501)

            tenant_id = self.tenant.tenant_id
            group_count = ServiceGroup.objects.filter(tenant_id=tenant_id, ID=group_id).count()
            if group_count == 0:
                result["status"] = 502
                result["msg"] = "group is not yours!"
                return JsonResponse(result, status=502)

            # 根据group_id获取group下的信息
            service_group_relation_list = ServiceGroupRelation.objects.filter(group_id=group_id)
            service_id_list = [x.service_id for x in service_group_relation_list]
            # 查询服务依赖信息
            service_relation_list = TenantServiceRelation.objects.filter(service_id__in=service_id_list)
            dep_service_id_list = [x.dep_service_id for x in service_relation_list]

            # 查询服务、依赖服务信息
            all_service_id_list = list(set(dep_service_id_list).union(set(service_id_list)))
            service_list = TenantServiceInfo.objects.filter(service_id__in=all_service_id_list)
            service_map = {x.service_id: x for x in service_list}
            json_data = {}
            json_svg = {}
            service_status_map = {}
            # 批量查询服务状态
            if len(service_list) > 0:
                service_region = service_list[0].service_region
                id_string = ','.join(service_map.keys())
                try:
                    service_status_list = region_api.service_status(service_region, self.tenantName,
                                                                    {"service_ids": service_map.keys(),
                                                                     "enterprise_id": self.tenant.enterprise_id})
                    service_status_list = service_status_list["list"]
                    service_status_map = {status_map["service_id"]: status_map for status_map in service_status_list}
                except Exception as e:
                    logger.error('batch query service status failed!')
                    logger.exception(e)

            # 拼接服务状态
            for service_info in service_list:
                json_data[service_info.service_cname] = {
                    "service_id": service_info.service_id,
                    "service_cname": service_info.service_cname,
                    "service_alias": service_info.service_alias,
                    "node_num": service_info.min_node,
                }
                json_svg[service_info.service_cname] = []

                # closed\running\starting\unusual\closed\unknown
                if service_status_map.get(service_info.service_id):
                    status = service_status_map.get(service_info.service_id).get("status", "Unknown")
                    status_cn = service_status_map.get(service_info.service_id).get("status_cn", None)
                else:
                    status = None
                    status_cn = None
                if status:
                    if not status_cn:
                        from www.utils.status_translate import status_map
                        status_info_map = status_map().get(status, None)
                        if not status_info_map:
                            status_cn = "未知"
                        else:
                            status_cn = status_info_map["status_cn"]
                    json_data[service_info.service_cname]['cur_status'] = status
                    json_data[service_info.service_cname]['status_cn'] = status_cn
                else:
                    json_data[service_info.service_cname]['cur_status'] = 'Unknown'
                    json_data[service_info.service_cname]['status_cn'] = '未知'
                # 查询是否打开对外服务端口
                port_list = TenantServicesPort.objects.filter(service_id=service_info.service_id)
                # 判断服务是否有对外端口
                outer_port_exist = False
                if len(port_list) > 0:
                    outer_port_exist = reduce(lambda x, y: x or y, [t.is_outer_service for t in list(port_list)])
                json_data[service_info.service_cname]['is_internet'] = outer_port_exist

            for service_relation in service_relation_list:
                tmp_id = service_relation.service_id
                tmp_dep_id = service_relation.dep_service_id
                tmp_info = service_map.get(tmp_id)
                tmp_dep_info = service_map.get(tmp_dep_id)
                # 依赖服务的cname
                tmp_info_relation = []
                if tmp_info.service_cname in json_svg.keys():
                    tmp_info_relation = json_svg.get(tmp_info.service_cname)
                tmp_info_relation.append(tmp_dep_info.service_cname)
                json_svg[tmp_info.service_cname] = tmp_info_relation

            result["status"] = 200
            result["json_data"] = json_data
            result["json_svg"] = json_svg
        except Exception as e:
            logger.exception(e)
        return JsonResponse(result, status=200)


class TopologicalServiceView(AuthedView):

    def get(self, request, *args, **kwargs):
        """获取拓扑图中服务信息"""
        result = {}
        # 服务信息
        tenant_id = self.service.tenant_id
        tenant_name = self.tenantName
        service_id = self.service.service_id
        service_alias = self.service.service_alias
        service_cname = self.service.service_cname
        service_region = self.service.service_region
        deploy_version = self.service.deploy_version
        total_memory = self.service.min_memory * self.service.min_node
        # 服务名称
        result['tenant_id'] = tenant_id
        result['service_alias'] = service_alias
        result['service_cname'] = service_cname
        result['service_region'] = service_region
        result['deploy_version'] = deploy_version
        result['total_memory'] = total_memory
        result['cur_status'] = 'Unknown'
        # 服务端口信息
        port_list = TenantServicesPort.objects.filter(service_id=service_id)
        # 判断服务是否有对外端口
        # outer_port_exist = False
        # if len(port_list) > 0:
        #     outer_port_exist = reduce(lambda x, y: x or y, [t.is_outer_service for t in list(port_list)])
        # result['is_internet'] = outer_port_exist
        # result["ports"] = map(lambda x: x.to_dict(), port_list)
        # 域名信息
        service_domain_list = ServiceDomain.objects.filter(service_id=service_id)
        port_map = {}
        # 判断是否存在自定义域名
        for port in port_list:
            port_info = port.to_dict()
            exist_service_domain = False
            # 打开对外端口
            if port.is_outer_service:
                if port.protocol != 'http':
                    cur_region = service_region.replace("-1", "")
                    domain = "{0}.{1}.{2}-s1.goodrain.net".format(service_alias, tenant_name, cur_region)
                    if settings.STREAM_DOMAIN_URL[service_region] != "":
                        domain = settings.STREAM_DOMAIN_URL[service_region]
                    outer_service = {"domain": domain}
                    try:
                        outer_service['port'] = port.mapping_port
                    except Exception as e:
                        logger.exception(e)
                        outer_service['port'] = '-1'
                elif port.protocol == 'http':
                    exist_service_domain = True
                    outer_service = {
                        "domain": "{0}.{1}{2}".format(service_alias, tenant_name,
                                                      settings.WILD_DOMAINS[service_region]),
                        "port": settings.WILD_PORTS[service_region]
                    }
                else:
                    outer_service = {
                        "domain": 'error',
                        "port": '-1'
                    }
                # 外部url
                if outer_service['port'] == '-1':
                    port_info['outer_url'] = 'query error!'
                else:
                    if self.service.port_type == "multi_outer":
                        if port.protocol == "http":
                            port_info['outer_url'] = '{0}.{1}:{2}'.format(port.container_port, outer_service['domain'],
                                                                          outer_service['port'])
                        else:
                            port_info['outer_url'] = '{0}:{1}'.format(outer_service['domain'], outer_service['port'])
                    else:
                        port_info['outer_url'] = '{0}:{1}'.format(outer_service['domain'], outer_service['port'])
            # 自定义域名
            if exist_service_domain:
                if len(service_domain_list) > 0:
                    for domain in service_domain_list:
                        if port.container_port == domain.container_port:
                            if port_info.get('domain_list') is None:
                                if domain.protocol == "https":
                                    port_info['domain_list'] = ["https://" + domain.domain_name]
                                else:
                                    port_info['domain_list'] = ["http://" + domain.domain_name]
                            else:
                                if domain.protocol == "https":
                                    port_info['domain_list'].append("https://" + domain.domain_name)
                                else:
                                    port_info['domain_list'].append("http://" + domain.domain_name)
            port_map[port.container_port] = port_info
        result["port_list"] = port_map
        # pod节点信息
        try:
            status_data = region_api.check_service_status(service_region, self.tenantName, self.service.service_alias,
                                                          self.tenant.enterprise_id)
            region_data = status_data["bean"]

            pod_list = region_api.get_service_pods(service_region, self.tenantName, self.service.service_alias,
                                                   self.tenant.enterprise_id)
            region_data["pod_list"] = pod_list["list"]
        except Exception as e:
            logger.exception(e)
            region_data = {}
        # result["region_data"] = region_data
        result = dict(result, **region_data)

        # 依赖服务信息
        relation_list = TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id)
        relation_id_list = set([x.dep_service_id for x in relation_list])
        relation_service_list = TenantServiceInfo.objects.filter(service_id__in=relation_id_list)
        relation_service_map = {x.service_id: x for x in relation_service_list}

        relation_port_list = TenantServicesPort.objects.filter(service_id__in=relation_id_list)
        relation_map = {}

        for relation_port in relation_port_list:
            tmp_service_id = relation_port.service_id
            if tmp_service_id in relation_service_map.keys():
                tmp_service = relation_service_map.get(tmp_service_id)
                relation_info = relation_map.get(tmp_service_id)
                if relation_info is None:
                    relation_info = []
                # 处理依赖服务端口
                if relation_port.is_inner_service:
                    relation_info.append({
                        "service_cname": tmp_service.service_cname,
                        "service_alias": tmp_service.service_alias,
                        "mapping_port": relation_port.mapping_port,
                    })
                    relation_map[tmp_service_id] = relation_info
        result["relation_list"] = relation_map
        result["status"] = 200
        return JsonResponse(result, status=200)


class TopologicalInternetView(AuthedView):

    def get(self, request, group_id, *args, **kwargs):
        """根据group的id获取group的详细信息"""
        # group_id = request.GET.get("group_id", None)
        result = {}
        logger.debug("query topological graph from:{0}".format(group_id))
        try:
            if group_id is None or not group_id.isdigit():
                result["status"] = 501
                result["msg"] = "group id is missing or not digit!"
                return JsonResponse(result, status=501)

            tenant_id = self.tenant.tenant_id
            group_count = ServiceGroup.objects.filter(tenant_id=tenant_id, ID=group_id).count()
            if group_count == 0:
                result["status"] = 502
                result["msg"] = "group is not yours!"
                return JsonResponse(result, status=502)
            service_id_list = ServiceGroupRelation.objects.filter(group_id=group_id).values_list("service_id",
                                                                                                 flat=True)
            service_list = TenantServiceInfo.objects.filter(service_id__in=service_id_list)
            json_data = {}
            outer_http_service_list = []
            for service in service_list:
                port_list = TenantServicesPort.objects.filter(service_id=service.service_id)
                # 判断服务是否有对外端口
                outer_http_service = False
                if len(port_list) > 0:
                    outer_http_service = reduce(lambda x, y: x or y,
                                                [t.is_outer_service and t.protocol == 'http' for t in list(port_list)])
                if outer_http_service:
                    outer_http_service_list.append(service)
            # 每个对外可访问的服务
            result_list = []
            for service_info in outer_http_service_list:
                service_domain_result = {}
                service_region = service_info.service_region
                port_list = TenantServicesPort.objects.filter(service_id=service_info.service_id)
                service_domain_list = ServiceDomain.objects.filter(service_id=service_info.service_id)
                port_map = {}
                for port in port_list:
                    port_info = port.to_dict()
                    exist_service_domain = False
                    # 打开对外端口
                    if port.is_outer_service:
                        if port.protocol != 'http':
                            cur_region = service_region.replace("-1", "")
                            domain = "{0}.{1}.{2}-s1.goodrain.net".format(service_info.service_alias,
                                                                          self.tenant.tenant_name, cur_region)
                            if settings.STREAM_DOMAIN_URL[service_region] != "":
                                domain = settings.STREAM_DOMAIN_URL[service_region]
                            outer_service = {"domain": domain}
                            try:
                                outer_service['port'] = port.mapping_port
                            except Exception as e:
                                logger.exception(e)
                                outer_service['port'] = '-1'
                        elif port.protocol == 'http':
                            exist_service_domain = True
                            outer_service = {
                                "domain": "{0}.{1}{2}".format(service_info.service_alias, self.tenant.tenant_name,
                                                              settings.WILD_DOMAINS[service_region]),
                                "port": settings.WILD_PORTS[service_region]
                            }
                        else:
                            outer_service = {
                                "domain": 'error',
                                "port": '-1'
                            }
                        # 外部url
                        if outer_service['port'] == '-1':
                            port_info['outer_url'] = 'query error!'
                        else:
                            if service_info.port_type == "multi_outer":
                                if port.protocol == "http":
                                    port_info['outer_url'] = '{0}.{1}:{2}'.format(port.container_port,
                                                                                  outer_service['domain'],
                                                                                  outer_service['port'])
                                else:
                                    port_info['outer_url'] = '{0}:{1}'.format(outer_service['domain'],
                                                                              outer_service['port'])
                            else:
                                port_info['outer_url'] = '{0}:{1}'.format(outer_service['domain'],
                                                                          outer_service['port'])
                    # 自定义域名
                    if exist_service_domain:
                        if len(service_domain_list) > 0:
                            for domain in service_domain_list:
                                if port.container_port == domain.container_port:

                                    if port_info.get('domain_list') is None:
                                        if domain.protocol == "https":
                                            port_info['domain_list'] = ["https://" + domain.domain_name]
                                        else:
                                            port_info['domain_list'] = ["http://" + domain.domain_name]
                                    else:
                                        if domain.protocol == "https":
                                            port_info['domain_list'].append("https://" + domain.domain_name)
                                        else:
                                            port_info['domain_list'].append("http://" + domain.domain_name)

                    port_map[port.container_port] = port_info
                service_domain_result["service_alias"] = service_info.service_alias
                service_domain_result["service_cname"] = service_info.service_cname
                service_domain_result["port_map"] = port_map
                result_list.append(service_domain_result)
            result["result_list"] = result_list
        except Exception as e:
            logger.debug(e)
        return JsonResponse(result, status=200)
