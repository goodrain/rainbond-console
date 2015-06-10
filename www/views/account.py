# -*- coding: utf8 -*-
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from www.auth import authenticate, login, logout
from www.forms.account import UserLoginForm, InviteUserForm, InviteRegForm, InviteRegForm2, RegisterForm, SendInviteForm
from www.models import Users, Tenants, TenantServiceInfo, AnonymousUser, PermRelTenant, PermRelService
from www.utils.mail import MailUtil
from www.utils.crypt import AuthCode
from www.api import RegionApi
from www.gitlab_http import GitlabApi

from base import BaseView

import hashlib

import logging
logger = logging.getLogger('default')

gitClient = GitlabApi()


class Login(BaseView):
    def get_context(self):
        context = super(Login, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(Login, self).get_media()
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/login.html', self.get_context())

    def redirect_view(self):
        tenants_has = PermRelTenant.objects.filter(user_id=self.user.pk)
        if tenants_has:
            tenant_pk = tenants_has[0].tenant_id
            tenant_name = Tenants.objects.get(pk=tenant_pk).tenant_name
            return redirect('/apps/{0}'.format(tenant_name))
        else:
            return Http404

    def get(self, request, *args, **kwargs):
        user = request.user
        if isinstance(user, AnonymousUser):
            self.form = UserLoginForm()
            return self.get_response()
        else:
            time = request.GET.get('time', '')
            return_to = request.GET.get('return_to', '')
            if return_to is not None and return_to != "" and return_to.find("?") == -1:
                tmp = user.email + time + "20616aea2c1136cda6701dd13d5c71"
                d5 = hashlib.md5(tmp.encode("UTF-8")).hexdigest()
                url = return_to + "?username=" + user.email + "&time=" + time + "&token=" + d5
                logger.debug(d5)
                logger.debug(url)
                return redirect(url)
            else:
                return self.redirect_view()

    @never_cache
    def post(self, request, *args, **kwargs):
        self.form = UserLoginForm(request.POST)
        next_url = request.GET.get('next', None)
        username = request.POST.get('email')
        password = request.POST.get('password')

        if not self.form.is_valid():
            logger.error("login form is not right: %s" % self.form.errors)
            return self.get_response()
        user = authenticate(username=username, password=password)
        login(request, user)
        
        # create git user
        if user.git_user_id == 0:            
            git_user_id = gitClient.createUser(username, password, user.nick_name, user.nick_name)
            user.git_user_id = git_user_id
            user.save()
        
        if next_url is not None:
            return redirect(next_url)
        else:
            return self.redirect_view()


class Index(Login):
    def get(self, request, *args, **kwargs):
        user = request.user
        if isinstance(user, AnonymousUser):
            return redirect('/login')
        else:
            return self.redirect_view()

    def post(self, request, *args, **kwargs):
        return HttpResponse("POST METHOD IS NOT ALLOWED")


class Logout(BaseView):
    def init_request(self, *args, **kwargs):
        self.template = 'www/logout.html'

    def get_context(self):
        context = super(Logout, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(Logout, self).get_media()
        return media

    def get_response(self):
        return TemplateResponse(self.request, self.template, self.get_context())

    def get(self, request, *args, **kwargs):
        user = request.user
        if isinstance(user, AnonymousUser):
            return HttpResponse("未登录状态, 不需注销")
        else:
            logout(request)
            return redirect(settings.LOGIN_URL)

    @never_cache
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect(settings.LOGIN_URL)


class InviteUser(BaseView):
    def get_context(self):
        context = super(InviteUser, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(InviteUser, self).get_media() + self.vendor('www/css/userform.css')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/invite.html', self.get_context())

    def invite_link(self, email, tenant_name):
        domain = self.request.META.get('HTTP_HOST')
        mail_body = AuthCode.encode(tenant_name + ',' + email, 'goodrain')
        return 'http://{0}/invite?key={1}'.format(domain, mail_body)

    def get(self, request, *args, **kwargs):
        self.form = InviteUserForm()
        return self.get_response()

    def post(self, request, *args, **kwargs):
        self.form = InviteUserForm(request.POST)
        if self.form.is_valid():
            email = request.POST.get('email')
            tenant_name = request.POST.get('tenant')            
            #mailUtil = MailUtil()
            #content = mailUtil.get_inviteContent(self.invite_link(email, tenant_name))
            #mailUtil.send_invite_mail_withHtml(email, content)
            return redirect('/test/raster/')
        return self.get_response()


class InviteRegistation(BaseView):
    def get_context(self):
        context = super(InviteRegistation, self).get_context()
        context.update({
            'form': self.form,
            # 'tenant_name': self.tenant_name,
            'email': self.email,
        })
        return context

    def get_media(self):
        media = super(InviteRegistation, self).get_media()
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/register.html', self.get_context())

    def init_for_region(self, tenant_name, tenant_id):
        api = RegionApi()
        res, body = api.create_tenant(tenant_name, tenant_id)
        return res, body

    def create_new_tenant(self, user, password, tenant_name):
        tenant = Tenants.objects.create(tenant_name=tenant_name, pay_type='free')
        PermRelTenant.objects.create(user_id=user.pk, tenant_id=tenant.pk, identity='admin')
        res, body = self.init_for_region(tenant_name, tenant.tenant_id)
        self.add_git_user(user, password)

    def register_for_tenant(self, user, password, data):
        email, tenant_name, identity = data
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        PermRelTenant.objects.create(user_id=user.pk, tenant_id=tenant.pk, identity=identity)
        self.add_git_user(user, password)

    def register_for_service(self, user, password, data):
        email, tenant_name, service_alias, identity = data
        tenant = Tenants.objects.get(tenant_name=tenant_name)
        service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=service_alias)
        PermRelService.objects.create(user_id=user.pk, service_id=service.pk, identity=identity)

        perm_t, created = PermRelTenant.objects.get_or_create(user_id=user.pk, tenant_id=tenant.pk)
        if created:
            perm_t.identity = 'access'
            perm_t.save()
            self.add_git_user(user, password)

        git_project_id = service.git_project_id
        if git_project_id > 0 and user.git_user_id > 0:
            gitClient.addProjectMember(git_project_id, user.git_user_id)

    def add_git_user(self, user, password):
        git_user_id = gitClient.createUser(user.email, password, user.nick_name, user.nick_name)
        user.git_user_id = git_user_id
        user.save()

    def get(self, request, *args, **kwargs):
        encoded_data = str(request.GET.get('key'))
        data = AuthCode.decode(encoded_data, 'goodrain').split(',')
        new_tenant = False

        if len(data) == 1:
            new_tenant = True
            self.email = data[0]
        else:
            self.email, self.tenant_name = data[0:2]
        try:
            Users.objects.get(email=self.email)
            return redirect('/login')
        except Users.DoesNotExist:
            if new_tenant:
                self.form = InviteRegForm2()
            else:
                self.form = InviteRegForm()
            return self.get_response()

    def post(self, request, *args, **kwargs):
        encoded_data = str(request.GET.get('key'))
        data = AuthCode.decode(encoded_data, 'goodrain').split(',')

        if len(data) == 1:
            self.form = InviteRegForm2(request.POST)
            self.email = data[0]
        else:
            self.email, self.tenant_name = data[0:2]
            self.form = InviteRegForm(request.POST)

        if not self.form.is_valid():
            logger.error(self.form.errors)
            return self.get_response()
        nick_name = request.POST.get('nick_name')
        password = request.POST.get('password')
        user = Users(email=self.email, nick_name=nick_name, origion='invitation')
        user.set_password(password)
        user.save()

        if len(data) == 3:
            self.register_for_tenant(user, password, data)
        elif len(data) == 4:
            self.register_for_service(user, password, data)
        elif len(data) == 1:
            self.tenant_name = request.POST.get('tenant')
            self.create_new_tenant(user, password, self.tenant_name)

        user = authenticate(username=self.email, password=password)
        login(request, user)

        return redirect('/apps/{0}'.format(self.tenant_name))


class Registation(BaseView):
    def get_context(self):
        context = super(Registation, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(Registation, self).get_media() + self.vendor('www/css/okooostyle.css')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/register.html', self.get_context())

    def init_for_region(self, tenant_name, tenant_id):
        api = RegionApi()
        res, body = api.create_tenant(tenant_name, tenant_id)
        return res, body

    def get(self, request, *args, **kwargs):
        self.form = RegisterForm()
        return self.get_response()

    def post(self, request, *args, **kwargs):
        self.form = RegisterForm(request.POST)
        if self.form.is_valid():
            email = request.POST.get('email')
            nick_name = request.POST.get('nick_name')
            password = request.POST.get('password')
            tenant_name = request.POST.get('tenant')
            user = Users(email=email, nick_name=nick_name)
            user.set_password(password)
            user.save()
            tenant = Tenants.objects.create(tenant_name=tenant_name, pay_type='free')
            PermRelTenant.objects.create(user_id=user.pk, tenant_id=tenant.pk, identity='admin')
            res, body = self.init_for_region(tenant_name, tenant.tenant_id)

             # create gitlab user
            git_user_id = gitClient.createUser(email, password, nick_name, nick_name)
            user.git_user_id = git_user_id
            user.save()

            user = authenticate(username=email, password=password)
            login(request, user)

            return redirect('/apps/{0}'.format(tenant.tenant_name))

        return self.get_response()


class SendInviteView(BaseView):
    def get_context(self):
        context = super(SendInviteView, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(SendInviteView, self).get_media() + self.vendor('www/css/okooostyle.css')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/register.html', self.get_context())

    def invite_link(self, email):
        domain = self.request.META.get('HTTP_HOST')
        mail_body = AuthCode.encode(email, 'goodrain')
        return 'http://{0}/invite?key={1}'.format(domain, mail_body)

    def get(self, request, *args, **kwargs):
        self.form = SendInviteForm()
        return self.get_response()

    def post(self, request, *args, **kwargs):
        self.form = SendInviteForm(request.POST)
        if self.form.is_valid():
            email = request.POST.get('email')
            #mailUtil = MailUtil()
            #content = mailUtil.get_inviteContent(self.invite_link(email))
            #mailUtil.send_invite_mail_withHtml(email, content)            
            return HttpResponse("邀请邮件已发送")
        return self.get_response()
