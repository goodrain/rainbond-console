# -*- coding: utf8 -*-
import json
from django.template.response import TemplateResponse
from django.http.response import HttpResponse
from django.db.models import Q
from django import forms
from django.conf import settings

from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import TenantServicesPort, TenantServiceEnvVar
from www.service_http import RegionServiceApi
from www.utils.crypt import make_uuid
from www.servicetype import ServiceType
from www.utils import sn

from www.models import AppService, AppServiceEnv, AppServicePort, \
    AppServiceCategory, AppServiceRelation, ServiceExtendMethod, \
    TenantServiceVolume, AppServiceVolume

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

    @perm_required('app_publish')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["myAppStatus"] = "active"

        init_data = {
            'tenant_id': self.service.tenant_id,
            'service_id': self.service.service_id,
            'deploy_version': self.service.deploy_version,
            'publisher': self.user.email,
        }

        # 获取之前发布的服务信息
        pre_app = AppService.objects.filter(service_id=self.service.service_id).order_by('-ID')[:1]
        if len(pre_app) == 1:
            pre_app = list(pre_app)[0]
            # if pre_app.show_category:
            #     first, second, third = pre_app.show_category.split(",")
            init_data.update({
                'service_key': pre_app.service_key,
                'app_version': pre_app.app_version,
                'app_alias': pre_app.app_alias,
                'min_node': pre_app.min_node,
                'min_memory': pre_app.min_memory,
                'volume_mount_path': pre_app.volume_mount_path,
                'info': pre_app.info,
                'desc': pre_app.desc,
                'is_outer': pre_app.is_outer,
                'is_private': pre_app.status == "private",
                'show_app': pre_app.show_app,
                'show_assistant': pre_app.show_assistant,
                'is_init_accout': pre_app.is_init_accout,
                'first': '',
                'second': '',
                'thrid': '',
                'logo': pre_app.logo,
                'service_type': pre_app.service_type,
            })
        else:
            init_data.update({
                'service_key': make_uuid(self.serviceAlias),
                'app_version': "0.0.1",
                'app_alias': self.service.service_cname,
                'min_node': self.service.min_node,
                'min_memory': self.service.min_memory,
                'volume_mount_path': self.service.volume_mount_path,
                'info': '',
                'first': '',
                'second': '',
                'thrid': '',
                'desc': self.service.desc if self.service.desc else '',
                'is_init_accout': False,
                'is_outer': False,
                'service_type': self.service.service_type,
                'is_private': False,
                'show_app': True,
                'show_assistant': True,
            })
        # 查询对应服务的名称等信息
        context.update({'app': init_data})
        context["service_types"] = ServiceType.type_maps
        # root_categories = AppServiceCategory.objects.only('ID', 'name').filter(parent=0)
        # root_category_list = [{"id": x.pk, "display_name": x.name} for x in root_categories]
        # context['root_category_list'] = root_category_list
        # 返回页面
        return TemplateResponse(self.request,
                                'www/service/publish_step_1.html',
                                context)

    # form提交.
    @perm_required('app_publish')
    def post(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        # 信息的表单
        try:
            detail_form = ServiceDetailForm(request.POST, request.FILES)
            if detail_form.is_valid():
                logger.debug("service.publish", "post_data is {0}".format(detail_form))
                # 获取表单信息
                service_key = detail_form.cleaned_data['service_key']
                app_version = detail_form.cleaned_data['app_version']
                app_alias = detail_form.cleaned_data['app_alias']
                info = detail_form.cleaned_data['info']
                desc = detail_form.cleaned_data['desc']
                logo = detail_form.cleaned_data['logo']
                # app_type_first = detail_form.cleaned_data['app_type_first']
                # app_type_second = detail_form.cleaned_data['app_type_second']
                # app_type_third = detail_form.cleaned_data['app_type_third']
                is_outer = detail_form.cleaned_data['is_outer']
                is_init_accout = detail_form.cleaned_data['is_init_accout']
                app_service_type = detail_form.cleaned_data['app_service_type']

                is_private = detail_form.cleaned_data.get('is_private', False)
                show_app = detail_form.cleaned_data.get('show_app', False)
                show_assistant = detail_form.cleaned_data.get('show_assistant', False)
                # 获取保存的服务信息
                app = AppService.objects.filter(service_key=service_key, app_version=app_version)
                if len(app) == 1:
                    app = list(app)[0]
                if app:
                    # update
                    app.app_alias = app_alias
                    app.logo = logo
                    app.info = info
                    app.desc = desc
                    app.is_outer = is_outer
                    app.image = self.service.image
                    app.is_init_accout = is_init_accout
                    app.show_category = ''
                    app.save()
                else:
                    # new
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
                        logo=logo,
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
                        service_type=app_service_type,
                        is_init_accout=is_init_accout,
                        show_category='',
                        is_base=False,
                        is_outer=is_outer,
                        publisher=self.user.email,
                        show_app=True,
                        show_assistant=True,
                        is_ok=0)
                    filed_list = ('tenant_id', 'service_id', 'is_service', 'env',
                                  'is_web_service', 'image', 'extend_method', 'cmd',
                                  'min_node', 'min_cpu', 'min_memory', 'inner_port',
                                  'service_type', 'volume_mount_path', 'is_init_accout')
                    app = copy_properties(self.service, app, filed_list)
                    if app.is_slug():
                        app.slug = '/app_publish/{0}/{1}.tgz'.format(app.service_key, app.app_version)
                    # 更新status、show_app、show_assistant
                    if is_private:
                        app.status = "private"
                    app.show_app = show_app
                    app.show_assistant = show_assistant
                    app.save()
                # 跳转到服务关系页面
                return self.redirect_to('/apps/{0}/{1}/publish/extra/?service_key={2}&app_version={3}'.format(self.tenantName, self.serviceAlias, service_key, app_version))
            else:
                logger.error('service.publish', "form valid failed: {}".format(detail_form.errors))
        except Exception as e:
            logger.exception(e)
        return HttpResponse(u"发布过程出现异常", status=500)


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

    @perm_required('app_publish')
    def get(self, request, *args, **kwargs):
        # 跳转到服务发布页面
        context = self.get_context()
        service_key = request.GET.get('service_key')
        app_version = request.GET.get('app_version')
        # 查询服务上一次发布的信息,不存在会异常
        app = AppService.objects.get(service_key=service_key, app_version=app_version)
        # 查询上一次发布的服务
        pre_app = AppService.objects.filter(service_key=service_key).order_by('-ID')[1:2]
        pre_num = len(pre_app)
        if pre_num == 1:
            pre_app = list(pre_app)[0]
        # 生成新的version
        init_data = {
            'tenant_id': self.service.tenant_id,
            'service_id': self.service.service_id,
            'deploy_version': self.service.deploy_version,
            'service_key': app.service_key,
            'app_version': app.app_version,
            'app_alias': self.service.service_alias,
            'publisher': self.user.email,
            'min_node': self.service.min_node,
            'min_memory': self.service.min_memory,
            'volume_mount_path': self.service.volume_mount_path,
        }
        context.update({'fields': init_data})
        # 端口
        port_list = AppServicePort.objects.filter(service_key=app.service_key, app_version=app.app_version).values('container_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        if len(port_list) < 1 and pre_num == 1:
            port_list = AppServicePort.objects.filter(service_key=pre_app.service_key, app_version=pre_app.app_version).values('container_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        # 服务不存在直接使用tenantservice
        if len(port_list) < 1:
            port_list = TenantServicesPort.objects.filter(service_id=self.service.service_id).values('container_port', 'protocol', 'port_alias', 'is_inner_service', 'is_outer_service')
        # 环境
        env_list = AppServiceEnv.objects.filter(service_key=app.service_key, app_version=app.app_version).values('container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if len(env_list) < 1 and pre_num == 1:
            env_list = AppServiceEnv.objects.filter(service_key=pre_app.service_key, app_version=pre_app.app_version).values('container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')
        if len(env_list) < 1:
            ports = self.getServicePort(self.service.service_id)
            env_list = TenantServiceEnvVar.objects.filter(service_id=self.service.service_id).exclude(container_port__in=ports).values('container_port', 'name', 'attr_name', 'attr_value', 'is_change', 'scope')

        context.update({'port_list': list(port_list),
                        'env_list': list(env_list), })
        context["nodeList"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        choices = [(128, '128M'), (256, '256M'), (512, '512M'), (1024, '1G'), (2048, '2G'), (4096, '4G'), (8192, '8G'), (16384, '16G'), (32768, '32G'), (65536, '64G')]
        choice_list = []
        for value, label in choices:
            choice_list.append({"label": label, "value": value})
        context["memoryList"] = choice_list
        # 持久化信息
        result_list = []
        if self.service.category == "application":
            volume_list = TenantServiceVolume.objects.filter(service_id=self.service.service_id)
            for volume in list(volume_list):
                tmp_path = volume.volume_path
                if tmp_path:
                    volume.volume_path = tmp_path.replace("/app/", "", 1)
                result_list.append(volume)

        context["volume_list"] = result_list
        # 返回页面
        return TemplateResponse(self.request,
                                'www/service/publish_step_2.html',
                                context)

    # form提交.
    @perm_required('app_publish')
    def post(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        try:
            post_data = request.POST.dict()
            service_key = post_data.get('service_key')
            app_version = post_data.get('app_version')
            logger.debug("service.publish", "post_data is {0}".format(post_data))
            # 节点\内存\cpu
            minnode = post_data.get('min_node')
            minmemory = post_data.get('min_memory')
            maxnode = post_data.get('max_node')
            maxmemory = post_data.get('max_memory')
            stepnode = post_data.get('step_node')
            stepmemory = post_data.get('step_memory')
            node_is_restart = post_data.get('node_is_restart')
            
            app = AppService.objects.get(service_key=service_key, app_version=app_version)
            if minnode == self.service.min_node and minmemory == self.service.min_memory:
                pass
            else:
                app.min_node = minnode
                app.min_memory = minmemory
                cm = int(minmemory)
                if cm >= 128:
                    ccpu = int(cm / 128) * 20
                    app.min_cpu = ccpu
                app.save()
            logger.debug(u'publish.service. now add publish service ok')
            # 环境配置
            AppServiceEnv.objects.filter(service_key=app.service_key,
                                         app_version=app.app_version).delete()
            env_string = post_data.get('env_list')
            logger.info("env_list={}".format(env_string))
            if env_string != "" and env_string is not None:
                env_data = []
                env_list = env_string.split(";")
                for env in env_list:
                    name, attr_name, attr_value, scope, is_change = env.split(",")
                    app_env = AppServiceEnv(service_key=app.service_key,
                                            app_version=app.app_version,
                                            name=name,
                                            attr_name=attr_name.lstrip().rstrip(),
                                            attr_value=attr_value.lstrip().rstrip(),
                                            scope=scope,
                                            is_change=is_change,
                                            container_port=0 if is_change else -1)
                    env_data.append(app_env)
                # 批量增加
                AppServiceEnv.objects.bulk_create(env_data)
            logger.debug(u'publish.service. now add publish service env ok')
            # 端口配置
            AppServicePort.objects.filter(service_key=app.service_key,
                                          app_version=app.app_version).delete()
            port_string = post_data.get('port_list')
            if port_string != "" and port_string is not None:
                port_data = []
                port_list = port_string.split(";")
                for port in port_list:
                    container_port, protocol, port_alias, is_inner_service, is_outer_service = port.split(",")
                    if is_inner_service == "0":
                        is_inner_service = ""
                    if is_outer_service == "0":
                        is_outer_service = ""
                    app_port = AppServicePort(service_key=app.service_key,
                                              app_version=app.app_version,
                                              container_port=container_port.lstrip().rstrip(),
                                              protocol=protocol,
                                              port_alias=port_alias.lstrip().rstrip(),
                                              is_inner_service=is_inner_service,
                                              is_outer_service=is_outer_service)
                    port_data.append(app_port)
                AppServicePort.objects.bulk_create(port_data)
            logger.debug(u'publish.service. now add publish service port ok')
            
            ServiceExtendMethod.objects.filter(service_key=service_key, app_version=app_version).delete()
            extendMethod = {}
            extendMethod["service_key"] = service_key
            extendMethod["app_version"] = app_version
            extendMethod["min_node"] = minnode
            extendMethod["max_node"] = maxnode
            extendMethod["step_node"] = stepnode
            extendMethod["min_memory"] = minmemory
            extendMethod["max_memory"] = maxmemory
            extendMethod["step_memory"] = stepmemory
            if node_is_restart == "0":
                extendMethod["is_restart"] = False
            else:
                extendMethod["is_restart"] = True
            ServiceExtendMethod(**extendMethod).save()

            # 保存持久化设置
            if self.service.category == "application":
                volume_list = TenantServiceVolume.objects.filter(service_id=self.service.service_id)
                volume_data = []
                AppServiceVolume.objects.filter(service_key=app.service_key,
                                                app_version=app.app_version).delete()
                for volume in volume_list:
                    app_volume = AppServiceVolume(service_key=app.service_key,
                                                  app_version=app.app_version,
                                                  category=volume.category,
                                                  volume_path=volume.volume_path,
                                                  volume_type=volume.volume_type,
                                                  volume_name=volume.volume_name)
                    volume_data.append(app_volume)
                if len(volume_data) > 0:
                    AppServiceVolume.objects.bulk_create(volume_data)
            logger.debug(u'publish.service. now add publish service volume ok')

            return self.redirect_to('/apps/{0}/{1}/publish/relation/?service_key={2}&app_version={3}'.format(self.tenantName, self.serviceAlias, service_key, app_version))
        except Exception as e:
            logger.exception(e)
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
        service_key = request.GET.get('service_key')
        app_version = request.GET.get('app_version')
        # 查询基础服务,和当前用户发布的服务publisher in None,self.user.email
        app_list = AppService.objects.filter(Q(is_ok=True)).values('tenant_id', 'service_id', 'app_alias', 'service_key', 'app_version')
            
        # app_list = AppService.objects.filter(tenant_id=self.service.tenat_id, is_ok=True).values('tenant_id', 'service_id', 'app_alias', 'service_key', 'app_version')
            
        # 最新的纪录是之前新增的,获取service_key,app_version
        app = AppService.objects.get(service_key=service_key, app_version=app_version)
        # 获取所有可配置的服务列表
        # work_list = app_list.exclude(service_key=service_key, app_version=app_version)
        # 查询依赖关系
        suffix = AppServiceRelation.objects.filter(service_key=service_key,
                                                   app_version=app_version)
        prefix = AppServiceRelation.objects.filter(dep_service_key=service_key,
                                                   dep_app_version=app_version)
        context.update({
            'suffix': list(suffix),
            'prefix': list(prefix),
        })
        # 查询对应服务的名称等信息
        context.update({'relationlist': list(app_list),
                        'app': app})
        # 返回页面
        return TemplateResponse(self.request,
                                'www/service/publish_step_3.html',
                                context)

    # form提交.
    @perm_required('app_publish')
    def post(self, request, *args, **kwargs):
        # todo 需要添加form表单验证
        try:
            post_data = request.POST.dict()
            service_key = post_data.get('service_key')
            app_version = post_data.get('app_version')
            logger.debug("service.publish", "post_data is {0}".format(post_data))
            app = AppService.objects.get(service_key=service_key, app_version=app_version)
            # 保存当前服务依赖的其他服务
            relation_list = []
            pre_fix_string = post_data.get("prefix")
            logger.info("pre_fix_string={}".format(pre_fix_string))
            pre_fix_list = pre_fix_string.split(";")
            if pre_fix_list:
                for pre_fix in pre_fix_list:
                    if pre_fix:
                        pre_key, pre_version, pre_alias = pre_fix.split(",")
                        relation = AppServiceRelation(service_key=pre_key.lstrip().rstrip(),
                                                      app_version=pre_version.lstrip().rstrip(),
                                                      app_alias=pre_alias.lstrip().rstrip(),
                                                      dep_service_key=app.service_key,
                                                      dep_app_version=app.app_version,
                                                      dep_app_alias=app.app_alias)
                        relation_list.append(relation)
            AppServiceRelation.objects.filter(dep_service_key=app.service_key, dep_app_version=app.app_version).delete()
            # 保存依赖当前服务的发布服务
            suf_fix_string = post_data.get("suffix")
            logger.info("pre_fix_string={}".format(suf_fix_string))
            suf_fix_list = suf_fix_string.split(";")
            if suf_fix_list:
                for suf_fix in suf_fix_list:
                    if suf_fix:
                        suf_key, suf_version, suf_alias = suf_fix.split(",")
                        relation = AppServiceRelation(service_key=app.service_key,
                                                      app_version=app.app_version,
                                                      app_alias=app.app_alias,
                                                      dep_service_key=suf_key.lstrip().rstrip(),
                                                      dep_app_version=suf_version.lstrip().rstrip(),
                                                      dep_app_alias=suf_alias.lstrip().rstrip())
                        relation_list.append(relation)
            AppServiceRelation.objects.filter(service_key=app.service_key, app_version=app.app_version).delete()
    
            # 批量增加
            if len(relation_list) > 0:
                AppServiceRelation.objects.bulk_create(relation_list)
            
            app.dest_yb = False
            app.dest_ys = False
            app.save()
            # 事件
            if app.is_slug():
                self.upload_slug(app)
            elif app.is_image():
                self.upload_image(app)
            
            return self.redirect_to('/apps/{0}/{1}/detail/'.format(self.tenantName, self.serviceAlias))
        except Exception as e:
            logger.exception(e)
            return HttpResponse(u"发布过程出现异常", status=500)
    
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
