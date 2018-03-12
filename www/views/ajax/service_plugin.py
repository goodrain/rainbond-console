# -*- coding: utf8 -*-

from django.http.response import JsonResponse, Http404
import logging
from www.models import ConstKey, HasNoDownStreamService
from www.views import AuthedView, LeftSideBarMixin
from django.views.decorators.cache import never_cache
from www.decorator import perm_required
from www.services import plugin_svc
from www.apiclient.regionapi import RegionInvokeApi
from django.http import QueryDict
from www.utils.return_message import oldResultSuitGeneralMessage, general_message
from django.forms import model_to_dict
import json

logger = logging.getLogger('default')
region_api = RegionInvokeApi()

class PluginServiceRelation(LeftSideBarMixin, AuthedView):

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
                config["attr_name"]= attrItem.attr_name
                config["attr_type"]= attrItem.attr_type
                config["attr_default_value"]= attrItem.attr_default_value
                #TODO: 可选参数 alternative
                config["attr_alt_value"] = attrItem.attr_alt_value
                config["is_change"]= attrItem.is_change
                config["attr_default_value"] = attrItem.attr_default_value
                config["attr_value"] = attrItem.attr_default_value
                config["attr_info"] = attrItem.attr_info
                configList.append(config)
            logger.debug("plugin.relation", "configList is {}".format(configList))
            pieceList = plugin_svc.getMetaBaseInfo(
                    self.tenant.tenant_id, self.service.service_id, self.serviceAlias, plugin_id, build_version, meta_info, configList, tag)
            logger.debug("plugin.relation", "pieceList is {}".format(pieceList))
            attrsList.extend(pieceList)
        logger.debug("plugin.relation", "attrsList is {}".format(attrsList))
        return attrsList

    @never_cache
    @perm_required('tenant.tenant_access')
    def post(self, request, *args, **kwargs):
        """安装插件"""
        result = {}
        plugin_id = request.POST.get("plugin_id", None)
        build_version = request.POST.get("build_version", None)
        if not plugin_id or not build_version:
            logger.error("plugin.relation", u'参数错误，plugin_id and version_id')
            data = {"success":False, "code":405, 'msg':u'参数错误'}
            result = oldResultSuitGeneralMessage(data, "params error", "")
            return JsonResponse(result, status=200)
        logger.debug("plugin.relation", "plugin_id is {0}, build_version is {1}".format(plugin_id, build_version))
        try:
            #1. 建立关联关系
            #2. 生成默认的配置发送给前端
            #3. 生成默认配置存储至console数据库
            #4. 生成默认配置发送给region
            # >> 进行关联
            body_relation = {}
            body_relation["plugin_id"] = plugin_id
            body_relation["switch"]  = True
            body_relation["version_id"] = build_version
            # 1)发送关联请求
            try:
                res, resultBody = region_api.pluginServiceRelation(
                        self.response_region, self.tenant.tenant_name, self.serviceAlias, body_relation)
                if res.status == 200:
                    plugin_svc.add_service_plugin_relation(
                        service_id=self.service.service_id, plugin_id=plugin_id,build_version=build_version)
                pass
            except region_api.CallApiError as e:
                if e.status == 400:
                    result["success"] = False
                    result["code"] = 400
                    result["msg"] = u"该类型插件已关联，请先卸载同类插件"
                    result = oldResultSuitGeneralMessage(result, "relation already exist", "")
                    return JsonResponse(result, status=200)
                else:
                    result["success"] = False
                    result["code"] = e.status
                    result['msg'] = u"安装插件失败"
                    result = oldResultSuitGeneralMessage(result, "add relation error", "")
                    return JsonResponse(result, status=200)
            # 2)发送配置请求
            result["config_group"] = self.useDefaultAttr(plugin_id, build_version, "post")
            complex, normal = plugin_svc.createAttrsJsonForRegion(self.service.service_id, self.serviceAlias, plugin_id)
            config_envs = {}
            config_envs["normal_envs"] = normal
            config_envs["complex_envs"] = complex
            body = {}
            body["tenant_id"] = self.tenant.tenant_id
            body["service_id"] = self.service.service_id
            body["config_envs"] = config_envs
            res, resultBody = region_api.postPluginAttr(self.response_region, self.tenant.tenant_name, self.serviceAlias, plugin_id, body)
            if res.status == 200:
                result["success"] = True
                result["code"] = 200
                result["msg"] = u"操作成功"
                result = oldResultSuitGeneralMessage(result, "success", result["config_group"])
                return JsonResponse(result, status=200)
            else:
                result["success"] = False
                result["code"] = res.status
                result['msg'] = resultBody
                result = oldResultSuitGeneralMessage(result, "add plugin attr error", "")
                return JsonResponse(result, status=200)
        except HasNoDownStreamService as e:
            try:
                plugin_svc.del_service_plugin_relation_and_attrs(self.service.service_id, plugin_id)
                region_api.delPluginServiceRelation(
                    self.response_region, self.tenant.tenant_name, plugin_id, self.serviceAlias)
            except Exception, e:
                pass
            result["success"] = False
            result['code']=400
            result['msg']=u'缺少依赖应用，不能使用该类型插件'
            result = oldResultSuitGeneralMessage(result, "havs no downstream services", "")
            logger.error("plugin.relation", u'缺少关联应用，不能使用该类型插件')
            logger.exception("plugin.relation", e)
            return JsonResponse(result, status=200)
        except Exception, e:
            try:
                plugin_svc.del_service_plugin_relation_and_attrs(self.service.service_id, plugin_id)
                region_api.delPluginServiceRelation(
                    self.response_region, self.tenant.tenant_name, plugin_id, self.serviceAlias)
            except Exception, e:
                pass
            result["success"] = False
            result['code']=500
            result['msg']=u'关联插件失败'
            result = oldResultSuitGeneralMessage(result, "get plugin attr error", "")
            logger.error("plugin.relation", u'关联插件失败')
            logger.exception("plugin.relation", e)
            return JsonResponse(result, status=200)

    @never_cache
    @perm_required('tenant.tenant_access')
    def put(self, request, *args, **kwargs):
        """更新插件到最新版本"""
        result = {}
        config = QueryDict(request.body)
        logger.debug("plugin.relation", "in PluginServiceRelation put method params is {}".format(config))
        plugin_id = config.get("plugin_id", None)
        build_version = config.get("build_version", "newest")
        switch = config.get("switch", True)
        switch = plugin_svc.chargeSwtich(switch)
        if not plugin_id or not build_version:
            logger.error("plugin.relation", u'参数错误，plugin_id and version_id')
            data = {"success":False, "code":400, 'msg':u'参数错误'}
            result = oldResultSuitGeneralMessage(data, "params error", "")
            return JsonResponse(result, status=200)
        try:
            body_relation = {}
            body_relation["plugin_id"] = plugin_id
            body_relation["switch"] = switch
            versionList = plugin_svc.get_tenant_plugin_newest_versions(self.response_region, self.tenant, plugin_id)
            if versionList > 0:
                body_relation["version_id"] = versionList[0].build_version
                build_version = versionList[0].build_version
                logger.debug("plugin.relation", "body_relation is {0}, build_version is {1}".format(body_relation, build_version))
            else:
                result["success"] = False
                result["code"] = 404
                result["msg"] = u"未找到插件的最新版本"
                result = oldResultSuitGeneralMessage(result, "cant find newest plugin", "")
                return JsonResponse(result, status=200)
            res, resultBody = region_api.delPluginServiceRelation(
                    self.response_region, self.tenant.tenant_name, plugin_id, self.serviceAlias)
            if res.status == 200:
                pass
            else:
                result["success"] = False
                result["code"] = res.status
                result['msg'] = resultBody
                result = oldResultSuitGeneralMessage(result, "update plugin relation error", "")
                return JsonResponse(result, status=res.status)
            res, resultBody = region_api.pluginServiceRelation(
                    self.response_region, self.tenant.tenant_name, self.serviceAlias, body_relation)
            if res.status == 200:
                plugin_svc.update_service_plugin_relation(self.service.service_id, plugin_id, build_version, switch)
                pass
            else:
                result["success"] = False
                result["code"] = res.status
                result['msg'] = resultBody
                result = oldResultSuitGeneralMessage(result, "update plugin relation error", "")
                return JsonResponse(result, status=res.status)
            complex, normal = plugin_svc.createAttrsJsonForRegion(self.service.service_id, self.serviceAlias, plugin_id)
            config_envs = {}
            config_envs["normal_envs"] = normal
            config_envs["complex_envs"] = complex
            body = {}
            body["tenant_id"] = self.tenant.tenant_id
            body["service_id"] = self.service.service_id
            body["config_envs"] = config_envs
            res, resultBody = region_api.postPluginAttr(self.response_region, self.tenant.tenant_name, self.serviceAlias, plugin_id, body)
            if res.status == 200:
                result["config_group"] = self.useDefaultAttr(plugin_id, build_version, "post")
                result["success"] = True
                result["code"] = 200
                result["msg"] = u"操作成功"
                result["bean"] = {"build_version": model_to_dict(versionList[0])}
                result = general_message(200, "success", u"操作成功", result["bean"], result["config_group"])
                return JsonResponse(result, status=200)
            else:
                result["success"] = False
                result["code"] = res.status
                result['msg'] = resultBody
                result = oldResultSuitGeneralMessage(result, "update plugin relation error",  "")
                return JsonResponse(result, status=200)
        except Exception, e:
            result["success"] = False
            result['code']=500
            result['msg']=u'更新插件关联失败'
            logger.error("plugin.relation", u'更新插件关联失败')
            logger.exception("plugin.relation", e)
            result = oldResultSuitGeneralMessage(result, "update plugin relation error", "")
            return JsonResponse(result, status=200)

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        """获取插件信息"""
        plugin_id = request.GET.get("plugin_id")
        build_version = request.GET.get("build_version")
        if not plugin_id or not build_version:
            logger.error("plugin.relation", u'参数错误，plugin_id and version_id')
            data = {"success":False, "code":405, 'msg':u'参数错误'}
            data = oldResultSuitGeneralMessage(data, "params error", "")
            return JsonResponse(data, status=200)
        result = {}
        result["config_group"] = self.useDefaultAttr(plugin_id, build_version, "get")
        build_relations = plugin_svc.get_tenant_service_plugin_relation_by_plugin(self.service.service_id, plugin_id)
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
        return JsonResponse(result, status=200)

    @never_cache
    @perm_required('tenant.tenant_access')
    def delete(self, request, *args, **kwargs):
        """删除插件"""
        result = {}
        config = QueryDict(request.body)
        logger.debug("plugin.relation", "in PluginServiceRelation delete method params is {}".format(config))
        plugin_id = config.get("plugin_id", None)
        if not plugin_id:
            logger.error("plugin.relation", u'参数错误，plugin_id')
            data = {"success":False, "code":400, 'msg':u'参数错误'}
            result = oldResultSuitGeneralMessage(data, "params error", "")
            return JsonResponse(result, status=200)
        try:
            plugin_svc.del_service_plugin_relation_and_attrs(self.service.service_id, plugin_id)
            res, resultBody = region_api.delPluginServiceRelation(
                    self.response_region, self.tenant.tenant_name, plugin_id, self.serviceAlias)
            if res.status == 200:
                result["success"] = True
                result["code"] = 200
                result["msg"] = u"操作成功"
                result = oldResultSuitGeneralMessage(result, "success", "")
                return JsonResponse(result, status=200)
            else:
                result["success"] = False
                result["code"] = res.status
                result['msg'] = resultBody
                result = oldResultSuitGeneralMessage(result, "delete plugin relation error", "")
                return JsonResponse(result, status=200)
        except Exception, e:
            result["success"] = False
            result['code']=500
            result['msg']=u'删除应用与插件的绑定关系失败'
            logger.error("plugin.relation", u'删除应用与插件的绑定关系失败')
            logger.exception("plugin.relation", e)
            result = oldResultSuitGeneralMessage(result, "delete plugin relation error", "")
            return JsonResponse(result, status=200)

class PluginServiceComplexAttr(LeftSideBarMixin, AuthedView):

    @never_cache
    @perm_required('tenant.tenant_access')
    def post(self, request, *args, **kwargs):
        pass

    @never_cache
    @perm_required('tenant.tenant_access')
    def put(self, request, *args, **kwargs):
        """更新插件配置"""
        result = {}
        config = json.loads(request.body)
        logger.debug("plugin.relation", "in PluginServiceComplexAttr put method params is {}".format(config))
        plugin_id = config.get("plugin_id", None)
        service_id = config.get("service_id", None)
        try:
            config_group = config.get("config_group", [])
            if len(config_group) == 0:
                result["success"] = False
                result["code"] = 400
                result['msg'] = "参数配置不可为空"
                result = oldResultSuitGeneralMessage(result, "params canot be null", "")
                return JsonResponse(result, status=200)
            plugin_svc.del_service_plugin_attrs(self.service.service_id, plugin_id)
            plugin_svc.updateALLTenantServicePluginAttr(config_group, plugin_id, self.service.service_id)
            complex, normal = plugin_svc.createAttrsJsonForRegion(self.service.service_id, self.serviceAlias, plugin_id)
            config_envs = {}
            config_envs["normal_envs"] = normal
            config_envs["complex_envs"] = complex
            logger.debug("plugin.relation", "--< config_envs is {}".format(config_envs))
            body = {}
            body["tenant_id"] = self.tenant.tenant_id
            body["service_id"] = self.service.service_id
            body["config_envs"] = config_envs
            res, resultBody = region_api.putPluginAttr(self.response_region, self.tenant.tenant_name, self.serviceAlias, plugin_id, body)
            if res.status == 200:
                result["success"] = True
                result["code"] = 200
                result["msg"] = u"操作成功"
                result = oldResultSuitGeneralMessage(result, "success", "")
                return JsonResponse(result, status=200)
            else:
                result["success"] = False
                result["code"] = res.status
                result['msg'] = resultBody
                result = oldResultSuitGeneralMessage(result, "add plugin attr error", "")
                return JsonResponse(result, status=200)

        except Exception, e:
            logger.error("plugin.relation", e)
            result["success"] = False
            result['code']=500
            result['msg']=u'更新插件配置失败'
            logger.error("plugin.relation", u'更新插件配置失败')
            logger.exception("plugin.relation", e)
            result = oldResultSuitGeneralMessage(result, "update plugin attr error", "")
            return JsonResponse(result, status=200)

class PluginServiceSwitch(LeftSideBarMixin, AuthedView):

    @never_cache
    @perm_required('tenant.tenant_access')
    def put(self, request, *args, **kwargs):
        """插件启停"""
        result = {}
        config = QueryDict(request.body)
        logger.debug("plugin.relation", "in PluginServiceRelation put method params is {}".format(config))
        try:
            plugin_id = config.get("plugin_id", None)
            switch = config.get("is_switch", True)
            switch = plugin_svc.chargeSwtich(switch)
            relations = plugin_svc.get_tenant_service_plugin_relation_by_plugin(self.service.service_id, plugin_id)
            if relations > 0:
                build_version = relations[0].build_version
            else:
                result["success"] = False
                result["code"] = 404
                result['msg'] = u"未找到关联插件的构建版本"
                result = oldResultSuitGeneralMessage(result, "success", "")
                return JsonResponse(result, status=200)
            body_relation = {}
            body_relation["plugin_id"] = plugin_id
            body_relation["switch"] = switch
            body_relation["version_id"] = build_version
            logger.debug("plugin.relation", "is_switch body is {}".format(body_relation))
            res, resultBody = region_api.updatePluginServiceRelation(
                        self.response_region, self.tenant.tenant_name, self.serviceAlias, body_relation)
            if res.status == 200:
                plugin_svc.update_service_plugin_relation(self.service.service_id, plugin_id, build_version, switch)
                result["success"] = True
                result["code"] = 200
                result['msg'] = u"操作成功"
                result = oldResultSuitGeneralMessage(result, "success", "")
                return JsonResponse(result, status=200)
            else:
                result["success"] = False
                result["code"] = res.status
                result['msg'] = resultBody
                result = oldResultSuitGeneralMessage(result, "update plugin status error", "")
                return JsonResponse(result, status=200)
        except Exception, e:
            logger.error("plugin.relation", e)
            result["success"] = False
            result["code"]= 500
            result["msg"] = u"操作失败"
            result = oldResultSuitGeneralMessage(result, "update plugin status error", "")
            return JsonResponse(result, status=200)

