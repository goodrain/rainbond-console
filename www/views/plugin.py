# -*- coding: utf8 -*-
import logging

from django.http import HttpResponse
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from django import forms

from goodrain_web.errors import CallApiError
from www.utils.return_message import general_message,error_message

from www.decorator import perm_required
from www.utils.crypt import make_uuid
from www.views import AuthedView, LeftSideBarMixin
from www.services import plugin_svc
import json
import datetime
from django.conf import settings

logger = logging.getLogger('default')


class AllPluginView(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(AllPluginView, self).get_media() + self.vendor(
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        try:
            context["pluginStatus"] = "active"
            result = plugin_svc.get_newest_plugin_version_info(self.response_region, self.tenant)
            context["plugins_info"] = result

            plugin_origin_key = ["82ce36bfd4044931adaa484ed8e75c12", "e003ce85b65d477896ee99798c3d8a54"]
            region = self.response_region
            for p in plugin_origin_key:
                p_info = plugin_svc.get_tenant_plugin_by_origin_key(region, self.tenant, p)
                if not p_info:
                    context["trans_plugins"] = "need"
                    break
            logger.debug("context is {}".format(context))
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/plugin/plugin_my.html", context)


class CreatePluginView(LeftSideBarMixin, AuthedView):
    def get_media(self):
        media = super(CreatePluginView, self).get_media() + self.vendor(
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        try:
            context["pluginStatus"] = "active"
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/plugin/create_plugin.html", context)

    @never_cache
    @perm_required('tenant.tenant_access')
    def post(self, request, *args, **kwargs):
        try:
            logger.debug("plugin.create", "create plugin")
            plugin_form = PluginCreateForm(request.POST)
            if plugin_form.is_valid():
                logger.debug("plugin.create", "post_data is {0}".format(plugin_form))
                plugin_alias = plugin_form.cleaned_data["plugin_alias"]
                build_source = plugin_form.cleaned_data["build_source"]
                min_memory = plugin_form.cleaned_data["min_memory"]
                category = plugin_form.cleaned_data["category"]
                build_cmd = plugin_form.cleaned_data["build_cmd"]
                code_repo = ""
                image = ""
                image_tag = ""
                code_version = ""
                if build_source == "dockerfile":
                    code_repo = plugin_form.cleaned_data["code_repo"]
                    code_version = plugin_form.cleaned_data.get("code_version", None)
                if build_source == "image":
                    image = plugin_form.cleaned_data["image"]
                    image_and_tag = image.split(":")
                    if len(image_and_tag) > 1:
                        image = image_and_tag[0]
                        image_tag = image_and_tag[1]
                    else:
                        image = image_and_tag[0]
                        image_tag = "latest"
                region = self.response_region

                desc = plugin_form.cleaned_data.get("desc", "")

                plugin_id, build_version = plugin_svc.init_plugin(self.tenant, self.user.user_id,
                                                                  region, desc,
                                                                  plugin_alias,
                                                                  category, build_source,
                                                                  "unbuild", image, code_repo, int(min_memory),
                                                                  build_cmd, image_tag,
                                                                  code_version)
                # 数据中心创建插件
                plugin_svc.create_region_plugin(self.response_region, self.tenant, plugin_id)
                return self.redirect_to(
                    "/plugins/{0}/{1}/config?build_version={2}".format(self.tenant.tenant_name, plugin_id,
                                                                       build_version))
            else:
                logger.error('plugin.create', "form valid failed: {}".format(plugin_form.errors))
                return HttpResponse("参数异常{0}".format(plugin_form.errors), status=403)

        except Exception as e:
            logger.exception("plugin.create", "create plugin failed!")
            logger.exception(e)
            return HttpResponse("系统异常", status=500)


class PluginConfigView(LeftSideBarMixin, AuthedView):
    """插件配置"""

    def get_ws_url(self, default_url, ws_type):
        if default_url != "auto":
            return "{0}/{1}".format(default_url, ws_type)
        host = self.request.META.get('HTTP_HOST').split(':')[0]
        return "ws://{0}:6060/{1}".format(host, ws_type)

    def get_media(self):
        media = super(PluginConfigView, self).get_media() + self.vendor(
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css',
            'www/js/jquery.cookie.js', 'www/js/service.js', 'www/js/common-scripts.js',
            'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js')
        return media

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, plugin_id, *args, **kwargs):
        context = self.get_context()
        try:
            context["pluginStatus"] = "active"
            build_version = request.GET.get("build_version", None)
            context["plugin_id"] = plugin_id
            base_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, plugin_id)
            if not base_info:
                return HttpResponse("插件不存在", status=404)
            build_version_info = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, plugin_id,
                                                                                               build_version)
            context["base_info"] = base_info
            context["build_version_info"] = build_version_info
            context["web_socket_url"] = self.get_ws_url(settings.EVENT_WEBSOCKET_URL[self.response_region], "event_log")
            logger.debug(context["web_socket_url"])
        except Exception as e:
            logger.exception(e)
        return TemplateResponse(self.request, "www/plugin/config_plugin.html", context)


class ManageConfigView(LeftSideBarMixin, AuthedView):

    def get_ws_url(self, default_url, ws_type):
        if default_url != "auto":
            return "{0}/{1}".format(default_url, ws_type)
        host = self.request.META.get('HTTP_HOST').split(':')[0]
        return "ws://{0}:6060/{1}".format(host, ws_type)

    @never_cache
    @perm_required('tenant.tenant_access')
    def get(self, request, plugin_id, *args, **kwargs):
        result = {}
        try:
            # 获取插件最新的配置信息
            build_version = request.GET.get("build_version", None)
            base_info = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, plugin_id)
            if not base_info:
                return JsonResponse({"msg": "插件不存在"}, status=404)
            if not build_version:
                pbv = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, plugin_id)
                build_version = pbv.build_version

            data = plugin_svc.get_plugin_config(self.tenant, plugin_id, build_version)
            web_socket_url = self.get_ws_url(settings.EVENT_WEBSOCKET_URL[self.response_region], "event_log")
            data["web_socket_url"] = web_socket_url
            result = general_message(200, "success","查询成功",bean=data)
        except Exception as e:
            result = error_message()
        return JsonResponse(data=result, status=result["code"])

    @never_cache
    @perm_required('tenant.tenant_access')
    def post(self, request, plugin_id, *args, **kwargs):
        result = {}
        build_version = None
        try:
            config = json.loads(request.body)
            min_memory = config["min_memory"]
            build_version = config["build_version"]
            config_group = config['config_group']
            update_info = config['update_info']
            build_cmd = config["build_cmd"]
            image_tag = config.get("image_tag", None)
            code_version = config.get("code_version", None)
            if config_group:
                is_success, msg = plugin_svc.check_config(*config_group)
                if not is_success:
                    result["status"] = "failure"
                    result["msg"] = msg
                    return JsonResponse(result)
            plugin = plugin_svc.get_tenant_plugin_by_plugin_id(self.tenant, plugin_id)
            min_cpu = plugin_svc.calculate_cpu(self.response_region, int(min_memory))
            pbv = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, plugin_id, build_version)

            if pbv.build_status == "unbuild":
                # 删除原有配置项目
                plugin_svc.delete_config_group_by_group_id_and_version(plugin_id, build_version)
                # 重新创建新配置
                plugin_svc.create_config_group(plugin_id, build_version, config_group)
                # 更新参数
                update_params = {"min_memory": min_memory, "build_cmd": build_cmd, "update_info": update_info}
                plugin_svc.update_plugin_version_by_unique_key(self.tenant, plugin_id, build_version, **update_params)
                build_version = pbv.build_version
            else:
                # 重新创建新的数据
                new_version = make_uuid()[:6] + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                if plugin.build_source == "dockerfile":
                    code_version = config.get("code_version", "master")
                if plugin.build_source == "image":
                    image_tag = config.get("image", "lastest")
                new_pbv = plugin_svc.create_plugin_build_version(self.response_region, pbv.plugin_id, pbv.tenant_id, self.user.user_id,
                                                                 update_info,
                                                                 new_version, "unbuild", min_memory, min_cpu, build_cmd,
                                                                 image_tag, code_version)

                plugin_svc.create_config_group(plugin_id, new_pbv.build_version, config_group)
                build_version = new_version
            bean = {"plugin_id":plugin_id,"build_version":build_version}
            result = general_message(200,"success","查询成功",bean=bean)

        except Exception as e:
            logger.exception(e)
            result = error_message()
        return JsonResponse(result,status=result["code"])


class BuildPluginView(LeftSideBarMixin, AuthedView):
    """
    插件构建
    """

    @never_cache
    @perm_required('tenant.tenant_access')
    def post(self, request, plugin_id, *args, **kwargs):
        new_version = None
        result = {}
        try:
            build_version = request.POST.get("build_version", None)
            newest_build_version = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, plugin_id,
                                                                                                 build_version)
            if newest_build_version.build_status == "building":
                result = general_message(403, "success", "构建中，请稍后再试")
                return JsonResponse(data=result, status=403)
            event_id = make_uuid()
            if newest_build_version.build_status != "unbuild":
                # 拷贝原有配置项
                plugin_id, new_version = plugin_svc.copy_config_to_new_version(self.tenant, plugin_id,
                                                                               newest_build_version.build_version)
                pbv = plugin_svc.get_tenant_plugin_version_by_plugin_id_and_version(self.tenant, plugin_id, new_version)
                pbv.event_id = event_id
                pbv.save()
                try:
                    plugin_svc.build_plugin(self.response_region, self.tenant, event_id, plugin_id, new_version)
                except CallApiError as e:
                    logger.exception(e)
                    if e.status == 404:
                        newest_build_version.build_status = "unbuild"
                        newest_build_version.save()
                    else:
                        newest_build_version.build_status = "build_fail"
                        newest_build_version.save()
                    raise Exception("invoke region build error")
                rt_pbv = pbv.to_dict()
            else:
                try:
                    plugin_svc.build_plugin(self.response_region, self.tenant,event_id, plugin_id,
                                            newest_build_version.build_version)
                except CallApiError as e:
                    logger.exception(e)
                    if e.status == 404:
                        newest_build_version.build_status = "unbuild"
                        newest_build_version.save()
                    else:
                        newest_build_version.build_status = "build_fail"
                        newest_build_version.save()
                    raise Exception("invoke region build error")

                newest_build_version.build_status = "building"
                newest_build_version.event_id = event_id
                newest_build_version.save()
                rt_pbv = newest_build_version.to_dict()
            result = general_message(200, "success", "操作成功", bean=rt_pbv)
            return JsonResponse(data=result, status=200)
        except Exception as e:
            result = error_message()
            # if new_version:
            #     plugin_svc.roll_back_build(plugin_id, new_version)
            return JsonResponse(data=result, status=500)


class PluginCreateForm(forms.Form):
    """插件创建表单详情"""
    plugin_alias = forms.CharField(help_text=u"插件名称")
    build_source = forms.CharField(help_text=u"构建来源")
    image = forms.CharField(required=False, initial="", help_text=u"镜像地址")
    code_repo = forms.CharField(required=False, initial="", help_text=u"代码仓库地址")
    code_version = forms.CharField(required=False, initial="", help_text=u"代码版本")
    category = forms.CharField(required=True, help_text=u"插件类型")
    min_memory = forms.IntegerField(required=True, help_text=u"最小内存")
    desc = forms.CharField(required=False, help_text=u"插件描述")
    build_cmd = forms.CharField(required=False, help_text=u"插件运行命令")
