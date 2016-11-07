# -*- coding: utf8 -*-
import logging
import uuid
import hashlib
import datetime
import json

from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse, JsonResponse

from cadmin.models.main import ConsoleSysConfig, ConsoleSysConfigAttr
from cadmin.utils import attrlist2json, is_number
from www.models import AppServiceImages
from www.models.service_publish import AppServiceImages
from www.views.base import CAdminView
from goodrain_web.custom_config import custom_config as custom_settings

logger = logging.getLogger('default')


class AdminViews(CAdminView):
    def get_media(self):
        media = super(AdminViews, self).get_media() + self.vendor('admin/css/jquery-ui.css',
                                                                  'admin/css/jquery-ui-timepicker-addon.css',
                                                                  'admin/js/jquery.cookie.js',
                                                                  'admin/js/common-scripts.js',
                                                                  'admin/js/jquery.dcjqaccordion.2.7.js',
                                                                  'admin/js/jquery.scrollTo.min.js',
                                                                  'admin/layer/layer.js', 'admin/js/jquery-ui.js',
                                                                  'admin/js/jquery-ui-timepicker-addon.js',
                                                                  'admin/js/jquery-ui-timepicker-addon-i18n.min.js',
                                                                  'admin/js/jquery-ui-sliderAccess.js')
        return media

    def init_context(self, context):
        context["config"] = "active"
        context["base_config"] = "active"

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        self.init_context(context)

        configs = ConsoleSysConfig.objects.all()
        context["config_list"] = list(configs)
        return TemplateResponse(self.request, "cadmin/config.html", context)


class ConfigDetailViews(CAdminView):
    def get_media(self):
        media = super(ConfigDetailViews, self).get_media() + self.vendor('admin/css/jquery-ui.css',
                                                                         'admin/css/jquery-ui-timepicker-addon.css',
                                                                         'admin/js/jquery.cookie.js',
                                                                         'admin/js/common-scripts.js',
                                                                         'admin/js/jquery.dcjqaccordion.2.7.js',
                                                                         'admin/js/jquery.scrollTo.min.js',
                                                                         'admin/layer/layer.js',
                                                                         'admin/js/jquery-ui.js',
                                                                         'admin/js/jquery-ui-timepicker-addon.js',
                                                                         'admin/js/jquery-ui-timepicker-addon-i18n.min.js',
                                                                         'admin/js/jquery-ui-sliderAccess.js')
        return media

    def init_context(self, context):
        context["config"] = "active"
        context["base_config"] = "active"

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        self.init_context(context)
        try:
            config_key = request.GET.get("config_key", None)
            config_id = ConsoleSysConfig.objects.get(key=config_key).ID
            config_attr_list = ConsoleSysConfigAttr.objects.filter(config_id=config_id)
            context["attr_list"] = list(config_attr_list)
            context["config_key"] = config_key
            context["config_id"] = config_id
        except ConsoleSysConfig.DoesNotExist:
            logger.error("consolesysconfig detail ", "config {0} is not exists, now create...".format(config_key))
        except Exception as e:
            logger.error(e)

        return TemplateResponse(self.request, "cadmin/edit.html", context)


class UpdateAttrViews(CAdminView):
    @never_cache
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            attr_id = request.POST.get("attr_id")
            attr_name = request.POST.get("attr_name")
            attr_val = request.POST.get("attr_val")
            attr_type = request.POST.get("attr_type")
            attr_desc = request.POST.get("attr_desc")

            if attr_type=='boolean':
                if attr_val.lower() not in ("true","false"):
                    return JsonResponse({"ok":False,"info":u"属性值和类型不匹配"})
            if attr_type=="float" or attr_type=="int":
                if not is_number(attr_val):
                    return JsonResponse({"ok":False,"info":u"属性值和类型不匹配"})

            config_attr = ConsoleSysConfigAttr.objects.get(ID=attr_id)
            if (config_attr.attr_name != attr_name or
                        config_attr.attr_val != attr_val or
                        config_attr.attr_type != attr_type or
                        config_attr.attr_desc != attr_desc):
                ConsoleSysConfigAttr.objects.filter(ID=attr_id).update(attr_name=attr_name, attr_val=attr_val,
                                                                       attr_type=attr_type, attr_desc=attr_desc)
                attr_list = ConsoleSysConfigAttr.objects.filter(config_id=config_attr.config_id)
                jsonstr = attrlist2json(attr_list)
                ConsoleSysConfig.objects.filter(ID=config_attr.config_id).update(value=jsonstr)

            data = {"ok": True,"info":u"操作成功"}


            # 更新缓存数据
            custom_settings.reload()
        except Exception as e:
            data = {"ok":False,"info":u"操作失败"}
            logger.error(e)

        return JsonResponse(data, status=200)


class ConfigLogoViews(CAdminView):
    def get_media(self):
        media = super(ConfigLogoViews, self).get_media() + self.vendor('admin/css/jquery-ui.css',
                                                                         'admin/css/jquery-ui-timepicker-addon.css',
                                                                         'admin/js/jquery.cookie.js',
                                                                         'admin/js/common-scripts.js',
                                                                         'admin/js/jquery.dcjqaccordion.2.7.js',
                                                                         'admin/js/jquery.scrollTo.min.js',
                                                                         'admin/layer/layer.js',
                                                                         'admin/js/jquery-ui.js',
                                                                         'admin/js/jquery-ui-timepicker-addon.js',
                                                                         'admin/js/jquery-ui-timepicker-addon-i18n.min.js',
                                                                         'admin/js/jquery-ui-sliderAccess.js')
        return media

    def init_context(self, context):
        context["config"] = "active"
        context["upload_page"]="active"

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        self.init_context(context)
        try:
            data =  AppServiceImages.objects.get(service_id="logo")
            context["data"] = data
        except Exception as e:
            logger.error(e)

        return TemplateResponse(self.request, "cadmin/upload.html", context)

class SpecificationSViews(CAdminView):
    def get_media(self):
        media = super(SpecificationSViews, self).get_media() + self.vendor('admin/css/jquery-ui.css',
                                                                           'admin/css/jquery-ui-timepicker-addon.css',
                                                                           'admin/js/jquery.cookie.js',
                                                                           'admin/js/common-scripts.js',
                                                                           'admin/js/jquery.dcjqaccordion.2.7.js',
                                                                           'admin/js/jquery.scrollTo.min.js',
                                                                           'admin/layer/layer.js',
                                                                           'admin/js/jquery-ui.js',
                                                                           'admin/js/jquery-ui-timepicker-addon.js',
                                                                           'admin/js/jquery-ui-timepicker-addon-i18n.min.js',
                                                                           'admin/js/jquery-ui-sliderAccess.js')
        return media

    def init_context(self, context):
        context["config"] = "active"
        context["info_page"]="active"

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        self.init_context(context)
        return TemplateResponse(self.request, "cadmin/info.html", context)