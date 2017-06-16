# -*- coding: utf8 -*-
import json
from django.template.response import TemplateResponse
from django.http.response import HttpResponse, JsonResponse
from django.db.models import Q
from django import forms, http
from django.conf import settings

from www.views import AuthedView, LeftSideBarMixin, BaseView
from www.decorator import perm_required
from www.service_http import RegionServiceApi
from www.utils.crypt import make_uuid
from www.servicetype import ServiceType
from www.utils import sn
from www.models import *

import logging

logger = logging.getLogger('default')
regionClient = RegionServiceApi()


class ShareServiceStep1View(LeftSideBarMixin, AuthedView):
    """ 服务分享概览页面 """
    
    def get_context(self):
        context = super(ShareServiceStep1View, self).get_context()
        return context
    
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["myAppStatus"] = "active"
        # 端口信息
        port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id). \
            values('container_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        context["port_list"] = list(port_list)
        # 环境变量
        used_port = [x["container_port"] for x in port_list]
        env_list = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id) \
            .exclude(container_port__in=used_port) \
            .exclude(attr_name="GD_ADAPTER") \
            .values('container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        context["env_list"] = list(env_list)
        # 持久化目录
        result_list = []
        if self.service.category == "application":
            volume_list = TenantServiceVolume.objects.filter(service_id=self.service.service_id)
            for volume in list(volume_list):
                tmp_path = volume.volume_path
                if tmp_path:
                    volume.volume_path = tmp_path.replace("/app/", "", 1)
                result_list.append(volume)
        context["volume_list"] = result_list
        # 依赖应用
        dep_service_ids = TenantServiceRelation.objects.filter(service_id=self.service.service_id).values(
            "dep_service_id")
        dep_service_list = TenantServiceInfo.objects.filter(service_id__in=dep_service_ids) \
            .values("service_key", "version", "service_alias", "service_type", "service_cname")
        context["dep_service_list"] = dep_service_list
        # 检查依赖服务是否已经发布
        context["dep_status"] = True
        if len(dep_service_list) > 0:
            for dep_service in list(dep_service_list):
                if dep_service["service_key"] == "application":
                    context["dep_service_name"] = dep_service["service_cname"]
                    context["dep_status"] = False
                    break
                count = AppService.objects.filter(service_key=dep_service["service_key"],
                                                  app_version=dep_service["version"]).count()
                if count == 0:
                    context["dep_status"] = False
                    context["dep_service_name"] = dep_service["service_cname"]
                    break
        
        # 内存、节点
        context["memory"] = self.service.min_memory
        context["node"] = self.service.min_node
        #
        context["tenant_name"] = self.tenantName
        context["service_alias"] = self.serviceAlias
        context["tenantServiceInfo"] = self.service
        if TenantServicesPort.objects.filter(service_id=self.service.service_id, is_outer_service=True,
                                             protocol='http').exists():
            context["hasHttpServices"] = True
        # 检查是否打开对外端口
        context["have_outer"] = False
        for tmp_port in list(port_list):
            if tmp_port.get("is_outer_service"):
                context["have_outer"] = True
                break
        # 返回页面
        return TemplateResponse(request,
                                'www/service/share_step_1.html',
                                context)


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
    
    def get(self, request, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        context["myAppStatus"] = "active"
        app = {
            "tenant_id": self.service.tenant_id,
            "service_id": self.service.service_id,
            "app_alias": self.service.service_alias,
            "app_cname": self.service.service_cname,
            "desc": self.service.desc,
            # "info": "",
            # "logo": "",
            # "category_first": 0,
            # "category_second": 0,
            # "category_third": 0,
            # "url_site": "",
            # "url_source": "",
            # "url_demo": "",
            # "url_feedback": "",
            # "app_version": "",
            # "release_note": "",
            # "is_outer": False,
            "service_key": make_uuid(self.serviceAlias),
        }
        # 获取之前发布的服务
        pre_app = AppService.objects.filter(service_id=self.service.service_id).order_by('-ID')[:1]
        if len(pre_app) == 1:
            first_app = list(pre_app)[0]
            app["app_alias"] = first_app.app_alias
            app["desc"] = first_app.desc
            app["info"] = first_app.info
            app["logo"] = first_app.logo
            # if first_app.show_category:
            #     first, second, third = first_app.show_category.split(",")
            #     app["category_first"] = first
            #     app["category_second"] = second
            #     app["category_third"] = third
            
            try:
                extend_info = AppServiceExtend.objects.get(service_key=first_app.service_key,
                                                           app_version=first_app.app_version)
                app["url_site"] = extend_info.url_site
                app["url_source"] = extend_info.url_source
                app["url_demo"] = extend_info.url_demo
                app["url_feedback"] = extend_info.url_feedback
                app["release_note"] = extend_info.release_note
            except AppServiceExtend.DoesNotExist:
                logger.error("[share service] extend info query error!")
            
            app["service_key"] = first_app.service_key
            app["app_version"] = first_app.app_version
            app["is_outer"] = first_app.is_outer
            app["is_private"] = first_app.status == "private"
            app["show_app"] = first_app.show_app
            app["show_assistant"] = first_app.show_assistant
        
        context["data"] = app
        # path param
        context["tenant_name"] = self.tenantName
        context["service_alias"] = self.serviceAlias
        state = request.GET.get("state")
        if state is not None:
            context["state"] = state
        context["tenantServiceInfo"] = self.service
        if TenantServicesPort.objects.filter(service_id=self.service.service_id, is_outer_service=True,
                                             protocol='http').exists():
            context["hasHttpServices"] = True
        # 返回页面
        return TemplateResponse(request,
                                'www/service/share_step_3.html',
                                context)
    
    # form提交.
    def post(self, request, *args, **kwargs):
        # 获取form表单
        form_data = ShareServiceForm(request.POST, request.FILES)
        if not form_data.is_valid():
            return self.redirect_to('/apps/{0}/{1}/share/step3?state={2}'.format(self.tenantName, self.serviceAlias, 1))
        # 服务基础信息
        service_key = form_data.cleaned_data['service_key']
        app_version = form_data.cleaned_data['app_version']
        
        # 获取服务基本信息
        url_site = form_data.cleaned_data.get('url_site', '')
        url_source = form_data.cleaned_data.get('url_source', '')
        url_demo = form_data.cleaned_data.get('url_demo', '')
        url_feedback = form_data.cleaned_data.get('url_feedback', '')
        release_note = form_data.cleaned_data.get('release_note', '')
        # 判断是否需要重新添加
        count = AppServiceExtend.objects.filter(service_key=service_key, app_version=app_version).count()
        if count == 0:
            extend_info = AppServiceExtend(service_key=service_key,
                                           app_version=app_version,
                                           url_site=url_site,
                                           url_source=url_source,
                                           url_demo=url_demo,
                                           url_feedback=url_feedback,
                                           release_note=release_note.strip())
            extend_info.save()
        else:
            AppServiceExtend.objects.filter(service_key=service_key, app_version=app_version) \
                .update(url_site=url_site,
                        url_source=url_source,
                        url_demo=url_demo,
                        url_feedback=url_feedback,
                        release_note=release_note.strip())
        # 基础信息
        app_alias = form_data.cleaned_data['app_alias']
        logo = None
        try:
            image = AppServiceImages.objects.get(service_id=self.service.service_id)
            logo = image.logo
        except AppServiceImages.DoesNotExist:
            pass
        
        info = form_data.cleaned_data.get('info', '')
        desc = form_data.cleaned_data.get('desc', '')
        category_first = form_data.cleaned_data['category_first']
        category_second = form_data.cleaned_data['category_second']
        category_third = form_data.cleaned_data['category_third']
        is_outer = form_data.cleaned_data.get('is_outer', False)
        is_private = form_data.cleaned_data.get('is_private', False)
        # 如果发布到云市,就不能为私有云帮
        if is_outer:
            is_private = False
        show_app = form_data.cleaned_data.get('show_app', False)
        show_assistant = form_data.cleaned_data.get('show_assistant', False)
        logger.debug("{0}:{1}:{2}".format(is_outer, show_app, show_assistant))
        # count = AppService.objects.filter(service_key=service_key, app_version=app_version).count()
        # if count == 0:
        try:
            app = AppService.objects.get(service_key=service_key, app_version=app_version)
            app.app_alias = app_alias
            if logo is not None:
                app.logo = logo
            app.info = info
            app.desc = desc
            app.show_category = '{},{},{}'.format(category_first, category_second, category_third)
            app.is_outer = is_outer
            app.show_app = show_app
            app.show_assistant = show_assistant
        except AppService.DoesNotExist:
            namespace = sn.instance.username
            if self.service.language == "docker":
                namespace = sn.instance.cloud_assistant
            app = AppService(
                tenant_id=self.service.tenant_id,
                service_id=self.service.service_id,
                service_key=service_key,
                app_version=app_version,
                app_alias=app_alias,
                creater=self.user.pk,
                info=info,
                desc=desc,
                status='',
                category="app_publish",
                is_service=self.service.is_service,
                is_web_service=self.service.is_web_service,
                image=self.service.image,
                namespace=namespace,
                slug='',
                extend_method=self.service.extend_method,
                cmd=self.service.cmd,
                env=self.service.env,
                min_node=self.service.min_node,
                min_cpu=self.service.min_cpu,
                min_memory=self.service.min_memory,
                inner_port=self.service.inner_port,
                volume_mount_path=self.service.volume_mount_path,
                service_type='application',
                is_init_accout=False,
                show_category='{},{},{}'.format(category_first, category_second, category_third),
                is_base=False,
                is_outer=is_outer,
                publisher=self.user.email,
                show_app=show_app,
                show_assistant=show_assistant,
                is_ok=0)
            if logo is not None:
                app.logo = logo
            if app.is_slug():
                app.slug = '/app_publish/{0}/{1}.tgz'.format(app.service_key, app.app_version)
        # save
        app.dest_yb = False
        app.dest_ys = False
        if is_private:
            app.status = "private"
        app.save()
        # 保存port
        # port 1 delete all old info
        AppServicePort.objects.filter(service_key=service_key, app_version=app_version).delete()
        # query new port
        port_list = TenantServicesPort.objects.filter(tenant_id=self.service.tenant_id,
                                                      service_id=self.service.service_id) \
            .values('container_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        port_data = []
        for port in list(port_list):
            app_port = AppServicePort(service_key=service_key,
                                      app_version=app_version,
                                      container_port=port["container_port"],
                                      protocol=port["protocol"],
                                      port_alias=port["port_alias"],
                                      is_inner_service=port["is_inner_service"],
                                      is_outer_service=port["is_outer_service"])
            port_data.append(app_port)
        if len(port_data) > 0:
            logger.debug(len(port_data))
            AppServicePort.objects.bulk_create(port_data)
        logger.debug(u'share.service. now add shared service port ok')
        # 保存env
        AppServiceEnv.objects.filter(service_key=service_key, app_version=app_version).delete()
        export = [x["container_port"] for x in list(port_list)]
        env_list = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id) \
            .exclude(container_port__in=export) \
            .values('ID', 'container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        share_info_list = AppServiceShareInfo.objects.filter(service_id=self.service.service_id) \
            .values("tenant_env_id", "is_change")
        share_info_map = {x["tenant_env_id"]: x["is_change"] for x in list(share_info_list)}
        env_data = []
        for env in list(env_list):
            is_change = env["is_change"]
            if env["ID"] in share_info_map.keys():
                is_change = share_info_map.get(env["ID"])
            app_env = AppServiceEnv(service_key=service_key,
                                    app_version=app_version,
                                    name=env["name"],
                                    attr_name=env["attr_name"],
                                    attr_value=env["attr_value"],
                                    scope=env["scope"],
                                    is_change=is_change,
                                    container_port=env["container_port"])
            env_data.append(app_env)
        if len(env_data) > 0:
            logger.debug(len(env_data))
            AppServiceEnv.objects.bulk_create(env_data)
        logger.debug(u'share.service. now add shared service env ok')
        
        # 保存extend_info
        count = ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version).count()
        if count == 0:
            extend_method = ServiceExtendMethod(
                service_key=service_key,
                app_version=app_version,
                min_node=self.service.min_node,
                max_node=20,
                step_node=1,
                min_memory=self.service.min_memory,
                max_memory=65536,
                step_memory=128,
                is_restart=False)
            extend_method.save()
        else:
            ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version) \
                .update(min_node=self.service.min_node, min_memory=self.service.min_memory)
        logger.debug(u'share.service. now add shared service extend method ok')
        
        # 保存持久化设置
        if self.service.category == "application":
            volume_list = TenantServiceVolume.objects.filter(service_id=self.service.service_id)
            volume_data = []
            AppServiceVolume.objects.filter(service_key=service_key,
                                            app_version=app_version).delete()
            for volume in list(volume_list):
                app_volume = AppServiceVolume(service_key=service_key,
                                              app_version=app_version,
                                              category=volume.category,
                                              volume_path=volume.volume_path)
                volume_data.append(app_volume)
            if len(volume_data) > 0:
                logger.debug(len(volume_data))
                AppServiceVolume.objects.bulk_create(volume_data)
        logger.debug(u'share.service. now add share service volume ok')
        # 服务依赖关系
        AppServiceRelation.objects.filter(service_key=service_key,
                                          app_version=app_version).delete()
        relation_list = TenantServiceRelation.objects.filter(service_id=self.service.service_id)
        dep_service_ids = [x.dep_service_id for x in list(relation_list)]
        dep_service_list = TenantServiceInfo.objects.filter(service_id__in=dep_service_ids)
        app_relation_list = []
        if len(dep_service_list) > 0:
            for dep_service in list(dep_service_list):
                if dep_service.service_key == "application":
                    logger.error("dep service is application not published")
                    raise http.Http404
                # dep_app_alias需要获取对应app_service中的app_alias
                dep_service_alias = dep_service.service_cname
                try:
                    app_service = AppService.objects.get(service_key=dep_service.service_key,
                                                         app_version=dep_service.version)
                    dep_service_alias = app_service.app_alias
                except Exception as e:
                    logger.exception(e)
                relation = AppServiceRelation(service_key=service_key,
                                              app_version=app_version,
                                              app_alias=app_alias,
                                              dep_service_key=dep_service.service_key,
                                              dep_app_version=dep_service.version,
                                              dep_app_alias=dep_service_alias)
                app_relation_list.append(relation)
        if len(app_relation_list) > 0:
            logger.debug(len(app_relation_list))
            AppServiceRelation.objects.bulk_create(app_relation_list)
        # 跳转到套餐设置
        return self.redirect_to(
            '/apps/{0}/{1}/share/step4?service_key={2}&app_version={3}'.format(self.tenantName, self.serviceAlias,
                                                                               service_key, app_version))


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


class ShareServiceImageView(BaseView):
    def post(self, request, *args, **kwargs):
        # 获取表单信息
        service_id = request.POST['service_id']
        logo = request.FILES['logo']
        # 更新图片路径
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
        data = {"success": True, "code": 200, "pic": image_info.logo.name}
        return JsonResponse(data, status=200)


class ShareServiceStep4View(LeftSideBarMixin, AuthedView):
    """分享设置套餐"""
    
    def get_context(self):
        context = super(ShareServiceStep4View, self).get_context()
        return context
    
    def get(self, request, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        context["myAppStatus"] = "active"
        # 查询之前是否设置有套餐
        service_key = request.GET.get("service_key")
        app_version = request.GET.get("app_version")
        context["service_key"] = service_key
        context["app_version"] = app_version
        context["tenant_name"] = self.tenantName
        context["service_alias"] = self.serviceAlias
        service_package = AppServicePackages.objects.filter(service_key=service_key, app_version=app_version)
        # 兼容之前数据
        dep_service_list = AppServiceRelation.objects.filter(service_key=service_key, app_version=app_version)
        if len(dep_service_list) > 0:
            service_package_map = {}
            for package in list(service_package):
                dep_info = package.dep_info
                dep_service_json = json.loads(dep_info)
                package.price = round(package.price, 2)
                package.total_price = round(package.total_price, 2)
                dep_service_map = {}
                if len(dep_service_json) > 0:
                    dep_service_map = {'{0}-{1}'.format(x.get("service_key"), x.get("app_version")): x for x in
                                       dep_service_json}
                for dep_service in list(dep_service_list):
                    service_key = dep_service.dep_service_key
                    app_version = dep_service.dep_app_version
                    service_alias = dep_service.dep_app_alias
                    
                    key = '{0}-{1}'.format(service_key, app_version)
                    if key in dep_service_map.keys():
                        pass
                    else:
                        memory = 128
                        node = 1
                        try:
                            service_info = ServiceInfo.objects.get(service_key=service_key, version=app_version)
                            memory = service_info.min_memory
                            node = service_info.min_node
                        except Exception:
                            pass
                        dep_service_map[key] = {
                            "service_key": service_key,
                            "app_version": app_version,
                            "memory": memory,
                            "node": node,
                            "service_alias": service_alias,
                        }
                service_package_map[package.ID] = dep_service_map.values()
            context["service_package_map"] = service_package_map
            dep_service_model = []
            for dep_service in list(dep_service_list):
                service_key = dep_service.dep_service_key
                app_version = dep_service.dep_app_version
                service_alias = dep_service.dep_app_alias
                tmp_map = {
                    "service_key": service_key,
                    "app_version": app_version,
                    "memory": 128,
                    "node": 1,
                    "service_alias": service_alias,
                }
                dep_service_model.append(tmp_map)
            context["dep_service_model"] = json.dumps(dep_service_model)
        else:
            context["service_package_map"] = {}
            context["dep_service_model"] = "[]"
        context["service_package"] = service_package
        context["tenantServiceInfo"] = self.service
        if TenantServicesPort.objects.filter(service_id=self.service.service_id, is_outer_service=True,
                                             protocol='http').exists():
            context["hasHttpServices"] = True
        # 返回页面
        return TemplateResponse(request, 'www/service/share_step_4.html', context)
    
    # form提交.
    def post(self, request, *args, **kwargs):
        # 获取form表单
        service_key = request.POST.get("service_key")
        app_version = request.POST.get('app_version')
        try:
            app = AppService.objects.get(service_key=service_key,
                                         app_version=app_version)
        except Exception as e:
            logger.exception(e)
            raise http.Http404
        try:
            # region发送请求
            if app.is_slug():
                self.upload_slug(app)
            elif app.is_image():
                self.upload_image(app)
            if not app.is_outer:
                return self.redirect_to('/apps/{0}/{1}/detail/'.format(self.tenantName, self.serviceAlias))
            return self.redirect_to('/apps/{0}/{1}/share/step5'.format(self.tenantName, self.serviceAlias))
        except Exception as e:
            logger.exception(e)
            return HttpResponse(status=500, content=e.__str__())
    
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
    
    def get(self, request, *args, **kwargs):
        # 跳转到服务关系发布页面
        package_id = request.POST.get("id", None)
        try:
            service_package = AppServicePackages.objects.get(pk=package_id)
        except Exception as e:
            logger.exception(e)
            return JsonResponse(status=500, data={"code": 500})
        data = {
            "code": 200,
            "data-name": service_package.name,
            "data-memory": service_package.memory,
            "data-node": service_package.node,
            "data-time": service_package.trial,
            "data-price": round(service_package.price, 2),
            "data-total": round(service_package.total_price, 2),
        }
        return JsonResponse(status=200, data=data)
    
    def post(self, request, *args, **kwargs):
        # 获取类型
        action = request.POST.get("action")
        package_id = request.POST.get("id", None)
        name = request.POST.get("name", "")
        memory = request.POST.get("memory", 128)
        node = request.POST.get("node", 1)
        trial = request.POST.get("trial", 0)
        price = request.POST.get("price", 0)
        total_price = request.POST.get("total_price", 0)
        service_key = request.POST.get("service_key", None)
        app_version = request.POST.get("app_version", None)
        dep_info = request.POST.get("dep_info", "[]")
        logger.debug(request.POST)
        
        if action == "delete":
            # delete
            AppServicePackages.objects.filter(pk=package_id).delete()
            return JsonResponse(status=200, data={"code": 200})
        elif action == "add" or action == "update":
            package = AppServicePackages()
            if package_id is None:
                count = AppServicePackages.objects.filter(service_key=service_key,
                                                          app_version=app_version,
                                                          name=name).count()
                if count > 0:
                    return JsonResponse(status=500, data={"code": 500, "msg": "套餐名称已存在!"})
            else:
                try:
                    package = AppServicePackages.objects.get(pk=package_id)
                except Exception:
                    pass
            package.service_key = service_key
            package.app_version = app_version
            package.name = name
            package.memory = memory
            package.node = node
            package.trial = trial
            package.price = round(float(price), 2)
            package.total_price = round(float(total_price), 2)
            package.dep_info = dep_info
            package.save()
            return JsonResponse(status=200, data={"code": 200, "info": json.dumps(package.to_dict())})
        else:
            try:
                service_package = AppServicePackages.objects.get(pk=package_id)
            except Exception as e:
                logger.exception(e)
                return JsonResponse(status=500, data={"code": 500})
            data = {
                "code": 200,
                "data-name": service_package.name,
                "data-memory": service_package.memory,
                "data-node": service_package.node,
                "data-time": service_package.trial,
                "data-price": service_package.price,
                "data-total": service_package.total_price,
            }
            return JsonResponse(status=200, data=data)
