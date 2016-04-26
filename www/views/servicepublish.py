# -*- coding: utf8 -*-
import json
from addict import Dict
# from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse, JsonResponse
from django.core import serializers
from django.db import transaction
from django.db.models import Q
from django import forms


from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import Users, PermRelTenant, TenantServiceRelation, App, Category, \
    TenantServicesPort, TenantServiceEnvVar
from www.forms.services import ServicePublishForm
from www.utils import increase_version
from www.service_http import RegionServiceApi
from www.utils.crypt import make_uuid

from www.models import AppService, ServiceInfo, AppServiceEnv, AppServicePort, AppServiceCategory, AppServiceRelation

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
        media = super(PublishServiceDetailView, self).get_media() + \
                self.vendor('www/css/goodrainstyle.css',
                            'www/js/jquery.cookie.js',
                            'www/js/validator.min.js',
                            'www/js/gr/app_publish.js')
        return media

    @perm_required('app_publish')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        # 获取之前发布的服务信息
        pre_app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[:1]
        # 生成新的version
        init_data = {
            'tenant_id': self.service.tenant_id,
            'service_id': self.service.service_id,
            'deploy_version': self.service.deploy_version,
            'app_key': pre_app.app_key if pre_app else make_uuid(self.serviceAlias),
            'app_version': pre_app.app_version if pre_app else '0.0.1',
            'app_alias': self.service.service_alias,
            'publisher': self.user.email,
            'min_node': self.service.min_node,
            'min_memory': self.service.min_memory,
            'volume_mount_path': self.service.volume_mount_path,
        }
        # 查询对应服务的名称等信息
        context.update({'app': init_data})
        root_categories = AppServiceCategory.objects.only('ID', 'name').filter(parent=0)
        root_category_list = [{"id": x.pk, "display_name": x.name} for x in root_categories]
        context['root_category_list'] = root_category_list
        # 返回页面
        return TemplateResponse(self.request,
                                'www/service/publish_step_3.html',
                                context)

    # form提交.
    @perm_required('app_publish')
    def post(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        # 信息的表单
        detail_form = ServiceDetailForm(request.POST, request.FILES)
        if detail_form.is_valid():
            logger.debug("service.publish", "post_data is {0}".format(detail_form))
            # 获取表单信息
            service_id = detail_form.cleaned_data['service_id']
            deploy_version = detail_form.cleaned_data['deploy_version']
            app_key = detail_form.cleaned_data['app_key']
            app_version = detail_form.cleaned_data['app_version']
            app_alias = detail_form.cleaned_data['app_version']
            info = detail_form.cleaned_data['info']
            desc = detail_form.cleaned_data['desc']
            logo = detail_form.cleaned_data['logo']
            app_type_first = detail_form.cleaned_data['app_type_first']
            app_type_second = detail_form.cleaned_data['app_type_second']
            app_type_third = detail_form.cleaned_data['app_type_third']
            is_outer = detail_form.cleaned_data['is_outer']

            # 获取保存的服务信息
            app = AppService.objects.filter(app_key=app_key, app_version=app_version)
            if app:
                # update
                app.app_alias = app_alias
                app.logo = logo
                app.info = info
                app.desc = desc
                app.is_outer = is_outer
                app.category = app_type_third
                app.save()
            else:
                # new
                app = AppService(
                    app_key=app_key,
                    app_version=app_version,
                    app_alias=app_alias,
                    creater=self.user.email,
                    logo=logo,
                    info=info,
                    desc=desc,
                    status='show',
                    category=app_type_third,
                    is_base=False,
                    is_outer=is_outer,
                    is_ok=1)
                filed_list = ('tenant_id', 'service_id', 'is_service', 'env',
                              'is_web_service', 'image', 'extend_method', 'cmd',
                              'min_node', 'min_cpu', 'min_memory', 'inner_port',
                              'service_type', 'volume_mount_path', 'is_init_accout')
                app = copy_properties(self.service, app, filed_list)
                app.save()
            # 跳转到服务关系页面
            return self.redirect_to('/apps/{0}/{1}/publish/relation/'.format(self.tenantName, self.serviceAlias))
        else:
            logger.error('service.publish', "form valid failed: {}".format(detail_form.errors))
            return HttpResponse(u"发布过程出现异常", status=500)


class PublishServiceRelationView(LeftSideBarMixin, AuthedView):
    """ 服务关系配置页面 """
    def get_context(self):
        context = super(PublishServiceRelationView, self).get_context()
        return context

    def get_media(self):
        media = super(PublishServiceRelationView, self).get_media() + \
                self.vendor('www/css/goodrainstyle.css',
                            'www/js/jquery.cookie.js',
                            'www/js/validator.min.js',
                            'www/js/gr/app_publish.js')
        return media

    @perm_required('app_publish')
    def get(self, request, *args, **kwargs):
        # 跳转到服务关系发布页面
        context = self.get_context()
        # 查询基础服务,和当前用户发布的服务publisher in None,self.user.email
        app_list = AppService.objects.filter(Q(is_base=True) |
                                             Q(publisher=self.user.email)) \
            .values('tenant_id', 'service_id', 'app_alias', 'deploy_version', 'app_key', 'app_version')
        # 最新的纪录是之前新增的,获取app_key,app_version
        app = app_list.filter(service_id=self.service.service_id).order_by('ID')[:1]
        # 获取所有可配置的服务列表
        work_list = app_list.exclude(service_id=self.service.service_id)
        # 查询对应服务的名称等信息
        context.update({'relationlist': list(work_list),
                        'app': app})
        # 返回页面
        return TemplateResponse(self.request,
                                'www/service/publish_step_2.html',
                                context)

    # form提交.
    @perm_required('app_publish')
    def post(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        post_data = request.POST.dict()
        logger.debug("service.publish", "post_data is {0}".format(post_data))
        app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[:1]
        # 保存当前服务依赖的其他服务
        relation_list = []
        pre_fix_list = post_data.get("prefix", [])
        if pre_fix_list:
            for pre_fix in pre_fix_list:
                relation = AppServiceRelation(app_key=pre_fix.app_key,
                                              app_version=pre_fix.app_version,
                                              dep_app_key=app.app_key,
                                              dep_app_version=app.app_version)
                relation_list.append(relation)
            AppServiceRelation.objects.filter(dep_app_key=app.app_key, dep_app_version=app.app_version).delete()
        # 保存依赖当前服务的发布服务
        suf_fix_list = post_data.get("suffix", [])
        if suf_fix_list:
            for suf_fix in suf_fix_list:
                relation = AppServiceRelation(app_key=app.app_key,
                                              app_version=app.app_version,
                                              dep_app_key=suf_fix.app_key,
                                              dep_app_version=suf_fix.app_version)
                relation_list.append(relation)
            AppServiceRelation.objects.filter(app_key=app.app_key, app_version=app.app_version).delete()
        try:
            # 批量增加
            new_list = AppServiceRelation.objects.bulk_create(relation_list)
            if new_list:
                return self.redirect_to('/apps/{0}/{1}/publish/extra/'.format(self.tenantName, self.serviceAlias))
            else:
                logger.error('service.publish', "batch add relationship failed")
                return HttpResponse(u"发布过程出现异常", status=500)
        except Exception as e:
            logger.exception('service.publish', e)
            return HttpResponse(u"应用发布失败", status=500)


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

    @perm_required('app_publish')
    def get(self, request, *args, **kwargs):
        # 跳转到服务发布页面
        context = self.get_context()
        # 查询服务上一次发布的信息
        app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[:1]
        pre_app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[1:2]
        # 生成新的version
        init_data = {
            'tenant_id': {'value': self.service.tenant_id},
            'service_id': {'value': self.service.service_id},
            'deploy_version': {'value': self.service.deploy_version},
            'app_key': {'value': app.app_key},
            'app_version': {'value': app.app_version},
            'app_alias': {'value': self.service.service_alias},
            'publisher': {'value': self.user.email},
            'min_node': {'value': self.service.min_node},
            'min_memory': {'value': self.service.min_memory},
            'volume_mount_path': {'value': self.service.volume_mount_path},
        }
        context.update('fields', init_data)
        # 端口
        port_list = AppServicePort.objects.filter(app_key=app.app_key, app_version=app.app_version).values('container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        if not port_list and pre_app:
            port_list = AppServicePort.objects.filter(app_key=pre_app.app_key, app_version=pre_app.app_version).values('container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        # 服务不存在直接使用tenantservice
        if not port_list:
            port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id).values('container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        # 环境
        env_list = AppServiceEnv.objects.filter(app_key=app.app_key, app_version=app.app_version).values('container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if not env_list and pre_app:
            env_list = AppServiceEnv.objects.filter(app_key=pre_app.app_key, app_version=pre_app.app_version).values('container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        #
        if not env_list:
            env_list = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).values('container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')

        context.update({'port_list': list(port_list),
                        'env_list': list(env_list),
                        })
        context["nodeList"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        choices = [(128, '128M'), (256, '256M'), (512, '512M'), (1024, '1G'), (2048, '2G'), (4096, '4G'), (8192, '8G')]
        choice_list = []
        for value, label in choices:
            choice_list.append({"label": label, "value": value})
        context["memoryList"] = choice_list

        # 返回页面
        return TemplateResponse(self.request,
                                'www/service/publish_step_1.html',
                                context)

    # form提交.
    @perm_required('app_publish')
    def post(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        post_data = request.POST.dict()
        logger.debug("service.publish", "post_data is {0}".format(post_data))
        # 节点\内存\cpu
        minnode = post_data.get('min_node')
        minmemory = post_data.get('min_memory')
        app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[:1]
        # app slug
        if app.is_slug():
            app.slug = '/app_publish/{0}/{1}.tgz'.format(app.app_key, app.app_version)
        if minnode == self.service.min_node and minmemory == self.service.min_memory:
            pass
        else:
            app.min_node = minnode
            app.min_memory = minmemory
            cm = int(minmemory)
            if cm >= 128:
                ccpu = int(cm / 128) * 20
                app.min_cpu = ccpu
            app = app.save()
        logger.debug(u'publish.service. now add publish service ok')
        # 环境配置
        AppServiceEnv.objects.filter(app_key=app.app_key,
                                     app_version=app.app_version).delete()
        env_list = post_data.get('env_list', [])
        env_data = []
        for i in env_list:
            app_env = AppServiceEnv(app_key=app.app_key,
                                    app_version=app.app_version)
            filed_list = ('name', 'attr_name', 'attr_value', 'is_change',
                          'container_port', 'scope', 'options')
            app_env = copy_properties(i, app_env, filed_list)
            env_data.append(app_env)
        # 批量增加
        AppServiceEnv.objects.bulk_create(env_data)
        logger.debug(u'publish.service. now add publish service env ok')
        # 端口配置
        AppServicePort.objects.filter(app_key=app.app_key,
                                      app_version=app.app_version).delete()
        port_list = post_data.get('port_list', [])
        port_data = []
        for port in port_list:
            app_port = AppServicePort(app_key=app.app_key,
                                      app_version=app.app_version)
            field_list = ('container_port', 'mapping_port', 'protocol',
                          'port_alias', 'is_inner_service', 'is_outer_service')
            app_port = copy_properties(port, app_port, field_list)
            port_data.append(app_port)
        AppServicePort.objects.bulk_create(port_data)
        logger.debug(u'publish.service. now add publish service port ok')

        # 生成发布事件
        event_id = self._create_publish_event()
        if app.is_slug():
            self.upload_slug(app, event_id)
        elif app.is_image():
            self.upload_image(app, event_id)

        next_url = '/apps/{0}/{1}/detail/'.format(self.tenantName, self.serviceAlias)
        return JsonResponse({"success": True, "next_url": next_url}, status=200)

    def _create_publish_event(self):
        template = {
            "user_id": self.user.nick_name,
            "tenant_id": self.service.tenant_id,
            "service_id": self.service.service_id,
            "type": "publish",
            "desc": u"应用发布中...",
            "show": True,
        }
        try:
            body = regionClient.create_event(self.service.service_region, json.dumps(template))
            return body.event_id
        except Exception as e:
            logger.exception("service.publish", e)
            return None

    def upload_slug(self, app, event_id):
        """ 上传slug包 """
        oss_upload_task = {
            "app_key": app.app_key,
            "app_version": app.app_version,
            "service_id": self.service.service_id,
            "deploy_version": self.service.deploy_version,
            "tenant_id": self.service.tenant_id,
            "action": "create_new_version",
            "event_id": event_id,
            "is_outer": app.is_outer,
        }
        try:
            regionClient.send_task(self.service.service_region, 'app_slug', json.dumps(oss_upload_task))
        except Exception as e:
            logger.error("service.publish",
                         "upload_slug for {0}({1}), but an error occurred".format(app.app_key, app.app_version))
            logger.exception("service.publish", e)

    def upload_image(self, app, event_id):
        """ 上传image镜像 """
        image_upload_task = {
            "action": "create_new_version",
            "image": app.image,
            "event_id": event_id,
            "is_outer": app.is_outer,
        }

        try:
            regionClient.send_task(self.service.service_region, 'app_image', json.dumps(image_upload_task))
        except Exception as e:
            logger.error("service.publish",
                         "upload_image for {0}({1}), but an error occurred".format(app.app_key, app.app_version))
            logger.exception("service.publish", e)


class ServiceDetailForm(forms.Form):
    """ 服务发布详情页form """
    service_id = forms.CharField()
    deploy_version = forms.CharField()
    app_key = forms.CharField()
    app_version = forms.CharField()
    app_alias = forms.CharField()
    logo = forms.FileField()
    info = forms.CharField(required=False)
    desc = forms.CharField(required=False)
    app_type_first = forms.CharField(required=False)
    app_type_second = forms.CharField(required=False)
    app_type_third = forms.CharField(required=False)
    is_outer = forms.BooleanField(required=False,
                                  initial=False)


    # 修改|新增|删除
    # def _filter_array(self, old_list, new_list):
    #     key_list = [x.attr_name for x in new_list]
    #     dict_list = [(x.attr_name, x) for x in new_list]
    #     del_list = []
    #     mod_list = []
    #     for env in old_list:
    #         if env.attr_name in key_list:
    #             # 修改|不变
    #             info = dict_list[env.attr_name]
    #             if info.attr_value == env.attr_value:
    #                 pass
    #             else:
    #                 env.attr_value = info.attr_value
    #                 mod_list.append(env)
    #             new_list.remove(info)
    #         else:
    #             # 待删除
    #             del_list.append(env)
    #     return new_list, mod_list, del_list

