# -*- coding: utf8 -*-
from functools import update_wrapper
from django.forms import Media
from django import http
from django.utils.decorators import classonlymethod
from django.views.generic import View
from django.shortcuts import redirect
from django.views.generic.base import RedirectView
from django.conf import settings
from goodrain_web.custom_config import custom_config
from django.core.exceptions import PermissionDenied
from www.perms import check_perm
from www.models import Tenants, TenantServiceInfo, AnonymousUser, PermRelTenant
from www.version import STATIC_VERSION
from www.utils.url import get_redirect_url
from www.utils import sn
from www.utils.license import LICENSE
import logging
from www.region import RegionInfo
if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
    from django.contrib.staticfiles.templatetags.staticfiles import static
else:
    from django.templatetags.static import static

logger = logging.getLogger('default')


class GrRedirectView(RedirectView):
    @classmethod
    def as_view(cls, **initkwargs):
        if 'permanent' not in initkwargs:
            initkwargs['permanent'] = True

        return super(GrRedirectView, cls).as_view(**initkwargs)

    def get(self, request, *args, **kwargs):
        url = get_redirect_url(self.url, request)
        if url:
            if self.permanent:
                return http.HttpResponsePermanentRedirect(url)
            else:
                return http.HttpResponseRedirect(url)
        else:
            logger.warning(
                'Gone: %s',
                request.path,
                extra={'status_code': 410,
                       'request': request})
            return http.HttpResponseGone()


class BaseObject(object):
    # @filter_hook

    def get_context(self):
        return {'media': self.media}

    @property
    def media(self):
        return self.get_media()

    # @filter_hook
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
                handler = getattr(self, self.request_method,
                                  self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            # 判断license是否过期 更改判断方式
            try:
                is_lisence_expired = LICENSE.is_expired()
                if is_lisence_expired and request.path != "/license":
                    return self.redirect_to('/license')
            except Exception as e:
                logger.exception(e)
                return self.redirect_to('/license?errMsg')

            if request.user.is_authenticated() and request.path != "/logout":
                user_id = request.user.user_id
                prt_num = PermRelTenant.objects.filter(user_id=user_id).count()
                if prt_num == 0:
                    logger.warning(
                        "account.login",
                        "user:{0} does not have any tenant,pls relogin!".
                        format(user_id))
                    return self.redirect_to("/logout")

                if settings.MODULES.get('SSO_LOGIN'):
                    cookies_sso_uid = request.COOKIES.get('uid')
                    if request.user.sso_user_id != cookies_sso_uid:
                        return self.redirect_to('/logout')

            response = handler(request, *args, **kwargs)
            return self.update_response(response)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())
        # view.need_site_permission = cls.need_site_permission

        return view

    def update_response(self, response):
        return response

    def init_request(self, *args, **kwargs):
        pass

    def redirect_to(self, path, *args, **kwargs):
        full_url = get_redirect_url(path, request=self.request)
        return redirect(full_url, *args, **kwargs)

    def get_context(self):
        context = super(BaseView, self).get_context()
        context['CUSTOM_CONFIG'] = custom_config.configs()
        return context


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
                raise http.Http404

            if self.serviceAlias is not None:
                try:
                    self.service = TenantServiceInfo.objects.get(
                        tenant_id=self.tenant.tenant_id,
                        service_alias=self.serviceAlias)
                    if self.service.service_region not in RegionInfo.valid_regions():
                        raise PermissionDenied
                except TenantServiceInfo.DoesNotExist:
                    logger.debug("Tenant {0} ServiceAlias {1} is not exists".
                                 format(self.tenantName, self.serviceAlias))
                    raise http.Http404

        BaseView.__init__(self, request, *args, **kwargs)

    def get_context(self):
        context = super(AuthedView, self).get_context()
        context['tenantName'] = self.tenantName
        context["tenant_pay_type"] = self.tenant.pay_type
        context['serviceAlias'] = self.serviceAlias
        context['MODULES'] = settings.MODULES
        context['is_private'] = sn.instance.is_private()
        return context

    def has_perm(self, perm):
        try:
            if check_perm(perm, self.user, self.tenantName, self.serviceAlias):
                return True
            else:
                return False
        except PermissionDenied:
            return False


class PluginView(BaseView):
    def __init__(self, request, *args, **kwargs):
        super(PluginView, self).__init__(request, *args, **kwargs)
        self.plugin_id = kwargs.get('plugin_id', None)




class CAdminView(BaseView):
    """是否有权限访问cadmin模块"""

    def __init__(self, request, *args, **kwargs):
        BaseView.__init__(self, request, *args, **kwargs)
        if isinstance(request.user, AnonymousUser):
            raise http.Http404
        if not request.user.is_sys_admin:
            if request.user.user_id == 1:
                pass
            else:
                raise http.Http404

    def get_context(self):
        context = super(CAdminView, self).get_context()
        context['MODULES'] = settings.MODULES
        context['is_private'] = sn.instance.is_private()
        return context
