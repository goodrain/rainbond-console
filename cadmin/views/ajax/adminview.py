# -*- coding: utf8 -*-
import datetime
import logging
import re
import json

from django.http import JsonResponse

from cadmin.models.main import ConsoleSysConfig, ConsoleSysConfigAttr
from cadmin.utils import attrlist2json, is_number
from www.models import AppServiceImages
from www.views.base import CAdminView
from goodrain_web.custom_config import custom_config as custom_settings

logger = logging.getLogger('default')


class ConfigViews(CAdminView):
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')
            if action == "add_config":
                config_key = request.POST.get('config_key', None)
                config_desc = request.POST.get('config_desc', "")
                config_type = request.POST.get('config_type')
                if config_key is None:
                    data["success"] = False
                    data["info"] = "key 不能为空"
                    return JsonResponse(data, status=500)
                if not re.match(r'^[A-Z][A-Z0-9_]*$', config_key):
                    return JsonResponse({"success": False, "code": 400, "info": u"配置输入参数不合法"})
                if ConsoleSysConfig.objects.filter(key=config_key).exists():
                    return JsonResponse({"success": False, "code": 400, "info": u"配置名已存在"})
                create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ConsoleSysConfig.objects.create(key=config_key, type=config_type, desc=config_desc, create_time=create_time)
                data["success"] = True
                data["info"] = "添加成功"
            elif action == "del_config":
                config_key = request.POST.get('config_key', None)
                if config_key is None:
                    data["success"] = False
                    data["info"] = "删除失败"
                    return JsonResponse(data, status=500)
                if ConsoleSysConfig.objects.filter(key=config_key).exists():
                    config = ConsoleSysConfig.objects.get(key=config_key)
                    ConsoleSysConfigAttr.objects.filter(config_id=config.ID).delete()
                    config.delete()
                data["success"] = True
                data["info"] = "删除成功"

            # 更新缓存数据
            custom_settings.reload()
        except Exception as e:
            logger.exception(e)
            data["success"] = False
            data["info"] = "操作失败"
        return JsonResponse(data, status=200)


class ConfigAttributeViews(CAdminView):
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')
            if action == "add_attribute":
                attr_name = request.POST.get('attr_name', None)
                attr_val = request.POST.get('attr_val', None)
                attr_type = request.POST.get('attr_type', "string")
                attr_desc = request.POST.get('attr_desc', None)
                config_id = request.POST.get('config_id')

                if attr_type=='boolean':
                    if attr_val.lower() not in ("true","false"):
                        return JsonResponse({"success":False,"info":u"属性值和类型不匹配"})
                if attr_type=="float" or attr_type=="int":
                    if not is_number(attr_val):
                        return JsonResponse({"success":False,"info":u"属性值和类型不匹配"})

                if attr_name is None or attr_val is None:
                    data["success"] = False
                    data["info"] = "属性不能为空"
                    return JsonResponse(data, status=500)

                if not re.match(r'^[a-zA-Z0-9_]+', attr_name):
                    return JsonResponse({"success": False, "code": 400, "info": u"配置输入参数不合法"})

                if ConsoleSysConfigAttr.objects.filter(attr_name=attr_name).exists():
                    return JsonResponse({"success": False, "code": 400, "info": u"属性名已存在"})
                ConsoleSysConfigAttr.objects.create(attr_name=attr_name, attr_val=attr_val, attr_type=attr_type,
                                                    attr_desc=attr_desc, config_id=config_id)
                attr_list = ConsoleSysConfigAttr.objects.filter(config_id=config_id)
                jsonstr = attrlist2json(attr_list)
                ConsoleSysConfig.objects.filter(ID=config_id).update(value=jsonstr)
                data["success"] = True
                data["info"] = "添加成功"
            elif action == "del_attribute":
                config_id = request.POST.get("config_id")
                attr_id = request.POST.get("attr_id")
                ConsoleSysConfigAttr.objects.filter(ID=attr_id).delete()

                attr_list = ConsoleSysConfigAttr.objects.filter(config_id=config_id)
                jsonstr = attrlist2json(attr_list)
                ConsoleSysConfig.objects.filter(ID=config_id).update(value=jsonstr)

                data["success"] = True
                data["info"] = "删除成功"

            # 更新缓存数据
            custom_settings.reload()
        except Exception as e:
            logger.exception(e)
            data["success"] = False
            data["info"] = "操作失败"
        return JsonResponse(data, status=200)


class ConfigDetailViews(CAdminView):
    def post(self, request, *args, **kwargs):
        data = {}
        try:
            config_key = request.POST.get("config_key")
            res_json = ConsoleSysConfig.objects.get(key=config_key).value
            data["success"] = True
            data["info"] = res_json
        except Exception as e:
            logger.exception(e)
            data["success"] = False
            data["info"] = "操作失败"
        return JsonResponse(data, status=200)


class SingAttrAddOrModifyViews(CAdminView):
    def post(self, request, *args, **kwargs):
        data={}
        try:
            config_key = request.POST.get("current_config_key")
            config_value = request.POST.get("config_value")

            ConsoleSysConfig.objects.filter(key=config_key).update(value=config_value)
            data["success"] = True
            data["info"]="操作成功";
            # 更新缓存数据
            custom_settings.reload()
        except Exception as e:
            logger.exception(e)
            data["success"] = False
            data["info"] = "操作失败"
        return JsonResponse(data, status=200)


class UploadLogoViews(CAdminView):
    def post(self, request, *args, **kwargs):
        logo = request.FILES['logo']
        service_id = "logo"
        # 更新图片路径
        try:
            count = AppServiceImages.objects.filter(service_id=service_id).count()
            if count > 1:
                AppServiceImages.objects.filter(service_id=service_id).delete()
                count = 0
            if count == 0:
                image_info = AppServiceImages()
                image_info.service_id = service_id
                image_info.logo = logo
            else:
                image_info = AppServiceImages.objects.get(service_id=service_id)
                image_info.logo = logo
            image_info.save()
            image_url = AppServiceImages.objects.get(service_id="logo").logo
            create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if ConsoleSysConfig.objects.filter(key="LOGO").exists():
                ConsoleSysConfig.objects.filter(key="LOGO").update(value = image_url)
            else:
                ConsoleSysConfig.objects.create(key="LOGO", type="string", value = image_url, desc="logo", create_time=create_time)
                # 更新缓存数据
            custom_settings.reload()
        except Exception as e:
            logger.error(e)
        data = {"success": True, "code": 200, "pic": image_info.logo.name}
        return JsonResponse(data, status=200)
