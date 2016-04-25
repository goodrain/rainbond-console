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

from www.models import AppService, Service, AppServiceEnv, AppServicePort, AppServiceCategory, AppServiceRelation

import logging

logger = logging.getLogger('default')


# 复制数据属性
def copy_properties(copy_from, to, field_list):
    for field in field_list:
        if hasattr(to, field) and hasattr(copy_from, field):
            setattr(to, field, getattr(copy_from, field))
    return to


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
        pre_app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[:1]
        # 生成新的version
        init_data = {
            'tenant_id': {'value': self.service.tenant_id},
            'service_id': {'value': self.service.service_id},
            'deploy_version': {'value': self.service.deploy_version},
            'app_key': {'value': make_uuid(self.serviceAlias) if pre_app else pre_app.app_key},
            'app_version': {'value': make_uuid(self.serviceAlias)[:20]},
            'app_alias': {'value': self.service.service_alias},
            'publisher': {'value': self.user.email},
            'min_node': {'value': self.service.min_node},
            'min_memory': {'value': self.service.min_memory},
            'volume_mount_path': {'value': self.service.volume_mount_path},
        }
        context.update('fields', init_data)
        if pre_app:
            # 查询端口信息
            port_list = AppServicePort.objects.filter(app_key=pre_app.app_key, app_version=pre_app.app_version)\
                .values('container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
            # 查询环境信息
            env_list = AppServiceEnv.objects.filter(app_key=pre_app.app_key, app_version=pre_app.app_version)\
                .values('container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        else:
            # 查询端口信息
            port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id) \
                .values('container_port', 'mapping_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
            # 查询环境信息
            env_list = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id) \
                .values('container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        context.update({'fields': init_data,
                        'port_list': list(port_list),
                        'env_list': list(env_list),
                        'is_init': False if pre_app else True})
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
        if 'publish' in post_data:
            action = 'app_publish'
        elif 'update' in post_data:
            action = 'app_publish'  # 'app_update'
        else:
            return HttpResponse("error", status=500)

        func = getattr(self, 'app_publish')
        try:
            success = func(post_data)
            if success:
                return self.redirect_to('/apps/{0}/{1}/publish/v1/relation/'.format(self.tenantName, self.serviceAlias))
            else:
                logger.error('service.publish', "{} failed".format(action))
                return HttpResponse(u"发布过程出现异常", status=500)
        except Exception as e:
            logger.exception('service.publish', e)
            return HttpResponse(u"应用发布失败", status=500)

    def app_publish(self, post_data):
        """ 服务发布流程 """
        # 添加发布服务
        app = self._add_new_app(post_data)
        logger.debug(u'publish.service. now add publish service ok')
        # 添加服务端口
        self._add_new_app_env(app, post_data)
        logger.debug(u'publish.service. now add publish service env ok')
        # 添加服务环境
        self._add_new_app_port(app, post_data)
        logger.debug(u'publish.service. now add publish service port ok')
        logger.info("service.publish",
                    "now publish service:{}:{}".format(app.service_id,
                                                       app.deploy_version))
        return True



    # 添加发布服务
    def _add_new_app(self, data):
        # 获取之前的数据
        pre_app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[:1]
        # 获X取新数据
        app = AppService(
            app_key=data['app_key'],
            app_version=data['app_version'],
            app_alias=data.get('app_alias', self.service.service_alias),
            publisher=self.user.email,
            logo=None if pre_app else pre_app.logo,
            info=None if pre_app else pre_app.info,
            desc=None if pre_app else pre_app.desc,
            status='show' if pre_app else pre_app.status,
            category=None if pre_app else pre_app.category,
            volume_mount_path=data.get('volume_mount_path', self.service.volume_mount_path),
            pay_type='free' if pre_app else pre_app.pay_type,
            price='0.00' if pre_app else pre_app.price,
            is_base=False if pre_app else pre_app.is_base,
            is_outer=False if pre_app else pre_app.is_outer,
            is_ok=1)
        filed_list = ('tenant_id', 'service_id', 'deploy_version',
                      'is_service', 'is_web_service', 'image',
                      'extend_method', 'cmd', 'env', 'language',
                      'min_node', 'min_cpu', 'min_memory', 'inner_port',
                      'service_type')
        app = copy_properties(self.service, app, filed_list)
        app.save()
        return app

    def _add_new_app_env(self, app, data):
        # 删除之前所有
        AppServiceEnv.objects.filter(app_key=app.app_key,
                                     app_version=app.app_version).delete()
        env_list = data.get('env_list', [])
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
        return env_data

    def _add_new_app_port(self, app, data):
        AppServicePort.objects.filter(app_key=app.app_key,
                                      app_version=app.app_version).delete()
        port_list = data.get('port_list', [])
        port_data = []
        for port in port_list:
            app_port = AppServicePort(app_key=app.app_key,
                                      app_version=app.app_version)
            field_list = ('container_port', 'mapping_port', 'protocol',
                          'port_alias', 'is_inner_service', 'is_outer_service')
            app_port = copy_properties(port, app_port, field_list)
            port_data.append(app_port)
        AppServicePort.objects.bulk_create(port_data)
        return port_data


class PublishServiceRelationView(LeftSideBarMixin, AuthedView):
    """ 服务关系配置页面 """
    def get_context(self):
        context = super(PublishServiceView, self).get_context()
        return context

    def get_media(self):
        media = super(PublishServiceView, self).get_media()
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
        pre_app = app_list.filter(service_id=self.service.service_id).order_by('ID')[1:2]
        # 获取所有可配置的服务列表
        work_list = app_list.exclude(service_id=self.service.service_id)
        # 判断之前是否已经发布过服务,获取之前的依赖关系
        if pre_app:
            # 查询依赖当前服务的发布服务
            suf_fix = AppServiceRelation.objects.filter(dep_app_key=pre_app.app_key,
                                                        dep_app_version=pre_app.app_version)
            suf_fix_key = [x.app_key for x in suf_fix]
            suf_fix_list = work_list.filter(service_id__in=suf_fix_key)
            # 查询当前服务依赖的其他服务
            pre_fix = AppServiceRelation.objects.filter(app_key=pre_app.app_key,
                                                        app_version=pre_app.app_version)
            pre_fix_key = [x.app_key for x in pre_fix]
            pre_fix_list = work_list.filter(service_id__in=pre_fix_key)

            work_list.remove(suf_fix_list)
            work_list.remove(pre_fix_list)
        # 查询对应服务的名称等信息
        context.update({'suffix': list(suf_fix_list),
                        'prefix': list(pre_fix_list),
                        'work_list': list(work_list),
                        'is_publish': True if pre_app else False})
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
        # 保存依赖当前服务的发布服务
        suf_fix_list = post_data.get("suffix", [])
        if suf_fix_list:
            for suf_fix in suf_fix_list:
                relation = AppServiceRelation(app_key=app.app_key,
                                              app_version=app.app_version,
                                              dep_app_key=suf_fix.app_key,
                                              dep_app_version=suf_fix.app_version)
            relation_list.append(relation)

        try:
            # 批量增加
            new_list = AppServiceRelation.objects.bulk_create(relation_list)
            if new_list:
                return self.redirect_to('/apps/{0}/{1}/publish/v1/extra/'.format(self.tenantName, self.serviceAlias))
            else:
                logger.error('service.publish', "batch add relationship failed")
                return HttpResponse(u"发布过程出现异常", status=500)
        except Exception as e:
            logger.exception('service.publish', e)
            return HttpResponse(u"应用发布失败", status=500)


class PublishServiceDetailView(LeftSideBarMixin, AuthedView):
    """ 服务信息配置页面 """
    def get_context(self):
        context = super(PublishServiceView, self).get_context()
        return context

    def get_media(self):
        media = super(PublishServiceView, self).get_media()
        return media

    @perm_required('app_publish')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        # 获取之前发布的服务信息
        pre_app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[1:2]
        if pre_app:
            pass
        else:
            pre_app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[:1]
        # 查询对应服务的名称等信息
        context.update({'app': pre_app})
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
            service_id = self.service.service_id
            app_key = detail_form.cleaned_data['app_key']
            app_version = detail_form.cleaned_data['app_version']
            pre_version = detail_form.cleaned_data['pre_version']
            app_alias = detail_form.cleaned_data['app_version']
            info = detail_form.cleaned_data['info']
            desc = detail_form.cleaned_data['desc']
            category_1 = detail_form.cleaned_data['category_1']
            category_2 = detail_form.cleaned_data['category_2']
            category_3 = detail_form.cleaned_data['category_3']
            logo = detail_form.cleaned_data['logo']
            is_outer = detail_form.cleaned_data['is_outer']
            # 获取保存的服务信息
            app = AppService.objects.filter(service_id=self.service.service_id).order_by('ID')[:1]
            # 更新app的属性
            app.app_alias = app_alias
            # 这里判断版本号是否与之前的一致
            if app_version == pre_version:
                # 需要删除之前的纪录
                AppService.objects.delete(app_version=pre_version, app_key=app.app_key)
                AppServiceEnv.objects.filter(app_version=pre_version, app_key=app.app_key).delete()
                AppServiceEnv.objects.filter(app_version=app.app_version, app_key=app.app_key).update(app_version=app_version)
                AppServicePort.objects.filter(app_version=pre_version, app_key=app.app_key).delete()
                AppServicePort.objects.filter(app_version=app.app_version, app_key=app.app_key).update(app_version=app_version)
                AppServiceRelation.objects.filter(app_version=pre_version, app_key=app.app_key).delete()
                AppServiceRelation.objects.filter(app_version=app.app_version, app_key=app.app_key).update(app_version=app_version)
                AppServiceRelation.objects.filter(dep_app_version=pre_version, dep_app_key=app.app_key).delete()
                AppServiceRelation.objects.filter(dep_app_version=app.app_version, dep_app_key=app.app_key).update(app_version=app_version)
            app.app_version = app_version
            app.info = info
            app.desc = desc
            app.logo = logo
            app.category = '{}:{}:{}'.format(category_1, category_2, category_3)
            app.save()

            # 保存到service表格
            app_record = Service()
            filed_list = ('tenant_id', 'service_id', 'deploy_version', 'app_key',
                          'app_version', 'app_alias', 'publisher', 'logo', 'info',
                          'desc', 'status', 'category', 'is_service', 'is_web_service',
                          'image', 'extend_method', 'cmd', 'env', 'min_node',
                          'min_cpu', 'min_memory', 'inner_port', 'volume_mount_path',
                          'service_type', 'language', 'pay_type', 'price', 'is_base'
                          )
            app_record = copy_properties(app, app_record, filed_list)
            app_record['is_outer'] = is_outer

            # 通知region api进行发布操作
            # 生成发布事件
            event_id = self._create_publish_event(is_outer)
            if app.is_slug():
                self.upload_slug(app, event_id)
            elif app.is_image():
                self.upload_image(app, event_id)

            data = {"success": True, "code": 200}
            return JsonResponse(data, status=200)
        else:
            data = {"success": False, "code": 201}
            return JsonResponse(data, status=200)

    def _create_publish_event(self, is_outer):
        template = {
            "user_id": self.user.nick_name,
            "tenant_id": self.service.tenant_id,
            "service_id": self.service.service_id,
            "type": "publish",
            "desc": u"应用发布中...",
            "show": True,
            "is_outer": is_outer,
        }
        try:
            r = RegionServiceApi()
            body = r.create_event(self.service.service_region, json.dumps(template))
            return body.event_id
        except Exception as e:
            logger.exception("service.publish", e)
            return None

    def upload_slug(self, app, event_id, is_outer):
        """ 上传slug包 """
        oss_upload_task = {
            "app_key": app.app_key,
            "app_version": app.app_version,
            "service_id": app.service_id,
            "deploy_version": app.deploy_version,
            "tenant_id": self.service.tenant_id,
            "action": "create_new_version",
            "event_id": event_id,
            "is_outer": is_outer,
        }
        try:
            r = RegionServiceApi()
            r.send_task(self.service.service_region, 'app_slug', json.dumps(oss_upload_task))
        except Exception as e:
            logger.error("service.publish",
                         "upload_slug for {0}({1}), but an error occurred".format(app.app_key, app.app_version))
            logger.exception("service.publish", e)

    def upload_image(self, app, event_id, is_outer):
        """ 上传image镜像 """
        image_upload_task = {
            "action": "create_new_version",
            "image": app.image,
            "event_id": event_id,
            "is_outer": is_outer,
        }

        try:
            r = RegionServiceApi()
            r.send_task(self.service.service_region, 'app_image', json.dumps(image_upload_task))
        except Exception as e:
            logger.error("service.publish",
                         "upload_image for {0}({1}), but an error occurred".format(app.app_key, app.app_version))
            logger.exception("service.publish", e)


class ServiceDetailForm(forms.Form):
    """ 服务发布详情页form """
    service_id = forms.CharField()
    app_key = forms.CharField()
    app_version = forms.CharField()

    app_alias = forms.CharField()
    logo = forms.FileField()
    info = forms.CharField()
    desc = forms.CharField()
    category_1 = forms.ChoiceField()
    category_2 = forms.ChoiceField()
    category_3 = forms.ChoiceField()

    is_outer = forms.BooleanField()


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

