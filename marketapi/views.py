# -*- coding: utf8 -*-
import logging
import time
from random import randint

from rest_framework import status

from base_view import EnterpriseMarketAPIView
from marketapi.services import MarketServiceAPIManager
from www.apiclient.regionapi import RegionInvokeApi
from www.services import tenant_svc

logger = logging.getLogger('marketapi')
LOGGER_TAG = 'marketapi'
market_api = MarketServiceAPIManager()
region_api = RegionInvokeApi()


class MarketSSOUserInitAPIView(EnterpriseMarketAPIView):
    allowed_methods = ('GET',)

    def get(self, request, sso_user_id):
        """
        SSO用户初始化
        ---
        parameters:
            - name: sso_user_id
              description: sso上的用户ID
              required: true
              type: string
              paramType: path
        """
        user = request.user

        if not user.is_active:
            tenant = market_api.create_and_init_tenant(user)
        else:
            tenant = market_api.get_default_tenant_by_user(user.user_id)

        return self.success_response(
            data={'user_id': user.user_id,
                  'is_active': user.is_active,
                  'tenant_id': tenant.tenant_id,
                  'tenant_name': tenant.tenant_name,
                  'enterprise_id': tenant.enterprise_id})


class MarketSSOUserAPIView(EnterpriseMarketAPIView):
    allowed_methods = ('GET',)

    def get(self, request, sso_user_id):
        """
        获取SSO用户在云帮内部的用户信息
        ---
        parameters:
            - name: sso_user_id
              description: sso上的用户ID
              required: true
              type: string
              paramType: path
        """
        user = request.user

        tenants = market_api.list_user_tenants(user.user_id)

        default_tenant_name = ''
        if tenants:
            default_tenant_name = tenants[0].tenant_name

        ret_tenants = []
        for tenant in tenants:
            ret_tenants.append({
                'tenant_id': tenant.tenant_id,
                'tenant_name': tenant.tenant_name,
                'enterprise_id': tenant.enterprise_id
            })
        return self.success_response(
            data={'user_id': user.user_id, 'is_active': user.is_active,
                  'tenant_name': default_tenant_name, 'tenants': ret_tenants})


# class MarketGroupServiceListAPIView(EnterpriseMarketAPIView):
#     allowed_methods = ('GET', 'POST')
#
#     def get(self, request, tenant_name):
#         """
#         获取云市租户下应用组列表
#         ---
#         parameters:
#             - name: tenant_name
#               description: 租户名
#               required: true
#               type: string
#               paramType: path
#         """
#
#         user = request.user
#
#         tenant = market_api.get_tenant_by_name(tenant_name)
#         if not tenant:
#             logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
#             return self.error_response(code=status.HTTP_404_NOT_FOUND,
#                                        msg='tenant does not exist!',
#                                        msg_show='租户不存在')
#
#         # if tenant.creater != user.user_id:
#         #     logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
#         #     return self.error_response(code=status.HTTP_403_FORBIDDEN,
#         #                                msg='no access right for this tenant!',
#         #                                msg_show='您无权操作此租户')
#
#         data = []
#         group_list = market_api.list_tenant_group(tenant)
#         for group in group_list:
#             service_list = market_api.list_tenant_group_service(tenant, group)
#
#             services_status = []
#             for service in service_list:
#                 result = market_api.get_tenant_service_status(tenant, service)
#                 services_status.append(result)
#
#             group_status = market_api.compute_group_service_status(services_status)
#             data.append({
#                 'group_id': group.ID,
#                 'group_name': group.group_name,
#                 'tenant_name': tenant.tenant_name,
#                 'group_status': group_status,
#             })
#
#         return self.success_response(data)
#
#     def post(self, request, tenant_name):
#         """
#         在云市指定租户下创建新的组应用
#         ---
#         parameters:
#             - name: tenant_name
#               description: 租户名
#               required: true
#               type: string
#               paramType: path
#             - name: group_key
#               description: 应用组key
#               required: true
#               type: string
#               paramType: query
#             - name: version
#               description: 应用组version
#               required: true
#               type: string
#               paramType: query
#             - name: region
#               description: 安装到指定的数据中心
#               required: true
#               type: string
#               paramType: query
#         """
#         group_key = request.POST.get('group_key')
#         group_version = request.POST.get('version')
#         region = request.POST.get('region')
#         if not group_key or not group_version:
#             return self.error_response(code=status.HTTP_400_BAD_REQUEST,
#                                        msg='group_key, version can not be null',
#                                        msg_show='参数不合法')
#
#         user = request.user
#
#         tenant = market_api.get_tenant_by_name(tenant_name)
#         if not tenant:
#             logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
#             return self.error_response(code=status.HTTP_404_NOT_FOUND,
#                                        msg='tenant does not exist!',
#                                        msg_show='租户不存在')
#
#         # if tenant.creater != user.user_id:
#         #     logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
#         #     return self.error_response(code=status.HTTP_403_FORBIDDEN,
#         #                                msg='no access right for this tenant!',
#         #                                msg_show='您无权操作此租户')
#
#         app_service_group = market_api.get_app_service_group_by_unique(group_key, group_version)
#         if not app_service_group:
#             logger.error(LOGGER_TAG, "本地分享应用组不存在!")
#             return self.error_response(code=status.HTTP_404_NOT_FOUND,
#                                        msg='app_service_group does not exist!',
#                                        msg_show='应用组模板不存在')
#
#         success, message, result = market_api.install_services(user, tenant, group_key, group_version, region, 'cloud')
#         return self.success_response(result)


class MarketGroupServiceAPIView(EnterpriseMarketAPIView):
    allowed_methods = ('GET',)

    def get(self, request, tenant_name, group_id):
        """
        获取云市应用组详情
        ---
        parameters:
            - name: tenant_name
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用组id
              required: true
              type: string
              paramType: path
        """
        user = request.user

        tenant = market_api.get_tenant_by_name(tenant_name)
        if not tenant:
            logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='tenant does not exist!',
                                       msg_show='租户不存在')

        # if tenant.creater != user.user_id:
        #     logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
        #     return self.error_response(code=status.HTTP_403_FORBIDDEN,
        #                                msg='no access right for this tenant!',
        #                                msg_show='您无权操作此租户')

        group = market_api.get_tenant_group_by_id(tenant, group_id)
        if not group:
            logger.error(LOGGER_TAG,
                         "Tenant {0} Group {1} is not exists".format(tenant.tenant_name, group_id))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='group does not exist!',
                                       msg_show='组应用不存在')

        service_list = market_api.list_tenant_group_service(tenant, group)

        services_data = []
        for service in service_list:
            result = market_api.get_tenant_service_status(tenant, service)
            services_data.append({
                'service_id': service.service_id,
                'service_cname': service.service_cname,
                'service_alias': service.service_alias,
                'service_status': result,
                'access_url': market_api.get_access_url(tenant, service),
            })

        services_status = [svc['service_status'] for svc in services_data]
        group_status = market_api.compute_group_service_status(services_status)

        group_data = {
            'group_id': group.ID,
            'group_name': group.group_name,
            'group_status': group_status,
            'tenant_name': tenant.tenant_name,
            'services': services_data
        }

        return self.success_response(group_data)


class MarketGroupServiceLifeCycleAPIView(EnterpriseMarketAPIView):
    allowed_methods = ('PUT',)
    allowed_action = ('start', 'stop', 'restart')

    def put(self, request, tenant_name, group_id, action):
        """
        云市应用组生命周期状态操作接口
        start: 启动组应用中包含的所有服务
        stop: 停止组应用中包含的所有服务
        restart: 重启组应用中所有的服务
        ---
        parameters:
            - name: tenant_name
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: group_id
              description: 应用组id
              required: true
              type: string
              paramType: path
            - name: action
              description: 应用组实施操作类型
              required: true
              type: string
              paramType: path
        """
        if not self.__allowed_action(action):
            return self.error_response(code=status.HTTP_400_BAD_REQUEST,
                                       msg='not support operation!',
                                       msg_show='不支持的操作请求类型')

        user = request.user

        tenant = market_api.get_tenant_by_name(tenant_name)
        if not tenant:
            logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='tenant does not exist!',
                                       msg_show='租户不存在')

        # if tenant.creater != user.user_id:
        #     logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
        #     return self.error_response(code=status.HTTP_403_FORBIDDEN,
        #                                msg='no access right for this tenant!',
        #                                msg_show='您无权操作此租户')

        group = market_api.get_tenant_group_by_id(tenant, group_id)
        if not group:
            logger.error(LOGGER_TAG,
                         "Tenant {0} Group {1} is not exists".format(tenant.tenant_name, group_id))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='group does not exist!',
                                       msg_show='组应用不存在')

        operator_name = request.data.get("username", "system")
        if action == 'start':
            result = market_api.start_group_service(tenant, group, operator_name)
        elif action == 'stop':
            result = market_api.stop_group_service(tenant, group, operator_name)
        elif action == 'restart':
            result = market_api.restart_group_service(tenant, group, operator_name)

        return self.success_response(result)

    def __allowed_action(self, action):
        return action in self.allowed_action


class MarketServiceAPIView(EnterpriseMarketAPIView):
    allowed_methods = ('GET',)

    def get(self, request, tenant_name, service_alias):
        """
        获取云市应用组中特定服务详情查询接口
        ---
        parameters:
            - name: tenant_name
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: service_alias
              description: 应用别名
              required: true
              type: string
              paramType: path
        """
        logger.debug(LOGGER_TAG, request.data)

        user = request.user

        tenant = market_api.get_tenant_by_name(tenant_name)
        if not tenant:
            logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='tenant does not exist!',
                                       msg_show='租户不存在')

        # if tenant.creater != user.user_id:
        #     logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
        #     return self.error_response(code=status.HTTP_403_FORBIDDEN,
        #                                msg='no access right for this tenant!',
        #                                msg_show='您无权操作此租户')

        service = market_api.get_tenant_service_by_alias(tenant, service_alias)
        if not service:
            logger.error(LOGGER_TAG,
                         "Tenant {0} ServiceAlias {1} is not exists".format(tenant.tenant_name, service_alias))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='group does not exist!',
                                       msg_show='租户下应用不存在')

        result = market_api.get_tenant_service_status(tenant, service)

        service_data = {
            'service_id': service.service_id,
            'service_cname': service.service_cname,
            'service_alias': service.service_alias,
            'service_status': result,
        }

        return self.success_response(service_data)

    def delete(self, request, tenant_name, service_alias):
        """
        删除云市应用组中特定服务接口
        ---
        parameters:
            - name: tenant_name
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: service_alias
              description: 应用别名
              required: true
              type: string
              paramType: path
        """

        logger.debug(LOGGER_TAG, request.data)

        user = request.user

        tenant = market_api.get_tenant_by_name(tenant_name)
        if not tenant:
            logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='tenant does not exist!',
                                       msg_show='租户不存在')

        # if tenant.creater != user.user_id:
        #     logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
        #     return self.error_response(code=status.HTTP_403_FORBIDDEN,
        #                                msg='no access right for this tenant!',
        #                                msg_show='您无权操作此租户')

        service = market_api.get_tenant_service_by_alias(tenant, service_alias)
        if not service:
            logger.error(LOGGER_TAG,
                         "Tenant {0} ServiceAlias {1} is not exists".format(tenant.tenant_name, service_alias))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='group does not exist!',
                                       msg_show='租户下应用不存在')

        operator_name = request.data.get("username", "system")
        code, success, msg = market_api.delete_service(tenant, service, operator_name)
        if success:
            return self.success_response(msg=msg)
        else:
            return self.error_response(msg=msg)


class MarketServiceLifeCycleAPIView(EnterpriseMarketAPIView):
    allowed_methods = ('PUT',)
    allowed_action = ('start', 'stop', 'restart')

    def put(self, request, tenant_name, service_alias, action):
        """
           操作云市应用组中特定服务生命周期接口
           start: 启动应用
           stop: 停止应用
           restart: 重启应用
           ---
           parameters:
               - name: tenant_name
                 description: 租户名
                 required: true
                 type: string
                 paramType: path
               - name: service_alias
                 description: 应用组别名
                 required: true
                 type: string
                 paramType: path
               - name: action
                 description: 应用组实施操作类型
                 required: true
                 type: string
                 paramType: path
           """
        logger.debug(LOGGER_TAG, request.data)

        if not self.__allowed_action(action):
            return self.error_response(code=status.HTTP_400_BAD_REQUEST,
                                       msg='not support operation!',
                                       msg_show='不支持的操作请求类型')

        user = request.user

        tenant = market_api.get_tenant_by_name(tenant_name)
        if not tenant:
            logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='tenant does not exist!',
                                       msg_show='租户不存在')

        # if tenant.creater != user.user_id:
        #     logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
        #     return self.error_response(code=status.HTTP_403_FORBIDDEN,
        #                                msg='no access right for this tenant!',
        #                                msg_show='您无权操作此租户')

        service = market_api.get_tenant_service_by_alias(tenant, service_alias)
        if not service:
            logger.error(LOGGER_TAG,
                         "Tenant {0} ServiceAlias {1} is not exists".format(tenant.tenant_name, service_alias))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='group does not exist!',
                                       msg_show='租户下应用不存在')

        operator_name = request.data.get("username", "system")

        success, msg = True, 'ok'
        if action == 'start':
            code, success, msg = market_api.start_service(tenant, service, operator_name)
        elif action == 'stop':
            code, success, msg = market_api.stop_service(tenant, service, operator_name)
        elif action == 'restart':
            code, success, msg = market_api.restart_service(tenant, service, operator_name)

        if success:
            return self.success_response(msg=msg)
        else:
            return self.error_response(msg=msg)

    def __allowed_action(self, action):
        return action in self.allowed_action


class MarketServiceMonitorGraphAPIView(EnterpriseMarketAPIView):
    allowed_methods = ('GET',)

    graph_type = ['online-stat', 'response-time-stat']

    template = {
        "xAxisLabel": u"时间",
        "yAxisLabel": u"单位",
        "yAxisFormat": ',.2f',
    }

    # region_client = RegionServiceApi()

    metric_map = {
        'memory': {'metric': 'service.basic.node_memory', 'unit': 'MB'},
        'disk': {'metric': 'service.basic.disk_size', 'unit': 'MB'},
        'bandwidth': {"metric": 'service.basic.net.bytesout', "unit": 'bytes'},
        'response-time': {"metric": 'service.perf.web.response_time', "unit": "ms"},
        'throughput': {"metric": 'service.perf.web.throughput', "unit": "count"},
        'online': {"metric": 'service.analysis.online', "unit": u"人数"},
        'sqltime': {"metric": 'service.perf.mysql.sql_time', "unit": 'ms'},
        'sql-throughput': {"metric": 'service.perf.mysql.throughput', "unit": "count"},
    }

    downsamples = {
        '3m-ago': None,
        '1h-ago': '1m-avg',
        '8h-ago': '2m-avg',
        '24h-ago': '5m-avg',
        '7d-ago': '30m-avg',
    }

    def get(self, request, tenant_name, service_alias):
        """
        获取云市应用组中特定服务的监控信息
        ---
        parameters:
            - name: tenant_name
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: service_alias
              description: 应用别名
              required: true
              type: string
              paramType: path
            - name: graph_id
              description: 监控图表的数据来源ID, response-time-stat(响应时间), online-stat(在线人数).
              required: true
              type: string
              paramType: query
            - name: start
              description: 监控起始时间节点, 默认1h-ago, 可选1h-ago, 8h-ago, 24h-ago,1h-ago, 7dh-ago
              required: false
              type: string
              paramType: query
        """

        logger.debug(LOGGER_TAG, request.data)

        user = request.user

        tenant = market_api.get_tenant_by_name(tenant_name)
        if not tenant:
            logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='tenant does not exist!',
                                       msg_show='租户不存在')

        # if tenant.creater != user.user_id:
        #     logger.error(LOGGER_TAG, 'tenant [{0}] does not exist!'.format(tenant_name))
        #     return self.error_response(code=status.HTTP_403_FORBIDDEN,
        #                                msg='no access right for this tenant!',
        #                                msg_show='您无权操作此租户')

        service = market_api.get_tenant_service_by_alias(tenant, service_alias)
        if not service:
            logger.error(LOGGER_TAG,
                         "Tenant {0} ServiceAlias {1} is not exists".format(tenant.tenant_name, service_alias))
            return self.error_response(code=status.HTTP_404_NOT_FOUND,
                                       msg='group does not exist!',
                                       msg_show='租户下应用不存在')

        graph_id = request.GET.get('graph_id', None)
        start = request.GET.get('start', '1h-ago')
        get_last = request.GET.get('last', False)

        if graph_id not in self.graph_type:
            return self.error_response(code=status.HTTP_400_BAD_REQUEST,
                                       msg='unkonw graph id!',
                                       msg_show='参数错误!未知监控图表类型!')

        if start not in self.downsamples:
            start = self.downsamples['1h-ago']

        graph_key = graph_id.replace('-stat', '')
        result = self.template.copy()
        result['data'] = self.random_data(graph_key)
        data = self.get_tsdb_data(graph_key, start, tenant, service)
        if not data:
            return self.error_response('1005', 'graph data not found!')

        if get_last:
            tmp = data[0]['values']
            if len(tmp) > 0:
                tmp1 = tmp[-1]
                if len(tmp1) > 0:
                    result['value'] = tmp1[1]
        else:
            result['data'] = data
            self.add_tags(graph_key, result)

        return self.success_response(result)

    def random_data(self, graph_key):
        curr_time = int(time.time())

        def increase_time(step):
            return (curr_time + 30 * step) * 1000

        data = {
            "key": graph_key,
            "values": []
        }

        for i in range(30):
            data['values'].append([increase_time(i), randint(100, 1000)])
        return [data]

    def get_tsdb_data(self, graph_key, start, tenant, service):
        data = {"key": graph_key, "values": []}
        metric = self.metric_map.get(graph_key).get('metric', None)
        downsample = self.downsamples.get(start)
        aggregate = 'sum'

        if metric is not None:
            if downsample is None:
                queries = '{0}:{1}'.format(aggregate, metric)
            else:
                queries = '{0}:{1}:{2}'.format(aggregate, downsample, metric)

            if graph_key in ('memory', 'sqltime', 'sql-throughput'):
                tenant_region = tenant_svc.get_tenant_region_info(tenant, service.service_region)
                queries += '{' + 'tenant_id={0},service_id={1}'.format(tenant_region.region_tenant_id,
                                                                       service.service_id) + '}'
            else:
                # temp deal
                '''
                if self.service.port_type == "multi_outer" and graph_key not in ("disk","bandwidth"):
                    port = ""
                    tsps = TenantServicesPort.objects.filter(service_id=self.service.service_id, is_outer_service=True)
                    for tsp in tsps:
                        port = str(tsp.container_port)
                        break
                    queries += '{' + 'tenant={0},service={1}_{2}'.format(self.tenant.tenant_name, self.service.service_alias, port) + '}'
                else:
                    queries += '{' + 'tenant={0},service={1}'.format(self.tenant.tenant_name, self.service.service_alias) + '}'
                '''
                queries += '{' + 'tenant={0},service={1}'.format(tenant.tenant_name,
                                                                 service.service_alias) + '}'
            try:
                # query_data = self.region_client.opentsdbQuery(service.service_region, start, queries)
                body = {}
                body["start"] = start
                body["queries"] = queries
                result = region_api.get_opentsdb_data(service.service_region, tenant.tenant_name, body)
                query_data = result["bean"]
                if not query_data:
                    return None
            except Exception:
                return None

            for timestamp, value in sorted(query_data.items()):
                if graph_key == 'disk':
                    value = float(value) / (1024 * 1024)
                elif graph_key == 'online':
                    value = float(int(value))

                if isinstance(value, float):
                    if value.is_integer():
                        data['values'].append([int(timestamp) * 1000, int(value)])
                    else:
                        data['values'].append([int(timestamp) * 1000, float('%.3f' % value)])
                else:
                    data['values'].append([int(timestamp) * 1000, value])

            return [data]
        else:
            return None

    def add_tags(self, graph_key, result):
        if result['data'] is not None and len(result['data']) > 0:
            tmpdata = result['data'][0]['values']
            if tmpdata is not None and len(tmpdata) > 0:
                tem = tmpdata[0]
                if tem is not None and len(tem) > 0:
                    test_value = tem[1]
                    if isinstance(test_value, int):
                        result['yAxisFormat'] = ',.0f'

                    result['yAxisLabel'] = self.metric_map.get(graph_key, None).get('unit', '')
