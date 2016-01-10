# -*- coding: utf8 -*-
import json
# from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http.response import HttpResponse

from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import Users, PermRelTenant, AppServiceInfo, ServiceInfo, TenantServiceRelation, App, Category
from www.forms.services import ServicePublishForm
from www.utils import increase_version
from www.service_http import RegionServiceApi

import logging
logger = logging.getLogger('default')


class TeamInfo(LeftSideBarMixin, AuthedView):

    def get_context(self):
        context = super(TeamInfo, self).get_context()
        context.update({
            'perm_users': self.get_user_perms(),
            'tenantName': self.tenantName,
        })
        context["teamStatus"] = "active"
        return context

    def get_media(self):
        media = super(TeamInfo, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/service.js',
            'www/js/gr/basic.js', 'www/css/gr/basic.css', 'www/js/perms.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js'
        )
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/team.html', self.get_context())

    def get_user_perms(self):
        perm_users = []
        perm_template = {
            'name': None,
            'adminCheck': False,
            'developerCheck': False, 'developerDisable': False,
            'viewerCheck': False, 'viewerDisable': False
        }

        identities = PermRelTenant.objects.filter(tenant_id=self.tenant.pk)
        for i in identities:
            user_perm = perm_template.copy()
            user_perm['name'] = Users.objects.get(pk=i.user_id).nick_name
            if i.identity == 'admin':
                user_perm.update({
                    'adminCheck': True,
                    'developerCheck': True, 'developerDisable': True,
                    'viewerCheck': True, 'viewerDisable': True
                })
            elif i.identity == 'developer':
                user_perm.update({
                    'developerCheck': True,
                    'viewerCheck': True, 'viewerDisable': True
                })
            elif i.identity == 'viewer':
                user_perm.update({
                    'viewerCheck': True
                })

            perm_users.append(user_perm)

        return perm_users

    @perm_required('tenant_access')
    def get(self, request, *args, **kwargs):
        return self.get_response()


class ServicePublishView(LeftSideBarMixin, AuthedView):

    def get_context(self):
        context = super(ServicePublishView, self).get_context()
        # context.update({
        #    'form': self.form,
        #})
        return context

    def get_media(self):
        media = super(ServicePublishView, self).get_media(
        ) + self.vendor('www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/validator.min.js', 'www/js/gr/app_publish.js')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/service/publish.html', self.get_context())

    def prepare_app_update(self, last_pub_version):
        app = ServiceInfo.objects.get(service_key=last_pub_version.service_key)
        form_init_data = {
            'app_key': {"value": app.service_key, "attrs": {"readonly": True}},
            'app_name': {"value": app.service_name, "attrs": {"readonly": True}},
            'app_version': {"value": increase_version(last_pub_version.app_version, 1)},
            'app_info': {"value": app.info},
            'pay_type': {"value": last_pub_version.pay_type},
            'price': {"value": last_pub_version.price},
        }
        return form_init_data

    @perm_required('sys_admin')
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        published_versions = AppServiceInfo.objects.filter(service_id=self.service.service_id).order_by('-create_time')
        if published_versions:
            last_pub_version = published_versions[0]
            form_init_data = self.prepare_app_update(last_pub_version)
            #self.form = ServicePublishForm(initial=form_init_data, is_update=True)
            context.update({"fields": form_init_data, "isinit": False})
        else:
            #self.form = ServicePublishForm()
            context.update({"fields": {}, "isinit": True})
        root_categories = Category.objects.only('ID', 'name').filter(parent=0)
        root_category_list = [{"id": x.pk, "display_name": x.name} for x in root_categories]
        context['root_category_list'] = root_category_list
        return TemplateResponse(self.request, 'www/service/publish.html', context)

    @perm_required('sys_admin')
    def post(self, request, *args, **kwargs):
        self.form = ServicePublishForm(request.POST)
        if not self.form.is_valid():
            return self.get_response()

        post_data = request.POST.dict()
        logger.debug("service.publish", "post_data is {0}".format(post_data))
        if 'publish' in post_data:
            action = 'app_publish'
        elif 'update' in post_data:
            action = 'app_update'
        else:
            return HttpResponse("error", status=500)

        func = getattr(self, action)
        try:
            success = func(post_data)
            if success:
                return self.redirect_to('/apps/{0}/{1}/detail/'.format(self.tenantName, self.serviceAlias))
            else:
                logger.error('service.publish', "{} failed".format(action))
                return HttpResponse(u"发布过程出现异常", status=500)
        except Exception, e:
            logger.exception('service.publish', e)
            return HttpResponse(u"应用发布失败", status=500)

    def app_publish(self, post_data):
        try:
            app = self._add_new_app(post_data, self.service)
            new_version = self.create_new_version(app, post_data, self.service)
            app.save()
            event_id = self.create_publish_event()
            if new_version.is_slug():
                self.upload_slug(new_version, event_id)
            elif new_version.is_image():
                self.upload_image(new_version, event_id)
            return True
        except Exception, e:
            logger.exception('service.publish', e)
            return False

    def app_update(self, post_data):
        try:
            app = self._update_app(post_data, self.service)
            new_version = self.create_new_version(app, post_data, self.service)
            app.save()
            event_id = self.create_publish_event()
            if new_version.is_slug():
                self.upload_slug(new_version, event_id)
            elif new_version.is_image():
                self.upload_image(new_version, event_id)
            return True
        except Exception, e:
            logger.exception('service.publish', e)
            return False

    def _add_new_app(self, d, pub_service):
        try:
            app = ServiceInfo(service_key=d['app_key'], publisher=self.user.nick_name, service_name=d['app_name'], info=d['app_info'],
                              status="test", category="app_publish", version=d['app_version'], creater=self.user.pk)
            app = self.copy_public_properties(pub_service, app)
            app.dependecy = self.get_pub_srv_deps(pub_service)
            App.objects.create(name=app.service_name, description=app.info, service_key=app.service_key, category_id=d['app_type_third'],
                               pay_type=d['pay_type'], using=0, creater=self.user.pk)
            return app
        except Exception, e:
            raise e

    def _update_app(self, d, pub_service):
        app = ServiceInfo.objects.get(service_key=d['app_key'])
        app.info = d['app_info']
        app.version = d['app_version']
        app.service_name = d['app_name']
        app.dependecy = self.get_pub_srv_deps(pub_service)
        return app

    def create_new_version(self, app, d, pub_service):
        new_version = AppServiceInfo(service_key=app.service_key, service_id=pub_service.service_id, pay_type=d['pay_type'], price=d['price'],
                                     deploy_version=pub_service.deploy_version, app_version=d['app_version'], change_log=d['change_log'], creater=self.user.pk)
        new_version = self.copy_public_properties(pub_service, new_version)
        new_env = self.extend_env(new_version, pub_service)
        new_version.env = new_env
        new_version.save()
        app.env = new_env
        return new_version

    def copy_public_properties(self, copy_from, to):
        for field in ('is_service', 'is_web_service', 'image', 'extend_method', 'cmd', 'setting', 'env',
                      'min_node', 'min_cpu', 'min_memory', 'inner_port', 'volume_mount_path', 'service_type'):
            if hasattr(to, field) and hasattr(copy_from, field):
                setattr(to, field, getattr(copy_from, field))
        return to

    def extend_env(self, app_version, pub_service):
        if pub_service.image.startswith('goodrain.me/runner'):
            SLUG_PATH = '/app_publish/{0}/{1}.tgz'.format(app_version.service_key, pub_service.deploy_version)
            return app_version.env.rstrip(',') + ',SLUG_PATH=' + SLUG_PATH + ','
        else:
            return app_version.env

    def get_pub_srv_deps(self, pub_service):
        deps = TenantServiceRelation.objects.filter(service_id=pub_service.service_id)
        if deps:
            dep_service_keys = list(set([e.dep_service_type for e in deps]))
            return ','.join(dep_service_keys)
        else:
            return ""

    def create_publish_event(self):
        template = {
            "user_id": self.user.nick_name,
            "tenant_id": self.service.tenant_id,
            "service_id": self.service.service_id,
            "type": "publish",
            "desc": u"应用发布中...",
            "show": True,
        }
        try:
            r = RegionServiceApi()
            body = r.create_event(self.service.service_region, json.dumps(template))
            return body.event_id
        except Exception, e:
            logger.exception("service.publish", e)
            return None

    def upload_slug(self, new, event_id):
        oss_upload_task = {
            "app_key": new.service_key, "service_id": new.service_id,
            "deploy_version": new.deploy_version, "tenant_id": self.service.tenant_id,
            "action": "create_new_version", "event_id": event_id
        }
        try:
            delete_models = AppServiceInfo.objects.only('deploy_version').filter(service_key=new.service_key, deploy_num=0).exclude(app_version=new.app_version)
            if delete_models:
                oss_upload_task['delete_versions'] = [e.deploy_version for e in delete_models]
            r = RegionServiceApi()
            r.send_task(self.service.service_region, 'app_slug', json.dumps(oss_upload_task))
            delete_models.delete()
        except Exception, e:
            logger.error("service.publish", "upload_slug for {0}({1}), but an error occurred".format(new.service_key, new.app_version))
            logger.exception("service.publish", e)

    def upload_image(self, new, event_id):
        image_upload_task = {
            "action": "create_new_version", "image": new.image, "event_id": event_id
        }

        try:
            delete_models = AppServiceInfo.objects.only('deploy_version').filter(service_key=new.service_key, deploy_num=0).exclude(app_version=new.app_version)
            if delete_models:
                image_upload_task['delete_versions'] = [e.deploy_version for e in delete_models]
            r = RegionServiceApi()
            r.send_task(self.service.service_region, 'app_image', json.dumps(image_upload_task))
            delete_models.delete()
        except Exception, e:
            logger.error("service.publish", "upload_image for {0}({1}), but an error occurred".format(new.service_key, new.app_version))
            logger.exception("service.publish", e)
