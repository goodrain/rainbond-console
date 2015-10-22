# -*- coding: utf8 -*-
from functools import update_wrapper
from django.forms import Media
from django.http import Http404
from django.utils.decorators import classonlymethod
from django.views.generic import View
from django.shortcuts import redirect

from django.conf import settings

if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
    from django.contrib.staticfiles.templatetags.staticfiles import static
else:
    from django.templatetags.static import static

from goodrain_web.errors import PermissionDenied
from www.perms import check_perm
from www.models import Tenants, TenantServiceInfo
from www.tenantservice.baseservice import BaseTenantService
from www.version import STATIC_VERSION
from www.region import RegionInfo
from www.utils.url import get_redirect_url

import logging

logger = logging.getLogger('default')


class BaseObject(object):
    #@filter_hook

    def get_context(self):
        return {'media': self.media}

    @property
    def media(self):
        return self.get_media()

    #@filter_hook
    def get_media(self):
        return Media()

    def static(self, path):
        return static(path) + '?v={0}'.format(STATIC_VERSION)

    def vendor(self, *tags):
        media = Media()
        for tag in tags:
            file_type = tag.split('.')[-1]
            files = self.static(tag)
            if file_type == 'js':
                media.add_js([files])
            elif file_type == 'css':
                media.add_css({'screen': [files]})
        return media


class BaseView(BaseObject, View):

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.request_method = request.method.lower()
        self.args = args
        self.kwargs = kwargs
        self.user = request.user
        self.init_request(*args, **kwargs)

    @classonlymethod
    def as_view(cls):
        def view(request, *args, **kwargs):
            self = cls(request, *args, **kwargs)

            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get

            if self.request_method in self.http_method_names:
                handler = getattr(
                    self, self.request_method, self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            response = handler(request, *args, **kwargs)
            return self.update_response(response)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())
        #view.need_site_permission = cls.need_site_permission

        return view

    def update_response(self, response):
        return response

    def init_request(self, *args, **kwargs):
        pass

    def redirect_to(self, path, *args, **kwargs):
        full_url = get_redirect_url(path, request=self.request)
        return redirect(full_url, *args, **kwargs)


class AuthedView(BaseView):

    def __init__(self, request, *args, **kwargs):
        self.tenantName = kwargs.get('tenantName', None)
        self.serviceAlias = kwargs.get('serviceAlias', None)

        if self.tenantName is not None:
            try:
                self.tenant = Tenants.objects.get(tenant_name=self.tenantName)
            except Tenants.DoesNotExist:
                logger.error(
                    "Tenant {0} is not exists".format(self.tenantName))
                raise Http404

            if self.serviceAlias is not None:
                try:
                    self.service = TenantServiceInfo.objects.get(
                        tenant_id=self.tenant.tenant_id, service_alias=self.serviceAlias)
                except TenantServiceInfo.DoesNotExist:
                    logger.debug("Tenant {0} ServiceAlias {1} is not exists".format(
                        self.tenantName, self.serviceAlias))
                    raise Http404

        BaseView.__init__(self, request, *args, **kwargs)

    def get_context(self):
        context = super(AuthedView, self).get_context()
        context['tenantName'] = self.tenantName
        context['serviceAlias'] = self.serviceAlias
        return context

    def has_perm(self, perm):
        try:
            if check_perm(perm, self.user, self.tenantName, self.serviceAlias):
                return True
            else:
                return False
        except PermissionDenied:
            return False


class LeftSideBarMixin(object):

    def __init__(self, *args, **kwargs):
        super(LeftSideBarMixin, self).__init__(*args, **kwargs)
        if hasattr(self, 'tenant') and hasattr(self, 'user'):
            pass
        else:
            raise ImportWarning(
                "LeftSideBarMixin should inherit before AuthedView")

        self.cookie_region = self.request.COOKIES.get('region', None)
        self.response_region = self.tenant.region if self.cookie_region is None else self.cookie_region

    def update_response(self, response):
        if self.response_region != self.cookie_region:
            response.set_cookie('region', self.response_region)
        return response

    def get_context(self):
        context = super(LeftSideBarMixin, self).get_context()
        context['tenantServiceList'] = self.get_service_list()
        context = self.set_region_info(context)
        return context

    def set_region_info(self, context):
        arrival_regions = []
        for region in RegionInfo.region_list:
            if region['name'] == self.response_region:
                context['current_region'] = region
            else:
                if region['name'] == 'aws-bj-1':
                    if self.tenant.region != 'aws-bj-1':
                        continue
                arrival_regions.append(region)

        context['arrival_regions'] = tuple(arrival_regions)
        return context

    def get_service_list(self):
        baseService = BaseTenantService()
        services = baseService.get_service_list(
            self.tenant.pk, self.user.pk, self.tenant.tenant_id, region=self.response_region)
        for s in services:
            if s.service_alias == self.serviceAlias:
                s.is_selected = True
                break

        return services
