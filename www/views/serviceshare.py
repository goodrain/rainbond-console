# -*- coding: utf8 -*-
from django.template.response import TemplateResponse
from django import forms
from www.views import AuthedView, LeftSideBarMixin, BaseView
from www.service_http import RegionServiceApi
from www.models import *

import logging

logger = logging.getLogger('default')
regionClient = RegionServiceApi()


class ShareServiceStep1View(LeftSideBarMixin, AuthedView):
    """ 服务分享概览页面 """
    
    def get_context(self):
        context = super(ShareServiceStep1View, self).get_context()
        return context


class ShareServiceStep2View(LeftSideBarMixin, AuthedView):
    """服务分享step2:获取环境变量是否可修改"""
    
    def get_context(self):
        context = super(ShareServiceStep2View, self).get_context()
        return context
    
    def get(self, request, *args, **kwargs):
        # 获取服务的环境变量
        context = self.get_context()
        context["myAppStatus"] = "active"
        port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id) \
            .values_list('container_port', flat=True)
        env_list = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id) \
            .exclude(container_port__in=list(port_list)) \
            .values('ID', 'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        
        dep_num = TenantServiceRelation.objects.filter(service_id=self.service.service_id).count()
        if dep_num > 0:
            env_list = env_list.exclude(attr_name="GD_ADAPTER")
        
        env_ids = [str(x["ID"]) for x in list(env_list)]
        if len(env_ids) == 0:
            return self.redirect_to("/apps/{0}/{1}/share/step3".format(self.tenantName, self.serviceAlias))
        
        context["env_ids"] = ",".join(env_ids)
        context["env_list"] = list(env_list)
        # path param
        context["tenant_name"] = self.tenantName
        context["service_alias"] = self.serviceAlias
        context["tenantServiceInfo"] = self.service
        if TenantServicesPort.objects.filter(service_id=self.service.service_id, is_outer_service=True,
                                             protocol='http').exists():
            context["hasHttpServices"] = True
        # 返回页面
        return TemplateResponse(request,
                                'www/service/share_step_2.html',
                                context)
    
    def post(self, request, *args, **kwargs):
        # 服务的环境是否可修改存储
        post_data = request.POST.dict()
        env_ids = post_data.get('env_ids')
        logger.info("env_ids={}".format(env_ids))
        # clear old info
        AppServiceShareInfo.objects.filter(tenant_id=self.service.tenant_id,
                                           service_id=self.service.service_id).delete()
        if env_ids != "" and env_ids is not None:
            env_data = []
            tmp_id_list = env_ids.split(",")
            for tmp_id in tmp_id_list:
                is_change = post_data.get(tmp_id, "0")
                is_change = (is_change == "1")
                app_env = AppServiceShareInfo(tenant_id=self.service.tenant_id,
                                              service_id=self.service.service_id,
                                              tenant_env_id=int(tmp_id),
                                              is_change=is_change)
                env_data.append(app_env)
            # add new info
            if len(env_data) > 0:
                AppServiceShareInfo.objects.bulk_create(env_data)
        logger.debug(u'publish.service. now add publish service env ok')
        return self.redirect_to('/apps/{0}/{1}/share/step3'.format(self.tenantName, self.serviceAlias))


class ShareServiceStep3View(LeftSideBarMixin, AuthedView):
    """ 服务关系配置页面 """
    
    def get_context(self):
        context = super(ShareServiceStep3View, self).get_context()
        return context


class ShareServiceForm(forms.Form):
    """ 服务发布详情页form """
    app_alias = forms.CharField(help_text=u"应用名称")
    info = forms.CharField(required=False, help_text=u"一句话介绍")
    desc = forms.CharField(required=False, help_text=u"应用简介")
    category_first = forms.CharField(required=False, help_text=u"分类1")
    category_second = forms.CharField(required=False, help_text=u"分类2")
    category_third = forms.CharField(required=False, help_text=u"分类3")
    
    url_site = forms.CharField(required=False, help_text=u"网站url")
    url_source = forms.CharField(required=False, help_text=u"源码url")
    url_demo = forms.CharField(required=False, help_text=u"样例代码url")
    url_feedback = forms.CharField(required=False, help_text=u"反馈url")
    
    service_key = forms.CharField(help_text=u"服务发布key")
    app_version = forms.CharField(help_text=u"版本")
    release_note = forms.CharField(help_text=u"更新说明")
    is_outer = forms.BooleanField(required=False, initial=False, help_text=u"是否发布到云市")
    is_private = forms.BooleanField(required=False, initial=False, help_text=u"是否发布为私有应用")
    show_app = forms.BooleanField(required=False, initial=False, help_text=u"发布到云市后是否在云市展示")
    show_assistant = forms.BooleanField(required=False, initial=False, help_text=u"发布到云市后是否在云帮展示")


class ShareServiceImageForm(forms.Form):
    """服务截图上传form表单"""
    logo = forms.FileField(help_text=u"应用logo")
    service_id = forms.CharField(help_text=u"服务发布key")


class ShareServiceStep4View(LeftSideBarMixin, AuthedView):
    """分享设置套餐"""
    
    def get_context(self):
        context = super(ShareServiceStep4View, self).get_context()
        return context

    def _create_publish_event(self, info):
        
        try:
            import datetime
            event = ServiceEvent(event_id=make_uuid(), service_id=self.service.service_id,
                                 tenant_id=self.tenant.tenant_id, type="share-{0}".format(info),
                                 deploy_version=self.service.deploy_version,
                                 old_deploy_version=self.service.deploy_version,
                                 user_name=self.user.nick_name, start_time=datetime.datetime.now())
            event.save()
            self.event = event
            return event.event_id
        except Exception as e:
            self.event = None
            raise e
    
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
            event_id = self._create_publish_event("yb")
            oss_upload_task.update({"dest": "yb", "event_id": event_id})
            regionClient.send_task(self.service.service_region, 'app_slug', json.dumps(oss_upload_task))
            if app.is_outer:
                event_id = self._create_publish_event("ys")
                oss_upload_task.update({"dest": "ys", "event_id": event_id})
                regionClient.send_task(self.service.service_region, 'app_slug', json.dumps(oss_upload_task))
        except Exception as e:
            if self.event:
                self.event.message = u"生成发布事件错误，" + e.message
                self.event.final_status = "complete"
                self.event.status = "failure"
                self.event.save()
            logger.exception(e)
            raise e
    
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
            event_id = self._create_publish_event("yb")
            image_upload_task.update({"dest": "yb", "event_id": event_id})
            regionClient.send_task(self.service.service_region, 'app_image', json.dumps(image_upload_task))
            if app.is_outer:
                event_id = self._create_publish_event("ys")
                image_upload_task.update({"dest": "ys", "event_id": event_id})
                regionClient.send_task(self.service.service_region, 'app_image', json.dumps(image_upload_task))
        except Exception as e:
            if self.event:
                self.event.message = u"生成发布事件错误，" + e.message
                self.event.final_status = "complete"
                self.event.status = "failure"
                self.event.save()
            logger.exception(e)
            raise e


class ShareServiceStep5View(LeftSideBarMixin, AuthedView):
    """用户选择编辑或返回界面"""
    
    def get_context(self):
        context = super(ShareServiceStep5View, self).get_context()
        return context
    
    def get(self, request, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        context["myAppStatus"] = "active"
        context["tenantName"] = self.tenant.tenant_name
        context["serviceAlias"] = self.service.service_alias
        context["tenantServiceInfo"] = self.service
        return TemplateResponse(request, 'www/service/share_step_5.html', context)


class ShareServicePackageView(BaseView):
    """添加套餐接口"""
    
    def get_context(self):
        context = super(ShareServicePackageView, self).get_context()
        return context

