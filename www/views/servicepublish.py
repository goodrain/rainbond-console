# -*- coding: utf8 -*-
import json

from django import forms


from www.views import AuthedView, LeftSideBarMixin

from www.models import TenantServicesPort
from www.service_http import RegionServiceApi

import logging

logger = logging.getLogger('default')
regionClient = RegionServiceApi()


# 复制数据属性
def copy_properties(copy_from, to, field_list):
    for field in field_list:
        if hasattr(to, field) and hasattr(copy_from, field):
            setattr(to, field, getattr(copy_from, field))
    return to


class PublishServiceDetailView(LeftSideBarMixin, AuthedView):
    """ 服务信息配置页面 """
    def get_context(self):
        context = super(PublishServiceDetailView, self).get_context()
        return context
 
    def get_media(self):
        media = super(PublishServiceDetailView, self).get_media() + self.vendor(
            'www/assets/jquery-easy-pie-chart/jquery.easy-pie-chart.css',
            'www/css/owl.carousel.css', 'www/css/goodrainstyle.css', 'www/css/style.css',
            'www/css/bootstrap-switch.min.css', 'www/css/bootstrap-editable.css',
            'www/css/style-responsive.css', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js',
            'www/js/jquery.scrollTo.min.js', 'www/js/jquery.cookie.js', 'www/js/gr/app_publish.js', 'www/js/validator.min.js'
             )
        return media


class PublishServiceView(LeftSideBarMixin, AuthedView):
    """ 1, 服务发布统一按照新增处理
        2, 所有的服务数据均从tenant_service获取
        3, 动态配置app_version,最后统一更新为用户自定义version
    """
    def get_context(self):
        context = super(PublishServiceView, self).get_context()
        return context

    def get_media(self):
        media = super(PublishServiceView, self).get_media() + \
                self.vendor('www/css/goodrainstyle.css',
                            'www/js/jquery.cookie.js',
                            'www/js/validator.min.js',
                            'www/js/gr/app_publish.js')
        return media
    
    def getServicePort(self, service_id):
        port_list = TenantServicesPort.objects.filter(service_id=service_id).values_list('container_port', flat=True)
        return list(port_list)

    def _create_publish_event(self, info):
        template = {
            "user_id": self.user.nick_name,
            "tenant_id": self.service.tenant_id,
            "service_id": self.service.service_id,
            "type": "publish",
            "desc": info + u"应用发布中...",
            "show": True,
        }
        try:
            body = regionClient.create_event(self.service.service_region, json.dumps(template))
            return body.event_id
        except Exception as e:
            logger.exception("service.publish", e)
            return None

    def upload_slug(self, app):
        """ 上传slug包 """
        oss_upload_task = {
            "service_key": app.service_key,
            "app_version": app.app_version,
            "service_id": self.service.service_id,
            "deploy_version": self.service.deploy_version,
            "tenant_id": self.service.tenant_id,
            "action": "create_new_version",
            "is_outer": app.is_outer,
        }
        try:
            # 生成发布事件
            event_id = self._create_publish_event(u"云帮")
            oss_upload_task.update({"dest" : "yb", "event_id" : event_id})
            regionClient.send_task(self.service.service_region, 'app_slug', json.dumps(oss_upload_task))
            if app.is_outer:
                event_id = self._create_publish_event(u"云市")
                oss_upload_task.update({"dest" : "ys", "event_id" : event_id})
                regionClient.send_task(self.service.service_region, 'app_slug', json.dumps(oss_upload_task))
        except Exception as e:
            logger.error("service.publish",
                         "upload_slug for {0}({1}), but an error occurred".format(app.service_key, app.app_version))
            logger.exception("service.publish", e)

    def upload_image(self, app):
        """ 上传image镜像 """
        image_upload_task = {
            "service_key": app.service_key,
            "app_version": app.app_version,
            "action": "create_new_version",
            "image": self.service.image,
            "is_outer": app.is_outer,
        }
        try:
            event_id = self._create_publish_event(u"云帮")
            image_upload_task.update({"dest":"yb", "event_id" : event_id})
            regionClient.send_task(self.service.service_region, 'app_image', json.dumps(image_upload_task))
            if app.is_outer:
                event_id = self._create_publish_event(u"云市")
                image_upload_task.update({"dest":"ys", "event_id" : event_id})
                regionClient.send_task(self.service.service_region, 'app_image', json.dumps(image_upload_task))
        except Exception as e:
            logger.error("service.publish",
                         "upload_image for {0}({1}), but an error occurred".format(app.service_key, app.app_version))
            logger.exception("service.publish", e)


class ServiceDetailForm(forms.Form):
    """ 服务发布详情页form """
    service_id = forms.CharField()
    deploy_version = forms.CharField()
    service_key = forms.CharField()
    app_version = forms.CharField()
    app_alias = forms.CharField()
    logo = forms.FileField(required=False)
    info = forms.CharField(required=False)
    desc = forms.CharField(required=False)
    is_outer = forms.BooleanField(required=False, initial=False)
    is_private = forms.BooleanField(required=False, initial=False)
    show_app = forms.BooleanField(required=False, initial=False, help_text=u"发布到云市后是否在云市展示")
    show_assistant = forms.BooleanField(required=False, initial=False, help_text=u"发布到云市后是否在云帮展示")
    is_init_accout = forms.BooleanField(required=False, initial=False)
    app_service_type = forms.CharField(required=False)
