# -*- coding: utf8 -*-
from base import BaseView
from django.template.response import TemplateResponse
from django.contrib.auth.models import User as OAuthUser
import logging
import datetime
from www.forms.wizard import AdminForm
from www.region import RegionInfo
from www.models import *
from www.app_http import AppServiceApi
from www.utils.netutil import get_client_ip
from www.monitorservice.monitorhook import MonitorHook
from www.tenantservice.baseservice import CodeRepositoriesService
from www.auth import authenticate, login

logger = logging.getLogger("default")
monitorhook = MonitorHook()
appClient = AppServiceApi()
codeRepositoriesService = CodeRepositoriesService()


class PrefixView(BaseView):
    """向导前置"""
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        return TemplateResponse(request,
                                'www/wizard/prefix.html',
                                context)
        # def post(self, request, *args, **kwargs):


class WizardView(BaseView):
    """注册管理员"""
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context["form"] = AdminForm()
        return TemplateResponse(request,
                                'www/wizard/admin.html',
                                context)

    def post(self, request, *args, **kwargs):
        """注册管理员"""
        admin_form = AdminForm(request.POST)
        import datetime
        if admin_form.is_valid():
            email = request.POST.get('email')
            nick_name = request.POST.get('nick_name')
            password = request.POST.get('password')
            password_repeat = request.POST.get('password_repeat')
            region = request.POST.get('machine_region')
            if region is None or region == "" or region == "1":
                region = RegionInfo.register_choices()[0][0]
            # 租户信息
            tenant_name = nick_name
            # 清理之前所有的租户
            tenant_count = Tenants.objects.all().count()
            if tenant_count > 0:
                logger.error("account.register", "租户已存在，请先清理租户!")
                context = self.get_context()
                admin_form.add_error("", "租户已存在，请先清理租户!")
                context["form"] = admin_form
                return TemplateResponse(request,
                                        'www/wizard/admin.html',
                                        context)
                # Tenants.objects.all().delete()
            # 添加用户
            user = Users(email=email,
                         nick_name=nick_name,
                         client_ip=get_client_ip(request),
                         rf='admin')
            user.set_password(password)
            user.save()
            monitorhook.registerMonitor(user, 'register')
            # 添加django用户
            tmpname = nick_name + "_token"
            oauth_user = OAuthUser.objects.create(username=tmpname)
            oauth_user.set_password(password)
            oauth_user.is_staff = True
            oauth_user.save()
            # 添加租户
            expired_day = 7
            if hasattr(settings, "TENANT_VALID_TIME"):
                expired_day = int(settings.TENANT_VALID_TIME)
            expire_time = datetime.datetime.now() + datetime.timedelta(days=expired_day)
            # 管理员默认为付费企业用户
            tenant = Tenants.objects.create(
                tenant_name=tenant_name,
                pay_type='payed',
                pay_level='company',
                creater=user.pk,
                region=region,
                expired_time=expire_time.strftime('%Y-%m-%d %H:%M:%S'))
            monitorhook.tenantMonitor(tenant, user, "create_tenant", True)
            # 租户－用户关系
            PermRelTenant.objects.create(user_id=user.pk, tenant_id=tenant.pk, identity='admin')
            logger.info("account.register", "new registation, nick_name: {0}, tenant: {1}, region: {2}, tenant_id: {3}".format(nick_name, tenant_name, region, tenant.tenant_id))

            TenantRegionInfo.objects.create(tenant_id=tenant.tenant_id, region_name=tenant.region)
            # create gitlab user
            if user.email is not None and user.email != "":
                codeRepositoriesService.createUser(user, email, password, nick_name, nick_name)

            # 登录系统
            user = authenticate(username=nick_name, password=password)
            login(request, user)

            # 发送数据到app进行注册
            data = {
                "username": nick_name,
                "email": email,
                "password": password,
            }
            json_data = json.dumps(data)

            for num in range(0, 3):
                res, body = appClient.post_admin_info(json_data)
                logger.debug("account.register", res)
                logger.debug("account.register", body)
                if res.status == 200:
                    logger.debug("account.register", "register app success!")
                    break
                else:
                    logger.error("account.register", "register app failed! try again!num:{0}".format(num))

            url = '/apps/{0}'.format(tenant_name)
            if settings.MODULES["Package_Show"]:
                selected_pay_level = ""
                pl = request.GET.get("pl", "")
                region_levels = pl.split(":")
                if len(region_levels) == 2:
                    selected_pay_level = region_levels[1]
                url = '/payed/{0}/select?selected={1}'.format(tenant_name, selected_pay_level)
            logger.debug(url)
            return self.redirect_to(url)
        else:
            context = self.get_context()
            context["form"] = admin_form
            return TemplateResponse(request,
                                    'www/wizard/admin.html',
                                    context)

