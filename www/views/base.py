# -*- coding: utf8 -*-
from functools import update_wrapper
from django.forms import Media
from django.http import Http404
from django.utils.decorators import classonlymethod
from django.views.generic import View

from django.conf import settings

if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
    from django.contrib.staticfiles.templatetags.staticfiles import static
else:
    from django.templatetags.static import static

from goodrain_web.errors import PermissionDenied
from www.perms import check_perm
from www.models import Tenants, TenantServiceInfo

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
        return static(path)

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

            return handler(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())
        #view.need_site_permission = cls.need_site_permission

        return view

    def init_request(self, *args, **kwargs):
        pass


class AuthedView(BaseView):

    def __init__(self, request, *args, **kwargs):
        self.tenantName = kwargs.get('tenantName', None)
        self.serviceAlias = kwargs.get('serviceAlias', None)

        if self.tenantName is not None:
            try:
                self.tenant = Tenants.objects.get(tenant_name=self.tenantName)
            except Tenants.DoesNotExist:
                logger.error("Tenant {0} is not exists".format(self.tenantName))
                raise Http404

            if self.serviceAlias is not None:
                try:
                    self.service = TenantServiceInfo.objects.get(tenant_id=self.tenant.tenant_id, service_alias=self.serviceAlias)
                except TenantServiceInfo.DoesNotExist:
                    logger.debug("Tenant {0} ServiceAlias {1} is not exists".format(self.tenantName, self.serviceAlias))
                    raise Http404

        BaseView.__init__(self, request, *args, **kwargs)

    def has_perm(self, perm):
        try:
            if check_perm(perm, self.user, self.tenantName, self.serviceAlias):
                return True
            else:
                return False
        except PermissionDenied:
            return False
