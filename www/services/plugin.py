# -*- coding: utf8 -*-

from www.apiclient.regionapi import RegionInvokeApi
from www.db import BaseConnection

from www.models import TenantPlugin, PluginBuildVersion, PluginConfigGroup, PluginConfigItems, \
    TenantServicePluginRelation, TenantServicePluginAttr, ConstKey, TenantServiceRelation, \
    TenantServiceInfo, TenantServicesPort, Users, HasNoDownStreamService, TenantPluginShareInfo
import logging
from www.utils.crypt import make_uuid
import datetime
import copy
from django.forms import model_to_dict

logger = logging.getLogger('default')

BUILD_STATUS_MAP = {
    "building": "构建中",
    "build_fail": "构建失败",
    "build_success": "构建成功",
    "unbuild": "未构建",
    "time_out": "构建超时"
}

CATEGORY_MAP = {
    "output_net": "出口网络",
    "input_net": "入口网络",
    "performance_analysis": "性能分析",
    "analyst-plugin:perf": "性能分析",
    "init_type": "初始化类型",
    "common_type": "一般类型",
    "net-plugin:down": "出口网络",
    "net-plugin:up": "入口网络",
    "init-plugin": "初始化类型",
    "general-plugin": "一般类型",
}
CATEGORY_REGION_MAP = {

    "output_net": "net-plugin:down",
    "input_net": "net-plugin:up",
    "performance_analysis": "analyst-plugin:perf",
    "init_type": "init-plugin",
    "common_type": "general-plugin"
}

REGION_BUILD_STATUS_MAP = {
    "failure": "build_fail",
    "complete": "build_success",
    "building": "building",
    "timeout": "time_out",

}

# 插件构建完成状态
NO_NEED_UPDATE_STATUS = ["build_fail", "build_success", "time_out", "unbuild"]

region_api = RegionInvokeApi()


class PluginService(object):
    dsn = BaseConnection()

    def get_newest_plugin_version_info(self, region, tenant):
        """
        获取所有插件的最新构建信息
        :param region :数据中心信息
        :param tenant: 租户信息
        :return: 插件信息
        """
        result = []
        query_sql = """SELECT * from plugin_build_version  WHERE
                          id in (
                                   SELECT max(id) from plugin_build_version WHERE
                                    tenant_id="{0}" and region="{1}" GROUP BY plugin_id
                                ) and
                                  plugin_build_version.tenant_id="{2}";""".format(tenant.tenant_id, region,
                                                                                  tenant.tenant_id)

        data = self.dsn.query(query_sql)
        for d in data:
            plugin = TenantPlugin.objects.get(plugin_id=d.plugin_id)
            record_map = {}
            record_map["plugin_alias"] = plugin.plugin_alias
            record_map["plugin_name"] = plugin.plugin_name
            record_map["category"] = CATEGORY_MAP.get(plugin.category)
            record_map["build_version"] = d.build_version
            record_map["build_status"] = d.build_status
            record_map["plugin_id"] = plugin.plugin_id
            record_map["desc"] = plugin.desc
            result.append(record_map)
        return result

    def get_tenant_plugins(self, region, tenant):
        """
        获取租户下的所有插件
        :param region: 数据中心
        :param tenant: 租户信息
        :return: 插件信息
        """
        plugins = TenantPlugin.objects.filter(region=region, tenant_id=tenant.tenant_id)
        return plugins

    def get_tenant_plugin_by_plugin_id(self, tenant, plugin_id):
        """
        根据租户和插件id查询插件元信息
        :param tenant: 租户信息
        :param plugin_id: 插件ID列表
        :return: 插件信息
        """
        tenant_plugins = TenantPlugin.objects.filter(tenant_id=tenant.tenant_id, plugin_id=plugin_id)
        if tenant_plugins:
            return tenant_plugins[0]
        else:
            return {}

    def get_tenant_plugin_by_origin_key(self,region, tenant, origin_share_id):
        """
        根据origin key 获取plugin
        @param tenant:
        @param origin_key:
        @return:
        """
        tenant_plugins = TenantPlugin.objects.filter(region=region, tenant_id=tenant.tenant_id, origin_share_id=origin_share_id)
        if tenant_plugins:
            return tenant_plugins[0]
        else:
            return {}

    def get_tenant_plugin_versions(self, region, tenant, plugin_id):
        """
        获取指定租户的指定插件的所有版本信息
        :param region: 数据中心
        :param tenant: 租户
        :param plugin_id: 插件id
        :return: 指定插件的所有版本信息
        """
        plugin_build_version = PluginBuildVersion.objects.filter(region=region, tenant_id=tenant.tenant_id,
                                                                 plugin_id=plugin_id).order_by("-ID")
        return plugin_build_version

    def get_tenant_plugin_newest_versions(self, region_name, tenant, plugin_id):
        """
        获取指定租户的指定插件的最新版本信息
        :param tenant: 租户
        :param plugin_id: 插件id
        :return: 指定插件的所有版本信息
        """
        plugin_build_version = PluginBuildVersion.objects.filter(region=region_name, tenant_id=tenant.tenant_id,
                                                                 plugin_id=plugin_id,
                                                                 build_status="build_success").order_by("-ID")
        return plugin_build_version

    def get_tenant_service_plugin_relation(self, service_id):
        """
        获取当前应用关联的插件
        @param service_id: 租户id
        @return: 获取当前应用关联的插件
        """
        return TenantServicePluginRelation.objects.filter(service_id=service_id)

    def get_tenant_service_plugin_relation_by_plugin(self, service_id, plugin_id):
        """
        获取当前应用关联的插件
        @param service_id: 租户id
        @return: 获取当前应用关联的插件
        """
        return TenantServicePluginRelation.objects.filter(service_id=service_id, plugin_id=plugin_id)

    def add_service_plugin_relation(self, service_id, plugin_id, build_version):
        """
        添加应用与插件的绑定关系
        @param service_id: 服务id
        @param plugin_id: 插件id
        @param build_version: 插件构建版本
        @return:
        """
        return TenantServicePluginRelation.objects.create(
            service_id=service_id,
            build_version=build_version,
            plugin_id=plugin_id

        )

    def del_service_plugin_relation_and_attrs(self, service_id, plugin_id):
        # delete service plugin attrs
        TenantServicePluginAttr.objects.filter(service_id=service_id, plugin_id=plugin_id).delete()
        # delete service plugin relation
        TenantServicePluginRelation.objects.filter(service_id=service_id,
                                                   plugin_id=plugin_id).delete()
        return

    def del_service_plugin_attrs(self, service_id, plugin_id):
        # delete service plugin attrs
        TenantServicePluginAttr.objects.filter(service_id=service_id, plugin_id=plugin_id).delete()
        return

    def update_service_plugin_relation(self, service_id, plugin_id, build_version, switch):
        oldRelation = TenantServicePluginRelation.objects.get(service_id=service_id,
                                                              plugin_id=plugin_id)
        oldRelation.build_version = build_version
        oldRelation.plugin_status = switch
        oldRelation.save()
        # delete old service plugin attrs
        TenantServicePluginAttr.objects.filter(service_id=service_id, plugin_id=plugin_id).delete()
        return

    def get_service_meta_type(self, plugin_id, build_version):
        return PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version)

    def getPluginMetaType(self, plugin_id, build_version):
        return PluginBuildVersion.objects.get(plugin_id=plugin_id, build_version=build_version)

    def get_env_attr_by_service_meta_type(self, plugin_id, build_version, service_meta_type):
        return PluginConfigItems.objects.filter(plugin_id=plugin_id,
                                                build_version=build_version,
                                                service_meta_type=service_meta_type)

    def InsertSqlInDownStreamMeta(self, downStreamList, plugin_id, service_id):
        store_list = []
        for stream in downStreamList:
            for cf in stream.get("config"):
                tspa = TenantServicePluginAttr(
                    service_id=stream.get("service_id"),
                    service_alias=stream.get("service_alias"),
                    dest_service_id=stream.get("dest_service_id"),
                    dest_service_alias=stream.get("dest_service_alias"),
                    plugin_id=plugin_id,
                    service_meta_type=stream.get("service_meta_type"),
                    injection=stream.get("injection"),
                    container_port=stream.get("port"),
                    attr_name=cf.get("attr_name"),
                    attr_value=cf.get("attr_default_value", " "),
                    attr_type=cf.get("attr_type"),
                    attr_default_value=cf.get("attr_default_value"),
                    attr_alt_value=cf.get("attr_alt_value"),
                    protocol=stream.get("protocol"),
                    attr_info=cf.get("attr_info"),
                    is_change=cf.get("is_change")
                )
                store_list.append(tspa)
        TenantServicePluginAttr.objects.filter(
            service_id=service_id, plugin_id=plugin_id, service_meta_type=ConstKey.DOWNSTREAM_PORT).delete()
        TenantServicePluginAttr.objects.bulk_create(store_list)

    def UpdateSqlInDownStreamMeta(self, downStreamList, plugin_id, service_id):
        store_list = []
        for stream in downStreamList:
            for cf in stream.get("config"):
                tspa = TenantServicePluginAttr(
                    service_id=stream.get("service_id"),
                    service_alias=stream.get("service_alias"),
                    dest_service_id=stream.get("dest_service_id"),
                    dest_service_alias=stream.get("dest_service_alias"),
                    plugin_id=plugin_id,
                    service_meta_type=stream.get("service_meta_type"),
                    injection=stream.get("injection"),
                    container_port=stream.get("port"),
                    attr_name=cf.get("attr_name"),
                    attr_value=cf.get("attr_value", " "),
                    attr_type=cf.get("attr_type"),
                    attr_default_value=cf.get("attr_default_value"),
                    attr_alt_value=cf.get("attr_alt_value"),
                    protocol=stream.get("protocol"),
                    attr_info=cf.get("attr_info"),
                    is_change=cf.get("is_change")
                )
                store_list.append(tspa)
        TenantServicePluginAttr.objects.bulk_create(store_list)

    def InsertSqlInUpStreamMeta(self, upStreamList, plugin_id, service_id):
        store_list = []
        for stream in upStreamList:
            for cf in stream.get("config"):
                tspa = TenantServicePluginAttr(
                    service_id=stream.get("service_id"),
                    service_alias=stream.get("service_alias"),
                    plugin_id=plugin_id,
                    service_meta_type=stream.get("service_meta_type"),
                    injection=stream.get("injection"),
                    container_port=stream.get("port"),
                    attr_name=cf.get("attr_name"),
                    attr_value=cf.get("attr_default_value", " "),
                    attr_type=cf.get("attr_type"),
                    attr_default_value=cf.get("attr_default_value"),
                    attr_alt_value=cf.get("attr_alt_value"),
                    protocol=stream.get("protocol"),
                    attr_info=cf.get("attr_info"),
                    is_change=cf.get("is_change")
                )
                store_list.append(tspa)
        TenantServicePluginAttr.objects.filter(
            service_id=service_id, plugin_id=plugin_id, service_meta_type=ConstKey.UPSTREAM_PORT).delete()
        TenantServicePluginAttr.objects.bulk_create(store_list)

    def UpdateSqlInUpStreamMeta(self, upStreamList, plugin_id, service_id):
        store_list = []
        for stream in upStreamList:
            for cf in stream.get("config"):
                tspa = TenantServicePluginAttr(
                    service_id=stream.get("service_id"),
                    service_alias=stream.get("service_alias"),
                    plugin_id=plugin_id,
                    service_meta_type=stream.get("service_meta_type"),
                    injection=stream.get("injection"),
                    container_port=stream.get("port"),
                    attr_name=cf.get("attr_name"),
                    attr_value=cf.get("attr_value", " "),
                    attr_type=cf.get("attr_type"),
                    attr_default_value=cf.get("attr_default_value"),
                    attr_alt_value=cf.get("attr_alt_value"),
                    protocol=stream.get("protocol"),
                    attr_info=cf.get("attr_info"),
                    is_change=cf.get("is_change")
                )
                store_list.append(tspa)
        TenantServicePluginAttr.objects.bulk_create(store_list)

    def InsertSqlInENVMeta(self, envList, plugin_id, service_id):
        store_list = []
        for stream in envList:
            for cf in stream.get("config"):
                tspa = TenantServicePluginAttr(
                    service_id=stream.get("service_id"),
                    service_alias=stream.get("service_alias"),
                    plugin_id=plugin_id,
                    service_meta_type=stream.get("service_meta_type"),
                    container_port=0,
                    injection=stream.get("injection"),
                    attr_name=cf.get("attr_name"),
                    attr_value=cf.get("attr_default_value", " "),
                    attr_type=cf.get("attr_type"),
                    attr_default_value=cf.get("attr_default_value"),
                    attr_alt_value=cf.get("attr_alt_value"),
                    attr_info=cf.get("attr_info"),
                    is_change=cf.get("is_change")
                )
                store_list.append(tspa)
        TenantServicePluginAttr.objects.filter(
            service_id=service_id, plugin_id=plugin_id, service_meta_type=ConstKey.UNDEFINE).delete()
        TenantServicePluginAttr.objects.bulk_create(store_list)

    def UpdateSqlInENVMeta(self, envList, plugin_id, service_id):
        store_list = []
        for stream in envList:
            for cf in stream.get("config"):
                tspa = TenantServicePluginAttr(
                    service_id=stream.get("service_id"),
                    service_alias=stream.get("service_alias"),
                    plugin_id=plugin_id,
                    service_meta_type=stream.get("service_meta_type"),
                    container_port=0,
                    injection=stream.get("injection"),
                    attr_name=cf.get("attr_name"),
                    attr_value=cf.get("attr_value", " "),
                    attr_type=cf.get("attr_type"),
                    attr_default_value=cf.get("attr_default_value"),
                    attr_alt_value=cf.get("attr_alt_value"),
                    attr_info=cf.get("attr_info"),
                    is_change=cf.get("is_change")
                )
                store_list.append(tspa)
        TenantServicePluginAttr.objects.bulk_create(store_list)

    def getServicePluginAttrByAttrName(self, service_id, plugin_id, metaType, pubDict, configList):
        if metaType == ConstKey.DOWNSTREAM_PORT:
            attrList = TenantServicePluginAttr.objects.filter(
                service_id=service_id,
                plugin_id=plugin_id,
                service_meta_type=metaType,
                dest_service_alias=pubDict.get("dest_service_alias"),
                container_port=int(pubDict.get("port")),
                injection=pubDict.get("injection"))
            if len(attrList) == 0:
                return configList
            for config in configList:
                for attr in attrList:
                    if attr.attr_name == config.get("attr_name"):
                        config["attr_value"] = attr.attr_value
        elif metaType == ConstKey.UPSTREAM_PORT:
            attrList = TenantServicePluginAttr.objects.filter(
                service_id=service_id,
                plugin_id=plugin_id,
                service_meta_type=metaType,
                container_port=int(pubDict.get("port")),
                injection=pubDict.get("injection"))
            if len(attrList) == 0:
                return configList
            for config in configList:
                for attr in attrList:
                    if attr.attr_name == config.get("attr_name"):
                        config["attr_value"] = attr.attr_value
        elif metaType == ConstKey.UNDEFINE:
            attrList = TenantServicePluginAttr.objects.filter(
                service_id=service_id,
                plugin_id=plugin_id,
                service_meta_type=metaType,
                injection=pubDict.get("injection"))
            if len(attrList) == 0:
                return configList
            for config in configList:
                for attr in attrList:
                    if attr.attr_name == config.get("attr_name"):
                        config["attr_value"] = attr.attr_value
        return configList

    def getMetaBaseInfo(self, tenant_id, service_id, service_alias, plugin_id, build_version, meta_info, configList,
                        tag):
        if meta_info.service_meta_type == ConstKey.DOWNSTREAM_PORT:
            relations = TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id)
            if len(relations) == 0:
                logger.error("service {0} has no relation dest_service".format(service_id))
                raise HasNoDownStreamService("has no dest_service")
            downStreamList = []
            for relation in relations:
                dest_service_id = relation.dep_service_id
                dest_service = TenantServiceInfo.objects.get(tenant_id=tenant_id,
                                                             service_id=dest_service_id)
                dest_service_alias = dest_service.service_alias
                dest_service_cname = dest_service.service_cname
                ports = TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=dest_service_id)
                if len(ports) == 0:
                    continue
                for port in ports:
                    destServiceDict = {}
                    destServiceDict["service_meta_type"] = ConstKey.DOWNSTREAM_PORT
                    destServiceDict["injection"] = meta_info.injection
                    destServiceDict["port"] = int(port.container_port)
                    destServiceDict["protocol"] = port.protocol
                    destServiceDict["service_alias"] = service_alias
                    destServiceDict["service_id"] = service_id
                    destServiceDict["dest_service_alias"] = dest_service_alias
                    destServiceDict["dest_service_id"] = dest_service_id
                    destServiceDict["dest_service_cname"] = dest_service_cname
                    destServiceDict["config"] = copy.deepcopy(self.getServicePluginAttrByAttrName(
                        service_id, plugin_id, ConstKey.DOWNSTREAM_PORT, destServiceDict, configList))
                    downStreamList.append(destServiceDict)
            if tag == "post":
                self.InsertSqlInDownStreamMeta(downStreamList, plugin_id, service_id)
            logger.debug("plugin.relation", "downstreamList is {}".format(downStreamList))
            return downStreamList
        elif meta_info.service_meta_type == ConstKey.UPSTREAM_PORT:
            upStreamList = []
            ports = TenantServicesPort.objects.filter(tenant_id=tenant_id, service_id=service_id)
            if len(ports) == 0:
                return []
            for port in ports:
                serviceDict = {}
                serviceDict["service_meta_type"] = ConstKey.UPSTREAM_PORT
                serviceDict["injection"] = meta_info.injection
                serviceDict["port"] = int(port.container_port)
                serviceDict["protocol"] = port.protocol
                serviceDict["service_alias"] = service_alias
                serviceDict["service_id"] = service_id
                serviceDict["config"] = copy.deepcopy(self.getServicePluginAttrByAttrName(
                    service_id, plugin_id, ConstKey.UPSTREAM_PORT, serviceDict, configList))
                upStreamList.append(serviceDict)
            if tag == "post":
                self.InsertSqlInUpStreamMeta(upStreamList, plugin_id, service_id)
            logger.debug("plugin.relation", "upstreamList is {}".format(upStreamList))
            return upStreamList
        elif meta_info.service_meta_type == ConstKey.UNDEFINE:
            envList = []
            DDict = {}
            DDict["service_meta_type"] = ConstKey.UNDEFINE
            DDict["injection"] = meta_info.injection
            DDict["service_alias"] = service_alias
            DDict["service_id"] = service_id
            DDict["config"] = copy.deepcopy(self.getServicePluginAttrByAttrName(
                service_id, plugin_id, ConstKey.UNDEFINE, DDict, configList))
            envList.append(DDict)
            if tag == "post":
                self.InsertSqlInENVMeta(envList, plugin_id, service_id)
            logger.debug("plugin.relation", "upstreamList is {}".format(envList))
            return envList
        else:
            logger.error("plugin.relation", "meta info is {}".format(meta_info.service_meta_type))
            return []

    def metaTypeAttrs(self, tenant_id, service_id, attrList, metaType):
        if metaType == ConstKey.DOWNSTREAM_PORT:
            relations = TenantServiceRelation.objects.filter(tenant_id=tenant_id, service_id=service_id)
            if len(relations) == 0:
                logger.error("service {0} has no relation dest_service".format(service_id))
                return {}

    def get_tenant_plugin_version_by_plugin_id_and_version(self, tenant, plugin_id, build_version=None):
        """
        根据插件id和版本信息获取插件版本信息
        :param tenant: 租户
        :param plugin_id: 插件id
        :param build_version: 指定插件的版本
        :return: 指定插件的和版本的构建信息
        """
        if not build_version:
            plugin_build_versions = PluginBuildVersion.objects.filter(tenant_id=tenant.tenant_id,
                                                                      plugin_id=plugin_id).order_by("-ID")
        else:
            plugin_build_versions = PluginBuildVersion.objects.filter(tenant_id=tenant.tenant_id, plugin_id=plugin_id,
                                                                      build_version=build_version).order_by("-ID")
        if plugin_build_versions:
            return plugin_build_versions[0]
        return None

    def init_plugin(self, tenant, user_id, region, desc, plugin_alias, category, build_source, build_status, image,
                    code_repo, min_memory, build_cmd="", image_tag="", code_version=""):
        """初始化插件信息"""
        plugin = self.create_plugin(tenant, user_id, region, desc, plugin_alias, category, build_source, image,
                                    code_repo)
        build_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        min_cpu = self.calculate_cpu(region, min_memory)
        plugin_build_version = self.create_plugin_build_version(region, plugin.plugin_id, tenant.tenant_id, user_id, "",
                                                                build_version, "unbuild", min_memory, min_cpu,
                                                                build_cmd, image_tag, code_version)
        return plugin_build_version.plugin_id, plugin_build_version.build_version

    def create_plugin(self, tenant, user_id, region, desc, plugin_alias, category, build_source, image, code_repo):
        """创建插件基础信息"""
        plugin_id = make_uuid()
        category = CATEGORY_REGION_MAP.get(category, category)
        tenant_plugin = TenantPlugin.objects.create(
            plugin_id=plugin_id,
            tenant_id=tenant.tenant_id,
            region=region,
            create_user=user_id,
            desc=desc,
            plugin_name="gr" + plugin_id[:6],
            plugin_alias=plugin_alias,
            category=category,
            build_source=build_source,
            image=image,
            code_repo=code_repo
        )
        return tenant_plugin

    def sortList(self, pList):
        listp = []
        for pdict in pList:
            strdict = ""
            for (k, v) in pdict.items():
                strmm = "{0}^-^{1}".format(str(k), str(v))
                if strdict:
                    strdict = "{0}^_^{1}".format(strdict, strmm)
                else:
                    strdict = strmm
            listp.append(strdict)
        logger.debug("plugin.relation", "listp is {}".format(listp))
        listp = list(set(listp))
        # ['port^-^5000^_^name^-^gr1', 'port^-^6000^_^name^-^gr1']
        listDict = []
        for mm in listp:
            listMM = mm.split("^_^")
            ppdict = {}
            for nn in listMM:
                listNN = nn.split("^-^")
                ppdict[listNN[0]] = listNN[1]
            listDict.append(ppdict)
        logger.debug("plugin.relation", "listDict is {}".format(listDict))
        return listDict

    def createAttrsJsonForRegion(self, service_id, service_alias, plugin_id):
        complex_envs = {}
        base_services = []
        base_ports = []
        normal_envs = []
        auto_envs = {}
        logger.debug("plugin.relation",
                     "service_id: {0}, plugin_id:{1}, service_alias:{2}".format(service_id, service_alias, plugin_id))
        downStream_attrsList = TenantServicePluginAttr.objects.filter(
            service_id=service_id, plugin_id=plugin_id, service_meta_type=ConstKey.DOWNSTREAM_PORT)
        upstream_attrsList = TenantServicePluginAttr.objects.filter(
            service_id=service_id, plugin_id=plugin_id, service_meta_type=ConstKey.UPSTREAM_PORT)
        env_attrsList = TenantServicePluginAttr.objects.filter(
            service_id=service_id, plugin_id=plugin_id, service_meta_type=ConstKey.UNDEFINE)

        # 处理downstram
        service_port_items = self.sortList(downStream_attrsList.values(
            "container_port", "dest_service_alias", "dest_service_id", "service_meta_type", "protocol"))
        logger.debug("plugin.relation", "service port items is {}".format(service_port_items))
        if len(service_port_items) > 0:
            for service_port in service_port_items:
                _base_services = {}
                _base_services["service_alias"] = service_alias
                _base_services["service_id"] = service_id
                _base_services["depend_service_id"] = service_port["dest_service_id"]
                _base_services["depend_service_alias"] = service_port["dest_service_alias"]
                _base_services["port"] = int(service_port["container_port"])
                _base_services["protocol"] = service_port["protocol"]
                _options = {}
                for attr in downStream_attrsList:
                    if attr.container_port != int(service_port["container_port"]) or \
                                    attr.dest_service_alias != service_port["dest_service_alias"]:
                        continue
                    _options[attr.attr_name] = attr.attr_value
                _base_services["options"] = _options
                base_services.append(_base_services)

        # 处理 upstream
        port_items = self.sortList(upstream_attrsList.values("container_port", "service_meta_type", "protocol"))
        logger.debug("plugin.relation", "port items is {}".format(port_items))
        if len(port_items) > 0:
            for port in port_items:
                _base_port = {}
                _base_port["port"] = int(port["container_port"])
                _base_port["protocol"] = port["protocol"]
                _base_port["service_alias"] = service_alias
                _base_port["service_id"] = service_id
                _options = {}
                for attr in upstream_attrsList:
                    if attr.container_port != int(port["container_port"]):
                        continue
                    _options[attr.attr_name] = attr.attr_value
                _base_port["options"] = _options
                base_ports.append(_base_port)

        # 处理envs
        env_items = self.sortList(env_attrsList.values("service_meta_type", "injection"))
        logger.debug("plugin.relation", "env items is {}".format(env_items))
        if len(env_items) > 0:
            for env in env_items:
                for attr in env_attrsList:
                    if env["injection"] == attr.injection == "auto":
                        auto_envs[attr.attr_name] = attr.attr_value
                    elif env["injection"] == attr.injection == "env":
                        _env = {}
                        _env["env_name"] = attr.attr_name
                        _env["env_value"] = attr.attr_value
                        normal_envs.append(_env)

        complex_envs["base_ports"] = base_ports
        complex_envs["base_services"] = base_services
        complex_envs["base_normal"] = {"option": auto_envs}
        logger.debug("plugin.relation", "complex json is {}".format(complex_envs))
        return complex_envs, normal_envs

    def updateALLTenantServicePluginAttr(self, config, plugin_id, service_id):
        downstream_list = []
        upstream_list = []
        envstream_list = []
        for stream in config:
            if stream.get("service_meta_type") == ConstKey.DOWNSTREAM_PORT:
                downstream_list.append(stream)
            elif stream.get("service_meta_type") == ConstKey.UPSTREAM_PORT:
                upstream_list.append(stream)
            elif stream.get("service_meta_type") == ConstKey.UNDEFINE:
                envstream_list.append(stream)
        self.UpdateSqlInDownStreamMeta(downstream_list, plugin_id, service_id)
        self.UpdateSqlInUpStreamMeta(upstream_list, plugin_id, service_id)
        self.UpdateSqlInENVMeta(envstream_list, plugin_id, service_id)

    def updateTenantServicePluginAttr(self, request):
        logger.debug("plugin.relation", "old attr is " + request.get("config_group[service_alias]", "") + ";"
                     + request.get("config_group[dest_service_alias]", "") + ";"
                     + request.get("plugin_id", None) + ";"
                     + request.get("config_group[service_meta_type]", None) + ";"
                     + str(request.get("config_group[port]", 0)) + ";"
                     + request.get("config_group[config][attr_name]", None))
        oldAttr = TenantServicePluginAttr.objects.get(
            service_alias=request.get("config_group[service_alias]", ""),
            dest_service_alias=request.get("config_group[dest_service_alias]", ""),
            plugin_id=request.get("plugin_id", None),
            service_meta_type=request.get("config_group[service_meta_type]", None),
            container_port=request.get("config_group[port]", 0),
            attr_name=request.get("config_group[config][attr_name]", None))
        oldAttr.attr_value = request.get("config_group[config][attr_value]", None)
        if not oldAttr.attr_value:
            oldAttr.attr_value = request.get("config_group[config][attr_default_value]", None)
        oldAttr.save()

    def create_plugin_build_version(self, region, plugin_id, tenant_id, user_id, update_info, build_version,
                                    build_status,
                                    min_memory, min_cpu, build_cmd="", image_tag="latest", code_version="master"):
        """创建插件版本信息"""
        plugin_build_version = PluginBuildVersion.objects.create(
            plugin_id=plugin_id,
            tenant_id=tenant_id,
            region=region,
            user_id=user_id,
            update_info=update_info,
            build_version=build_version,
            build_status=build_status,
            min_memory=min_memory,
            min_cpu=min_cpu,
            build_cmd=build_cmd,
            image_tag=image_tag,
            code_version=code_version
        )
        return plugin_build_version

    def calculate_cpu(self, region, memory):
        """根据内存和数据中心计算cpu"""
        min_cpu = int(memory) * 20 / 128
        if region == "ali-hz":
            min_cpu = min_cpu * 2
        return min_cpu

    def check_config(self, *config_group):
        if config_group:
            temp_list = []
            for config in config_group:
                injection = config["injection"]
                service_meta_type = config["service_meta_type"]
                if injection == "env":
                    if service_meta_type == "port" or service_meta_type == "downstream_port":
                        return False, u"基于上游端口或下游端口的配置只能使用主动发现"
                if service_meta_type in temp_list:
                    return False, u"配置组配置类型不能重复"
                else:
                    temp_list.append(service_meta_type)
            return True, u"检测成功"

    def check_group_config(self, service_meta_type, injection, config_groups):
        if injection == "env":
            if service_meta_type == ConstKey.UPSTREAM_PORT or service_meta_type == ConstKey.DOWNSTREAM_PORT:
                return False, u"基于上游端口或下游端口的配置只能使用主动发现"
        for config_group in config_groups:
            if config_group.service_meta_type == service_meta_type:
                return False, u"配置组配置类型不能重复"
        return True, u"检测成功"

    def create_config_group(self, plugin_id, build_version, config_group):
        """创建配置组信息"""

        pbvs = PluginBuildVersion.objects.filter(plugin_id=plugin_id, build_version=build_version)
        if not pbvs:
            logger.error("plugin id {0} and build version {1} is not found !".format(plugin_id, build_version))
            raise Exception("version not found ! ")

        plugin_config_meta_list = []
        config_items_list = []
        if config_group:
            for config in config_group:
                options = config["options"]
                plugin_config_meta = PluginConfigGroup(
                    plugin_id=plugin_id,
                    build_version=build_version,
                    config_name=config["config_name"],
                    service_meta_type=config["service_meta_type"],
                    injection=config["injection"]
                )
                plugin_config_meta_list.append(plugin_config_meta)

                for option in options:
                    config_item = PluginConfigItems(
                        plugin_id=plugin_id,
                        build_version=build_version,
                        service_meta_type=config["service_meta_type"],
                        attr_name=option["attr_name"],
                        attr_alt_value=option["attr_alt_value"],
                        attr_type=option.get("attr_type", "string"),
                        attr_default_value=option.get("attr_default_value", None),
                        is_change=option.get("is_change", False),
                        attr_info=option.get("attr_info", "")
                    )
                    config_items_list.append(config_item)
        self.bulk_create_plugin_config_group(plugin_config_meta_list)
        self.bulk_create_plugin_config_items(config_items_list)

    def update_plugin_version_by_unique_key(self, tenant, plugin_id, build_version, **params):
        """更新构建版本信息"""
        pbv = self.get_tenant_plugin_version_by_plugin_id_and_version(tenant, plugin_id, build_version)
        for k, v in params.items():
            setattr(pbv, k, v)
        pbv.save(update_fields=params.keys())
        return pbv

    def bulk_create_plugin_config_group(self, plugin_config_meta_list):
        """批量创建插件配置组信息"""
        PluginConfigGroup.objects.bulk_create(plugin_config_meta_list)

    def bulk_create_plugin_config_items(self, config_items_list):
        """批量创建插件配置项信息"""
        PluginConfigItems.objects.bulk_create(config_items_list)

    def get_plugin_config(self, tenant, plugin_id, build_version):
        """获取插件信息"""
        build_version_info = self.get_tenant_plugin_version_by_plugin_id_and_version(tenant, plugin_id,
                                                                                     build_version)
        data = {}
        data.update(model_to_dict(build_version_info))
        config_group = []
        config_groups = self.get_config_group_by_unique_key(plugin_id, build_version)
        for conf in config_groups:
            config_dict = model_to_dict(conf)
            items = self.get_config_items_by_id_metadata_and_version(conf.plugin_id, conf.build_version,
                                                                     conf.service_meta_type)
            options = [model_to_dict(item) for item in items]
            config_dict["options"] = options
            config_group.append(config_dict)
        data["config_group"] = config_group
        return data

    def get_config_group_by_unique_key(self, plugin_id, build_version):
        return PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version)

    def get_config_items_by_id_and_version(self, plugin_id, build_version):
        return PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version)

    def get_config_items_by_id_metadata_and_version(self, plugin_id, build_version, service_meta_type):
        return PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version,
                                                service_meta_type=service_meta_type)

    def delete_config_group_by_group_id_and_version(self, plugin_id, build_version):
        PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()
        PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()

    def roll_back_build(self, plugin_id, build_version):
        """删除原有数据"""
        PluginBuildVersion.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()
        PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()
        PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()

    def create_region_plugin(self, region, tenant, plugin_id):
        """创建region端插件信息"""
        tenant_plugin = self.get_tenant_plugin_by_plugin_id(tenant, plugin_id)
        plugin_data = {}
        plugin_data["build_model"] = tenant_plugin.build_source
        plugin_data["git_url"] = tenant_plugin.code_repo
        plugin_data["plugin_id"] = tenant_plugin.plugin_id
        plugin_data["plugin_info"] = tenant_plugin.desc
        plugin_data["plugin_model"] = CATEGORY_REGION_MAP.get(tenant_plugin.category, tenant_plugin.category)
        plugin_data["plugin_name"] = tenant_plugin.plugin_name
        plugin_data["tenant_id"] = tenant.tenant_id
        res, body = region_api.create_plugin(region, tenant.tenant_name, plugin_data)
        return res, body

    def build_plugin(self, region, tenant, event_id, plugin_id, build_version, origin=None):
        """构建插件"""
        plugin_build_version = self.get_tenant_plugin_version_by_plugin_id_and_version(tenant, plugin_id, build_version)
        plugin_base_info = self.get_tenant_plugin_by_plugin_id(tenant, plugin_id)
        create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        plugin_build_version.build_time = create_time
        plugin_build_version.save()
        build_data = {}
        build_data["build_version"] = build_version
        build_data["event_id"] = event_id
        build_data["info"] = plugin_build_version.update_info
        user = Users.objects.get(user_id=plugin_build_version.user_id)
        build_data["operator"] = user.nick_name
        build_data["plugin_cmd"] = plugin_build_version.build_cmd
        build_data["plugin_memory"] = plugin_build_version.min_memory
        build_data["plugin_cpu"] = self.calculate_cpu(region, plugin_build_version.min_memory)
        build_data["repo_url"] = plugin_build_version.code_version
        build_data["tenant_id"] = tenant.tenant_id
        build_data["build_image"] = plugin_base_info.image
        if origin == "local_market":
            plugin_from = "yb"
        elif origin == "market":
            plugin_from = "ys"
        else:
            plugin_from = None

        # build_data["plugin_from"] = "yb" if plugin_base_info.origin == "source_code" else "ys"
        build_data["plugin_from"] = plugin_from
        logger.debug("=====> build_data {0}".format(build_data))
        body = region_api.build_plugin(region, tenant.tenant_name, plugin_id, build_data)
        return body

    def copy_config_to_new_version(self, tenant, plugin_id, old_version):
        new_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        self.__copy_build_version_info(tenant, plugin_id, old_version, new_version)
        self.__copy_config_group(plugin_id, old_version, new_version)
        self.__copy_config_items(plugin_id, old_version, new_version)
        return plugin_id, new_version

    def __copy_build_version_info(self, tenant, plugin_id, old_version, new_version):
        old_build_version = self.get_tenant_plugin_version_by_plugin_id_and_version(tenant, plugin_id, old_version)
        old_dict = model_to_dict(old_build_version)
        old_dict["build_status"] = "unbuild"
        old_dict["event_id"] = ""
        # 剔除主键
        old_dict.pop("ID")
        pbv = PluginBuildVersion.objects.create(**old_dict)
        pbv.build_version = new_version
        pbv.save()
        return pbv

    def __copy_config_group(self, plugin_id, old_version, new_version):
        config_groups = self.get_config_group_by_unique_key(plugin_id, old_version)
        config_group_copy = []
        for config in config_groups:
            config_dict = model_to_dict(config)
            config_dict["build_version"] = new_version
            # 剔除主键
            config_dict.pop("ID")
            config_group_copy.append(PluginConfigGroup(**config_dict))
        self.bulk_create_plugin_config_group(config_group_copy)

    def __copy_config_items(self, plugin_id, old_version, new_version):
        config_items = self.get_config_items_by_id_and_version(plugin_id, old_version)
        config_items_copy = []
        for item in config_items:
            item_dict = model_to_dict(item)
            # 剔除主键
            item_dict.pop("ID")
            item_dict["build_version"] = new_version
            config_items_copy.append(PluginConfigItems(**item_dict))
        self.bulk_create_plugin_config_items(config_items_copy)

    def get_plugin_event_log(self, region, tenant, event_id, level):
        data = {"event_id": event_id, "level": level}
        body = region_api.get_plugin_event_log(region, tenant.tenant_name, data)
        return body["list"]

    def get_plugin_build_status(self, region, tenant, plugin_id, build_version):
        pbv = self.get_tenant_plugin_version_by_plugin_id_and_version(tenant, plugin_id, build_version)
        if pbv.build_status == "building":
            status = self.get_region_plugin_build_status(region, tenant.tenant_name, pbv.plugin_id, pbv.build_version)
            pbv.build_status = status
            pbv.save()
        return pbv

    def update_plugin_build_status(self, region, tenant):
        logger.debug("start thread to update build status")
        pbvs = PluginBuildVersion.objects.filter(region=region, tenant_id=tenant.tenant_id, build_status="building")
        for pbv in pbvs:
            status = self.get_region_plugin_build_status(region, tenant.tenant_name, pbv.plugin_id, pbv.build_version)
            pbv.build_status = status
            pbv.save()

    def get_region_plugin_build_status(self, region, tenant_name, plugin_id, build_version):
        try:
            body = region_api.get_build_status(region, tenant_name, plugin_id, build_version)
            status = body["bean"]["status"]
            rt_status = REGION_BUILD_STATUS_MAP[status]
        except region_api.CallApiError as e:
            if e.status == 404:
                rt_status = "unbuild"
            else:
                rt_status = "unknown"
        return rt_status

    def chargeSwtich(self, s):
        if type(s) is not bool:
            if "false" in s:
                s = False
            elif "true" in s:
                s = True
            else:
                s = True
        return s

    def is_plugin_version_can_build(self, plugin_id, plugin_version):
        pbvs = PluginBuildVersion.objects.get(plugin_id=plugin_id, plugin_version=plugin_version)
        return pbvs.plugin_version_status == "unfixed"

    def delete_build_version_by_id_and_version(self, region, tenant, plugin_id, build_version):
        region_api.delete_plugin_version(region, tenant.tenant_name, plugin_id, build_version)

        PluginBuildVersion.objects.filter(plugin_id=plugin_id, build_version=build_version).delete()
        self.delete_config_group_by_group_id_and_version(plugin_id, build_version)

    def get_service_plugin_relation_by_plugin_unique_key(self, plugin_id, build_version):
        tsprs = TenantServicePluginRelation.objects.filter(plugin_id=plugin_id, build_version=build_version)
        if tsprs:
            return tsprs
        return None

    def get_config_group_by_pk(self, pk):
        return PluginConfigGroup.objects.get(pk=pk)

    def delete_config_group_by_meta_type(self, plugin_id, build_version, service_meta_type):
        PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version,
                                         service_meta_type=service_meta_type).delete()
        PluginConfigGroup.objects.filter(plugin_id=plugin_id, build_version=build_version,
                                         service_meta_type=service_meta_type).delete()

    def update_config_group_by_pk(self, pk, config_name, service_meta_type, injection):
        pcg = PluginConfigGroup.objects.get(pk=pk)
        pcg.service_meta_type = service_meta_type
        pcg.injection = injection
        pcg.config_name = config_name
        pcg.save()

    def delete_config_items_by_meta_type(self, plugin_id, build_version, service_meta_type):
        PluginConfigItems.objects.filter(plugin_id=plugin_id, build_version=build_version,
                                         service_meta_type=service_meta_type).delete()

    def create_config_items(self, plugin_id, build_version, service_meta_type, *options):
        config_items_list = []
        for option in options:
            config_item = PluginConfigItems(
                plugin_id=plugin_id,
                build_version=build_version,
                service_meta_type=service_meta_type,
                attr_name=option["attr_name"],
                attr_alt_value=option["attr_alt_value"],
                attr_type=option.get("attr_type", "string"),
                attr_default_value=option.get("attr_default_value", None),
                is_change=option.get("is_change", False),
                attr_info=option.get("attr_info", "")
            )
            config_items_list.append(config_item)

        self.bulk_create_plugin_config_items(config_items_list)


class PluginShareInfoServie(object):
    def get_share_info_by_unique_key(self, share_id, share_version):
        tpsis = TenantPluginShareInfo.objects.filter(share_id=share_id, share_version=share_version)
        if tpsis:
            return tpsis[0]
        return None

    def create_share_info(self, tenant, user_id, plugin_base_info, plugin_build_version, share_version, image, config):
        share_id = make_uuid()

        share_info = TenantPluginShareInfo()
        share_info.share_id = share_id
        share_info.share_version = share_version
        share_info.origin_plugin_id = plugin_base_info.plugin_id
        share_info.tenant_id = tenant.tenant_id
        share_info.user_id = user_id
        share_info.desc = plugin_base_info.desc
        share_info.plugin_name = plugin_base_info.plugin_name
        share_info.plugin_alias = plugin_base_info.plugin_alias
        share_info.category = plugin_base_info.category
        share_info.image = image
        share_info.update_info = plugin_build_version.update_info
        share_info.min_memory = plugin_build_version.min_memory
        share_info.min_cpu = plugin_build_version.min_cpu
        share_info.build_cmd = plugin_build_version.build_cmd
        share_info.config = config

        share_info.save()
        return share_info
