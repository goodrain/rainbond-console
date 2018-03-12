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
from www.services import enterprise_svc
from www.utils.conf_tool import regionConfig

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

            # 企业名称
            enter_alias = request.POST.get('enter_alias', '')

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

            regions = regionConfig.regions()
            if region not in [r['name'] for r in regions]:
                logger.error("account.register", "配置文件中未找到待初始化的数据中心配置信息!")
                context = self.get_context()
                admin_form.add_error("", "配置文件中未找到待初始化的数据中心配置信息!")
                context["form"] = admin_form
                return TemplateResponse(request,
                                        'www/wizard/admin.html',
                                        context)

            # 添加本地企业信息
            enterprise = enterprise_svc.create_enterprise(enterprise_alias=enter_alias)

            # 添加用户
            user = Users(email=email,
                         nick_name=nick_name,
                         client_ip=get_client_ip(request),
                         rf='admin',
                         is_active=False,
                         enterprise_id=enterprise.enterprise_id)
            user.set_password(password)
            user.save()
            monitorhook.registerMonitor(user, 'register')
            # 添加django用户
            tmpname = nick_name + "_token"
            oauth_user = OAuthUser.objects.create(username=tmpname)
            oauth_user.set_password(password)
            oauth_user.is_staff = True
            oauth_user.save()

            # 初始化企业与团队信息
            region_names = [region]
            enterprise_svc.create_and_init_tenant(user.user_id, tenant_name, region_names, enterprise.enterprise_id)

            # 第一个用户默认作为云帮管理员
            superadmin = SuperAdminUser()
            superadmin.email = email
            superadmin.save()

            # create gitlab user
            if user.email is not None and user.email != "":
                codeRepositoriesService.createUser(user, email, password, nick_name, nick_name)

            # 登录系统
            user = authenticate(username=nick_name, password=password)
            login(request, user)
            self.user = request.user

            # 发送数据到app进行注册
            data = {
                "username": nick_name,
                "email": email,
                "password": password,
            }
            json_data = json.dumps(data)

            try:
                # for num in range(0, 3):
                appClient.timeout = 5
                res, body = appClient.post_admin_info(json_data)
                if res is None:
                    logger.error("account.register", "register app failed!")
                else:
                    logger.debug("account.register", res)
                    logger.debug("account.register", body)
                    if res.status == 200:
                        logger.debug("account.register", "register app success!")
                    else:
                        logger.error("account.register", "register app failed!")
            except Exception as e:
                logger.exception("account.register", e)

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

