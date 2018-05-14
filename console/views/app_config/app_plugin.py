# -*- coding: utf8 -*-
"""
  Created on 18/3/5.
"""
from www.decorator import perm_required
from www.apiclient.regionapi import RegionInvokeApi
from console.views.app_config.base import AppBaseView
from console.services.app_config.plugin_service import app_plugin_service
from console.services.plugin import plugin_service, plugin_version_service
from www.utils.return_message import general_message, error_message
import logging
from rest_framework.response import Response
from www.services import plugin_svc
from www.models import ConstKey, HasNoDownStreamService
import json

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class APPPluginsView(AppBaseView):
    @perm_required('view_service')
    def get(self, request, *args, **kwargs):
        """
        获取应用可用的插件列表
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: category
              description: 插件类型 性能分析（analysis）| 网络治理（net_manage）
              required: true
              type: string
              paramType: query

        """
        try:
            category = request.GET.get("category", "")
            if category:
                if category not in ("analysis", "net_manage"):
                    return Response(general_message(400, "param can only be analysis or net_manage", "参数错误"),
                                    status=400)
            installed_plugins, not_install_plugins = app_plugin_service.get_plugins_by_service_id(
                self.service.service_region, self.tenant.tenant_id, self.service.service_id, category)
            bean = {"installed_plugins": installed_plugins, "not_install_plugins": not_install_plugins}
            result = general_message(200, "success", "查询成功", bean=bean)
        except Exception as e:
            logger.exception(e)
            result = general_message(500, e.message, "查询失败")
        return Response(result, status=result["code"])


class APPPluginInstallView(AppBaseView):
    def useDefaultAttr(self, plugin_id, build_version, tag):
        metaTypeList = plugin_svc.get_service_meta_type(plugin_id, build_version)
        logger.debug("plugin.relation", "metatype List is {}".format(len(metaTypeList)))
        attrsList = []
        for meta_info in metaTypeList:
            attr_list = plugin_svc.get_env_attr_by_service_meta_type(
                plugin_id=plugin_id, build_version=build_version, service_meta_type=meta_info.service_meta_type)
            logger.debug("plugin.relation", "attr_list is {}".format(len(attr_list)))
            configList = []
            for attrItem in attr_list:
                config = {}
                config["attr_name"] = attrItem.attr_name
                config["attr_type"] = attrItem.attr_type
                config["attr_default_value"] = attrItem.attr_default_value
                # TODO: 可选参数 alternative
                config["attr_alt_value"] = attrItem.attr_alt_value
                config["is_change"] = attrItem.is_change
                config["attr_default_value"] = attrItem.attr_default_value
                config["attr_value"] = attrItem.attr_default_value
                config["attr_info"] = attrItem.attr_info
                configList.append(config)
            logger.debug("plugin.relation", "configList is {}".format(configList))
            pieceList = plugin_svc.getMetaBaseInfo(
                self.tenant.tenant_id, self.service.service_id, self.service.service_alias, plugin_id, build_version,
                meta_info, configList, tag)
            logger.debug("plugin.relation", "pieceList is {}".format(pieceList))
            attrsList.extend(pieceList)
        logger.debug("plugin.relation", "attrsList is {}".format(attrsList))
        return attrsList

    @perm_required('manage_service_plugin')
    def post(self, request, plugin_id, *args, **kwargs):
        """
        应用安装插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 插件版本
              required: true
              type: string
              paramType: form
        """
        result = {}
        build_version = request.data.get("build_version", None)

        try:
            if not plugin_id:
                return Response(general_message(400, "params error","参数错误"),status=400)
            if not build_version:
                plugin_version = plugin_version_service.get_newest_usable_plugin_version(plugin_id)
                build_version = plugin_version.build_version

            # 1. 建立关联关系
            # 2. 生成默认的配置发送给前端
            # 3. 生成默认配置存储至console数据库
            # 4. 生成默认配置发送给region
            # >> 进行关联
            body_relation = {}
            body_relation["plugin_id"] = plugin_id
            body_relation["switch"] = True
            body_relation["version_id"] = build_version
            # 1)发送关联请求
            try:
                res, resultBody = region_api.pluginServiceRelation(
                    self.service.service_region, self.tenant.tenant_name, self.service.service_alias, body_relation)
                if res.status == 200:
                    plugin_svc.add_service_plugin_relation(
                        service_id=self.service.service_id, plugin_id=plugin_id, build_version=build_version)
            except region_api.CallApiError as e:
                if e.status == 400:
                    result = general_message(400, "plugin already related", u"该类型插件已关联，请先卸载同类插件")
                    return Response(result, status=400)
                else:
                    result = general_message(int(e.status), "region install error", "安装插件失败")
                    return Response(result, status=result["code"])
            # 2)发送配置请求
            result["config_group"] = self.useDefaultAttr(plugin_id, build_version, "post")
            complex, normal = plugin_svc.createAttrsJsonForRegion(self.service.service_id, self.service.service_alias,
                                                                  plugin_id)
            config_envs = {}
            config_envs["normal_envs"] = normal
            config_envs["complex_envs"] = complex
            body = {}
            body["tenant_id"] = self.tenant.tenant_id
            body["service_id"] = self.service.service_id
            body["config_envs"] = config_envs
            res, resultBody = region_api.postPluginAttr(self.service.service_region, self.tenant.tenant_name,
                                                        self.service.service_alias, plugin_id, body)
            if res.status == 200:
                result = general_message(200, "success", "操作成功", bean=result["config_group"])
                return Response(result, result["code"])
            else:
                result = general_message(int(res.status), "add plugin attr error", "操作失败")
                return Response(result, status=200)
        except HasNoDownStreamService as e:
            try:
                plugin_svc.del_service_plugin_relation_and_attrs(self.service.service_id, plugin_id)
                region_api.delPluginServiceRelation(
                    self.service.service_region, self.tenant.tenant_name, plugin_id, self.service.service_alias)
            except Exception, e:
                pass
            result = general_message(400, "havs no downstream services", u'缺少关联应用，不能使用该类型插件')
            logger.exception(e)
            return Response(result, status=400)
        except Exception, e:
            try:
                plugin_svc.del_service_plugin_relation_and_attrs(self.service.service_id, plugin_id)
                region_api.delPluginServiceRelation(
                    self.service.service_region, self.tenant.tenant_name, plugin_id, self.service.service_alias)
            except Exception, e:
                logger.exception(e)
                pass
            result = general_message(500, "service relate plugin error", u'关联插件失败')
            logger.exception(e)
            return Response(result, status=500)

    @perm_required('manage_service_plugin')
    def delete(self, request, plugin_id, *args, **kwargs):
        """
        应用卸载插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path  
        """
        try:
            plugin_svc.del_service_plugin_relation_and_attrs(self.service.service_id, plugin_id)
            res, resultBody = region_api.delPluginServiceRelation(
                self.service.service_region, self.tenant.tenant_name, plugin_id, self.service.service_alias)
            if res.status == 200:
                result = general_message(200, "success", "插件删除成功")
                return Response(result, status=200)
            else:
                result = general_message(int(res.status), "success", "插件删除成功")
                return Response(result, status=200)
        except Exception, e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=200)


class APPPluginOpenView(AppBaseView):
    # @perm_required('manage_service')
    # def post(self, request, plugin_id, *args, **kwargs):
    #     """
    #     应用启用插件
    #     ---
    #     parameters:
    #         - name: tenantName
    #           description: 租户名
    #           required: true
    #           type: string
    #           paramType: path
    #         - name: serviceAlias
    #           description: 服务别名
    #           required: true
    #           type: string
    #           paramType: path
    #         - name: plugin_id
    #           description: 插件ID
    #           required: true
    #           type: string
    #           paramType: path
    #     """
    #     pass
    #
    # @perm_required('manage_service')
    # def delete(self, request, plugin_id, *args, **kwargs):
    #     """
    #     应用停用插件
    #     ---
    #     parameters:
    #         - name: tenantName
    #           description: 租户名
    #           required: true
    #           type: string
    #           paramType: path
    #         - name: serviceAlias
    #           description: 服务别名
    #           required: true
    #           type: string
    #           paramType: path
    #         - name: plugin_id
    #           description: 插件ID
    #           required: true
    #           type: string
    #           paramType: path
    #     """
    #     pass

    @perm_required('manage_service_plugin')
    def put(self, request, plugin_id, *args, **kwargs):
        """
        启停用应用插件
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: is_switch
              description: 插件启停状态
              required: true
              type: boolean
              paramType: form
        """
        try:
            if not plugin_id:
                return Response(general_message(400, "params error", "参数异常"), status=400)
            switch = request.data.get("is_switch", True)
            switch = plugin_svc.chargeSwtich(switch)
            relations = plugin_svc.get_tenant_service_plugin_relation_by_plugin(self.service.service_id, plugin_id)
            if relations > 0:
                build_version = relations[0].build_version
            else:
                return Response(general_message(404, "params error", "未找到关联插件的构建版本"), status=400)
            body_relation = {}
            body_relation["plugin_id"] = plugin_id
            body_relation["switch"] = switch
            body_relation["version_id"] = build_version
            logger.debug("plugin.relation", "is_switch body is {}".format(body_relation))
            res, resultBody = region_api.updatePluginServiceRelation(
                self.service.service_region, self.tenant.tenant_name, self.service.service_alias, body_relation)
            if res.status == 200:
                plugin_svc.update_service_plugin_relation(self.service.service_id, plugin_id, build_version, switch)
                return Response(general_message(200, "success", "操作成功"), status=200)
            else:
                result = general_message(500, "update plugin status error", "系统异常")
                return Response(result, result["code"])
        except Exception, e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])


class APPPluginConfigView(AppBaseView):
    def useDefaultAttr(self, plugin_id, build_version, tag):
        metaTypeList = plugin_svc.get_service_meta_type(plugin_id, build_version)
        logger.debug("plugin.relation", "metatype List is {}".format(len(metaTypeList)))
        attrsList = []
        for meta_info in metaTypeList:
            attr_list = plugin_svc.get_env_attr_by_service_meta_type(
                plugin_id=plugin_id, build_version=build_version, service_meta_type=meta_info.service_meta_type)
            logger.debug("plugin.relation", "attr_list is {}".format(len(attr_list)))
            configList = []
            for attrItem in attr_list:
                config = {}
                config["attr_name"] = attrItem.attr_name
                config["attr_type"] = attrItem.attr_type
                config["attr_default_value"] = attrItem.attr_default_value
                # TODO: 可选参数 alternative
                config["attr_alt_value"] = attrItem.attr_alt_value
                config["is_change"] = attrItem.is_change
                config["attr_default_value"] = attrItem.attr_default_value
                config["attr_value"] = attrItem.attr_default_value
                config["attr_info"] = attrItem.attr_info
                configList.append(config)
            logger.debug("plugin.relation", "configList is {}".format(configList))
            pieceList = plugin_svc.getMetaBaseInfo(
                self.tenant.tenant_id, self.service.service_id, self.service.service_alias, plugin_id, build_version,
                meta_info, configList, tag)
            logger.debug("plugin.relation", "pieceList is {}".format(pieceList))
            attrsList.extend(pieceList)
        logger.debug("plugin.relation", "attrsList is {}".format(attrsList))
        return attrsList

    @perm_required('view_service')
    def get(self, request, plugin_id, *args, **kwargs):
        """
        应用插件查看配置
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: build_version
              description: 插件版本
              required: true
              type: string
              paramType: path
        """
        build_version = request.GET.get("build_version", None)
        if not plugin_id or not build_version:
            logger.error("plugin.relation", u'参数错误，plugin_id and version_id')
            return Response(general_message(400, "params error", "参数错误"), status=400)
        result = {}
        try:
            result["config_group"] = self.useDefaultAttr(plugin_id, build_version, "get")
            build_relations = plugin_svc.get_tenant_service_plugin_relation_by_plugin(self.service.service_id,
                                                                                      plugin_id)
            version_info = plugin_svc.getPluginMetaType(plugin_id, build_version)
            bl = {}
            bl["create_time"] = build_relations[0].create_time
            bl["build_info"] = version_info.update_info
            bl["memory"] = version_info.min_memory
            result["build_version"] = bl
            result["success"] = True
            result["code"] = 200
            result["msg"] = u"操作成功"
            result = general_message(200, "success", u"操作成功", result["build_version"], result["config_group"])
            return Response(result, status=200)
        except HasNoDownStreamService as e:
            logger.error("service has no dependence services operation suspend")
            return Response(general_message(409, "service has no dependence", "应用没有依赖其他应用，配置无效"),status=409)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, result["code"])

    @perm_required('manage_service_plugin')
    def put(self, request, plugin_id, *args, **kwargs):
        """
        应用插件更新
        ---
        parameters:
            - name: tenantName
              description: 租户名
              required: true
              type: string
              paramType: path
            - name: serviceAlias
              description: 服务别名
              required: true
              type: string
              paramType: path
            - name: plugin_id
              description: 插件ID
              required: true
              type: string
              paramType: path
            - name: body
              description: 配置内容
              required: true
              type: string
              paramType: body

        """
        try:
            logger.debug("update service plugin config ")
            config = json.loads(request.body)
            logger.debug("====> {0}".format(config))
            # config_group = config.get("config_group", [])
            config_group = config
            if not config_group:
                return Response(general_message(400, "params error", "参数配置不可为空"), status=400)

            plugin_svc.del_service_plugin_attrs(self.service.service_id, plugin_id)
            plugin_svc.updateALLTenantServicePluginAttr(config_group, plugin_id, self.service.service_id)
            complex, normal = plugin_svc.createAttrsJsonForRegion(self.service.service_id, self.service.service_alias,
                                                                  plugin_id)
            config_envs = {}
            config_envs["normal_envs"] = normal
            config_envs["complex_envs"] = complex
            logger.debug("plugin.relation", "--< config_envs is {}".format(config_envs))
            body = {}
            body["tenant_id"] = self.tenant.tenant_id
            body["service_id"] = self.service.service_id
            body["config_envs"] = config_envs
            res, resultBody = region_api.putPluginAttr(self.service.service_region, self.tenant.tenant_name,
                                                       self.service.service_alias,
                                                       plugin_id, body)
            result = general_message(200, "config error", "配置成功")
            return Response(result, result["code"])
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, result["code"])
