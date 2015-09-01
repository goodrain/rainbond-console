# -*- coding: utf8 -*-
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from www.auth import authenticate, login, logout
from www.forms.account import UserLoginForm, RegisterForm
from www.models import Users, Tenants, TenantServiceInfo, AnonymousUser, PermRelTenant, PermRelService, PhoneCode
from www.utils.mail import send_invite_mail_withHtml
from www.utils.crypt import AuthCode
from www.sms_service import send_phone_message
from www.api import RegionApi
from www.gitlab_http import GitlabApi
from www.db import BaseConnection
import datetime, time
import random
import re

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
        media = super(Login, self).get_media() + self.vendor('www/css/goodrainstyle.css', 'www/js/jquery.cookie.js')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/login.html', self.get_context())

    def redirect_view(self):
        tenants_has = PermRelTenant.objects.filter(user_id=self.user.pk)
        if tenants_has:
            tenant_pk = tenants_has[0].tenant_id
            tenant = Tenants.objects.get(pk=tenant_pk)
            tenant_name = tenant.tenant_name            
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


class Registation(BaseView):
    
    def get_context(self):
        context = super(Registation, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(Registation, self).get_media() + self.vendor('www/css/goodrainstyle.css', 'www/js/jquery.cookie.js')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/register.html', self.get_context())

    def init_for_region(self, region, tenant_name, tenant_id):
        api = RegionApi()
        res, body = api.create_tenant(region, tenant_name, tenant_id)
        return res, body

    def get(self, request, *args, **kwargs):
        self.form = RegisterForm()
        return self.get_response()
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def post(self, request, *args, **kwargs):
        querydict = request.POST
        querydict.update({u'real_captcha_code':request.session.get("captcha_code")})
        self.form = RegisterForm(querydict)        
        if self.form.is_valid():
            email = request.POST.get('email')
            nick_name = request.POST.get('nick_name')
            password = request.POST.get('password')
            tenant_name = request.POST.get('tenant')
            phone = request.POST.get('phone')
            user = Users(email=email, nick_name=nick_name, phone=phone, client_ip=self.get_client_ip(request))
            user.set_password(password)
            user.save()
            tenant = Tenants.objects.create(tenant_name=tenant_name, pay_type='free', creater=user.pk)
            PermRelTenant.objects.create(user_id=user.pk, tenant_id=tenant.pk, identity='admin')
            res, body = self.init_for_region(tenant.region, tenant_name, tenant.tenant_id)

             # create gitlab user
            git_user_id = gitClient.createUser(email, password, nick_name, nick_name)
            user.git_user_id = git_user_id
            user.save()

            user = authenticate(username=email, password=password)
            login(request, user)

            return redirect('/apps/{0}'.format(tenant.tenant_name))

        return self.get_response()

class InviteRegistation(BaseView):
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context(self):
        context = super(InviteRegistation, self).get_context()
        context.update({
            'form': self.form,
        })
        return context

    def get_media(self):
        media = super(InviteRegistation, self).get_media() + self.vendor('www/css/goodrainstyle.css', 'www/js/jquery.cookie.js')
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/register.html', self.get_context())

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
        if service.code_from != 'github' and git_project_id > 0 and user.git_user_id > 0:
            level = 10
            if identity == "viewer":
                level = 20
            elif identity == "developer":
                level = 30
            elif identity == "admin":
                level = 40
            gitClient.addProjectMember(git_project_id, user.git_user_id, level)

    def add_git_user(self, user, password):
        git_user_id = gitClient.createUser(user.email, password, user.nick_name, user.nick_name)
        user.git_user_id = git_user_id
        user.save()

    def get(self, request, *args, **kwargs):
        encoded_data = str(request.GET.get('key'))
        self.key = encoded_data
        logger.debug(self.key)
        data = AuthCode.decode(encoded_data, 'goodrain').split(',')
        logger.debug(data)
        # tenant member
        if len(data) == 3: 
            self.email, self.tenant_name = data[0:2]
            self.service_name = ""
        elif len(data) == 4:
            self.email, self.tenant_name, self.service_name = data[0:3]
        else:
            redirect('/register')
        try:
            if self.email.find("@") > 0:
                Users.objects.get(email=self.email)
            else:
                Users.objects.get(phone=self.email)
            return redirect('/login')
        except Users.DoesNotExist:
            curemail = ""
            curphone = ""
            if self.email.find("@"):
                curemail = self.email
            else:
                curphone = self.email            
            self.form = RegisterForm(
                initial={
                    "tenant":self.tenant_name,
                    "phone" : curphone,
                    "email":curemail
                }
            )
            return self.get_response()
        
    def post(self, request, *args, **kwargs):
        encoded_data = str(request.GET.get('key'))
        data = AuthCode.decode(encoded_data, 'goodrain').split(',')        
        querydict = request.POST
        querydict.update({u'invite_tag':"invite"})
        querydict.update({u'real_captcha_code':request.session.get("captcha_code")})
        self.form = RegisterForm(querydict)        
        if not self.form.is_valid():
            return self.get_response()
                
        email = request.POST.get('email')
        nick_name = request.POST.get('nick_name')
        password = request.POST.get('password')
        tenant_name = request.POST.get('tenant')
        phone = request.POST.get('phone')
        user = Users(email=email, nick_name=nick_name, phone=phone, client_ip=self.get_client_ip(request))
        user.set_password(password)
        user.save()
        
        if len(data) == 3:
            self.register_for_tenant(user, password, data)
        elif len(data) == 4:
            self.register_for_service(user, password, data)
        else:
            self.register_for_service(user, password, data)
        user = authenticate(username=email, password=password)
        login(request, user)
        return redirect('/apps/{0}'.format(tenant_name))

class PhoneCodeView(BaseView):
    
    def post(self, request, *args, **kwargs):
        result = {}
        phone = request.POST.get('phone')
        captcha_code = request.POST.get('captcha_code')
        real_captcha_code = request.session.get("captcha_code")
        logger.debug(captcha_code)
        logger.debug(real_captcha_code)
        if captcha_code != real_captcha_code:
            result["status"] = "errorcaptchacode"
            return JsonResponse(result) 
        
        if phone is not None:
            r = re.compile(r'^1[358]\d{9}$|^147\d{8}$')
            if not r.match(phone):
                result["status"] = "errorphone"
                return JsonResponse(result) 
        else:
            result["status"] = "errorphone"
            return JsonResponse(result) 
        try:
            phoneCodes = PhoneCode.objects.filter(phone=phone).order_by('-ID')[:1]
            if len(phoneCodes) > 0:
                phoneCode = phoneCodes[0]
                last = int(phoneCode.create_time.strftime("%s"))
                now = int(time.time())
                if now - last < 90:
                    result["status"] = "often"
                    return JsonResponse(result) 
            dsn = BaseConnection()
            query_time = datetime.datetime.now().strftime('%Y-%m-%d')
            query_sql = '''
                select count(1) as sendNumber from phone_code where phone = "{phone}" and create_time >= "{query_time}"
                '''.format(phone=phone, query_time=query_time + " 00:00:00")
            sqlobj = dsn.query(query_sql)
            if len(sqlobj) > 0:
                sendNumber = int(sqlobj[0]["sendNumber"])
                if sendNumber > 3:
                    result["status"] = "limited"
                    return JsonResponse(result) 
            phone_code = random.randrange(0, 1000001, 6)
            send_phone_message(phone, phone_code)
            newpc = PhoneCode(phone=phone, type="register", code=phone_code)
            newpc.save()
            result["status"] = "success"
            return JsonResponse(result) 
        except Exception as e:
            logger.exception(e)
        result["status"] = "error"
        return JsonResponse(result) 
