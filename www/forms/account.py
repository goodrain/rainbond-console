# -*- coding: utf8 -*-
import re
from django import forms
from django.forms.widgets import Select
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Fieldset, ButtonHolder, HTML, Hidden
from crispy_forms.bootstrap import (AppendedText, FieldWithButtons, StrictButton, InlineField,
                                    PrependedText, FormActions, AccordionGroup, InlineCheckboxes)
from www.models import Users, Tenants, PhoneCode
from www.layout import Submit, Field
import widgets
import fields
from www.region import RegionInfo
import time
from django.conf import settings
from www.utils import sn

import logging
logger = logging.getLogger('default')

SENSITIVE_WORDS = (
    'admin', 'root', 'goodrain', 'builder', 'app', 'tenant', 'tenants', 'service', 'services'
)

standard_regex_string = "^[a-z0-9][a-z0-9_\-]+[a-z0-9]$"
standard_regex_string_extend = "^[a-z0-9][a-z0-9\-]+[a-z0-9]$"


def is_standard_word(value):
    r = re.compile(standard_regex_string)
    if not r.match(value):
        raise forms.ValidationError(u"只可以使用小写英文字母、数字、下划线、中划线。")


def is_standard_word_extend(value):
    r = re.compile(standard_regex_string_extend)
    if not r.match(value):
        raise forms.ValidationError(u"只可以使用小写英文字母、数字、下划线、中划线。")


def is_sensitive(value):
    if value in SENSITIVE_WORDS:
        raise forms.ValidationError(u"不允许的用户名")


def password_len(value):
    if len(value) < 8:
        raise forms.ValidationError(u"密码长度至少为8位")


def is_phone(value):
    r = re.compile(r'^1[3578]\d{9}$|^147\d{8}$')
    if not r.match(value):
        raise forms.ValidationError(u"请填写正确的手机号")
    return True


def is_email(value):
    r = re.compile(r'^[\w\-\.]+@[\w\-]+(\.[\w\-]+)+$')
    if not r.match(value):
        raise forms.ValidationError(u"Email地址不合法")
    return True


def is_account(value):
    valid = False
    error = None

    for validator in (is_phone, is_email):
        try:
            validator(value)
            valid = True
        except forms.ValidationError, e:
            error = e

    if valid is False:
        raise error


class SelectWithDisabled(Select):

    def render_option(self, selected_choices, option_value, option_label):
        option_value = force_unicode(option_value)
        if (option_value in selected_choices):
            selected_html = u' selected="selected"'
        else:
            selected_html = ''
        disabled_html = ''
        if isinstance(option_label, dict):
            if dict.get(option_label, 'disabled'):
                disabled_html = u' disabled="disabled"'
            option_label = option_label['label']
        return u'<option value="%s"%s%s>%s</option>' % (
            escape(option_value), selected_html, disabled_html,
            conditional_escape(force_unicode(option_label)))


class UserLoginForm(forms.Form):

    '''
    用户登录表单
    '''
    email = forms.CharField(
        required=True, max_length=32,
        label=u"邮箱或手机号",
        # placeholder=u"邮箱",
        # widget=widgets.EmailInput
    )
    password = forms.CharField(
        required=True, label=u'密码',
        # min_length=8,
        widget=forms.PasswordInput,
        # widget = widgets.AdminTextareaWidget
        validators=[password_len]
    )
    remember = forms.BooleanField(
        required=False, label=u'记住我',
        initial=False,
    )

    error_messages = {
        'wrong_email': u"未注册的邮箱或手机号或用户名",
        'wrong_password': u"密码错误",
    }

    def __init__(self, *args, **kwargs):
        prefix_url = ""
        if len(kwargs) > 0:
            if kwargs.get("next_url") is not None:
                next_url = kwargs["next_url"]
                if next_url != "":
                    prefix_url += "&next={0}".format(next_url)
                kwargs.pop("next_url")
            if kwargs.get("origin") is not None:
                origin = kwargs["origin"]
                if origin != "":
                    prefix_url += "&origin={0}".format(origin)
                kwargs.pop("origin")
        if len(prefix_url) > 1:
            prefix_url = "?" + prefix_url[1:]
        super(UserLoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.form_show_labels = False
        if settings.MODULES["User_Register"]:
            if settings.MODULES["WeChat_Module"]:
                self.helper.layout = Div(
                    Field('email', css_class="form-control", placeholder='邮箱/手机号/用户名'),
                    Field('password', css_class="form-control", placeholder='密码'),
                    HTML("""<div class="checkbox clearfix"><label><input type="checkbox">下次自动登录</label><a href="/account/begin_password_reset" class="pull-right">忘记密码了？</a></div>"""),
                    FormActions(Submit('login', u'登录', css_class='btn btn-lg btn-success btn-block')),
                    HTML("""<p class="text-center">或使用以下账号登录</p><a href="/wechat/login{0}" class="weixin"><img src='/static/www/images/weixin.png'>&nbsp;微信</a>""".format(prefix_url)),
                    # HTML("""<div class="linkregister text-center">现在<a href="/register{0}">注册</a></div>""".format(prefix_url)),
                    css_class='login-wrap',
                    style="background: #FFFFFF;",
                )
            else:
                self.helper.layout = Div(
                    Field('email', css_class="form-control", placeholder='邮箱/手机号/用户名'),
                    Field('password', css_class="form-control", placeholder='密码'),
                    HTML("""<div class="checkbox clearfix"><label><input type="checkbox">下次自动登录</label><a href="/account/begin_password_reset" class="pull-right">忘记密码了？</a></div>"""),
                    FormActions(Submit('login', u'登录', css_class='btn btn-lg btn-success btn-block')),
                    # HTML("""<div class="linkregister text-center">现在<a href="/register{0}">注册</a></div>""".format(prefix_url)),
                    css_class='login-wrap',
                    style="background: #FFFFFF;",
                )
        else:
            self.helper.layout = Div(
                Field('email', css_class="form-control", placeholder='邮箱/手机号/用户名'),
                Field('password', css_class="form-control", placeholder='密码'),
                FormActions(Submit('login', u'登录', css_class='btn btn-lg btn-success btn-block')),
                css_class='login-wrap',
                style="background: #FFFFFF;",
            )
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.form_id = 'form-user-login'
        self.helper.form_class = 'form-horizontal'

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if password:
            if len(password) < 8:
                raise forms.ValidationError(
                    self.error_messages['password_length']
                )

        if email and password:
            try:
                if email.find("@") > 0:
                    user = Users.objects.get(email=email)
                elif email.isdigit():
                    user = Users.objects.get(phone=email)
                else:
                    user = Users.objects.get(nick_name=email)
                if not user.check_password(password):
                    logger.info('form_valid.login', 'password is not correct for user {0}'.format(email))
                    raise forms.ValidationError(
                        self.error_messages['wrong_password'],
                        code='wrong_password',
                        params={'email': email}
                    )
            except Users.DoesNotExist:
                logger.info('form_valid.login', 'user {0} does not exist'.format(email))
                raise forms.ValidationError(
                    self.error_messages['wrong_email'],
                    code='wrong_email',
                    params={'email': email}
                )
            # params={'username': self.username_field.verbose_name},

        return self.cleaned_data


class PasswordResetBeginForm(forms.Form):
    account = forms.CharField(
        required=True, max_length=32,
        label=u"注册邮箱",
        validators=[is_account],
    )

    def __init__(self, *args, **kwargs):
        super(PasswordResetBeginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Div(
            Field('account', css_class="form-control"),
            FormActions(Submit('next', u'下一步', css_class='btn btn-lg btn-success btn-block')),
            css_class='login-wrap',
            style="background: #FFFFFF;",
        )
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True

    def clean(self):
        account = self.cleaned_data.get('account')
        if account:
            try:
                if '@' in account:
                    u = Users.objects.get(email=account)
                else:
                    u = Users.objects.get(phone=account)
                if u.origion in ('ucloud',):
                    raise forms.ValidationError(
                        u'第三方账号不支持密码找回', code='reset passwd deny',
                        params={"account": account}
                    )
            except Users.DoesNotExist:
                logger.info('form_valid.password', 'account {0} does not exist'.format(account))
                raise forms.ValidationError(
                    u'不存在的账号',
                    code='account not exists', params={'account': account}
                )

        return self.cleaned_data


class PasswordResetForm(forms.Form):
    password = forms.CharField(
        required=True, label='',
        widget=forms.PasswordInput,
        validators=[password_len]
    )
    password_repeat = forms.CharField(
        required=True, label='',
        widget=forms.PasswordInput,
        validators=[password_len]
    )

    error_messages = {
        'password_repeat': u"两次输入的密码不一致",
    }

    def __init__(self, *args, **kwargs):
        super(PasswordResetForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Div(
            Field('account', css_class="form-control"),
            'password',
            'password_repeat',
            FormActions(Submit('commit', u'提交', css_class='btn btn-lg btn-primary btn-block')),
            css_class='login-wrap',
            style="background: #FFFFFF;",
        )

        self.helper.help_text_inline = True
        self.helper.error_text_inline = True

    def clean(self):
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')

        if password_repeat != password:
            raise forms.ValidationError(
                self.error_messages['password_repeat'],
                code='password_repeat',
            )


class RegisterForm(forms.Form):

    '''
    邀请注册表单
    '''
    email = forms.EmailField(
        required=False, max_length=32, label="",
        # ajax_check=True,
        # widget=widgets.EmailInput(attrs={"data-remote-error": u"邮件地址已存在"})
    )
    tenant = forms.CharField(
        required=True, max_length=40, label="",
        validators=[is_standard_word_extend, is_sensitive],
        # min_length=3, ajax_check=True, pattern=standard_regex_string,
        # widget=widgets.TextInput(attrs={"data-remote-error": u"已存在"})
    )
    nick_name = forms.CharField(
        required=True, max_length=24, label="",
        validators=[is_standard_word, is_sensitive],
        # pattern=standard_regex_string, ajax_check=True,
        # widget=widgets.TextInput(attrs={"data-remote-error": u"昵称已存在"})
    )
    password = forms.CharField(
        required=True, label='',
        widget=forms.PasswordInput,
        validators=[password_len]
    )
    password_repeat = forms.CharField(
        required=True, label='',
        widget=forms.PasswordInput,
        validators=[password_len]
    )
    phone = forms.CharField(
        required=True, label='',
        validators=[is_phone]
    )
    
    if settings.MODULES["Sms_Check"]:
        phone_code = forms.CharField(
            required=False, label='',
        )
        
    captcha_code = forms.CharField(
        required=True, label='',
    )
    real_captcha_code = forms.CharField(
        required=True, label='',
    )

    invite_tag = forms.CharField(
        required=False, label='',
    )

    # ('aws-bj-1', 'Amazon北京'),
    # ('aws-bj-1', '亚马逊[北京]'),
    # ('0', {'label':'亚马逊[北京](正在建设)', 'disabled': True})
    machine_region = forms.ChoiceField(
        label="",
        choices=RegionInfo.register_choices(),
        initial="ali-sh",
        widget=SelectWithDisabled
    )

    error_messages = {
        'nick_name_used': u"该用户名已存在",
        'email_used': u"邮件地址已被注册",
        'tenant_used': u"团队名已存在",
        'password_repeat': u"两次输入的密码不一致",
        'phone_used': u"手机号已存在",
        'phone_empty': u"手机号为空",
        'phone_captch_error': u"手机验证码已失效",
        'phone_code_error': u"手机验证码错误",
        'captcha_code_error': u"验证码有误",
        'machine_region_error': u"请选择数据中心",
    }

    def __init__(self, *args, **kwargs):
        init_phone = ""
        init_email = ""
        init_tenant = ""
        init_region = ""
        selected_region = ""
        next_url = None
        origin = None
        prefix_url = ""
        if len(kwargs) > 0:
            if kwargs.get("initial") is not None:
                initalObj = kwargs.get("initial")
                init_phone = initalObj["phone"]
                init_email = initalObj["email"]
                init_tenant = initalObj["tenant"]
                init_region = initalObj["region"]
            if kwargs.get("region_level") is not None:
                selected_region = kwargs["region_level"]["region"]
                kwargs.pop("region_level")
            if kwargs.get("next_url") is not None:
                next_url = kwargs["next_url"]
                prefix_url += "&next={0}".format(next_url)
                kwargs.pop("next_url")
            if kwargs.get("origin") is not None:
                origin = kwargs["origin"]
                prefix_url += "&origin={0}".format(origin)
                kwargs.pop("origin")
        if len(prefix_url) > 1:
            prefix_url = "?" + prefix_url[1:]
        if len(args) > 0:
            if type(args) is tuple:
                if args[0].get("initial") is not None:
                    initalObj = args[0]["initial"]
                    if type(initalObj) is list:
                        initalObj = initalObj(0)
                    init_phone = initalObj["phone"]
                    init_email = initalObj["email"]
                    init_tenant = initalObj["tenant"]
                    init_region = initalObj["region"]
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False

        text_phone = "手机号"
        text_email = "请输入邮箱地址"
        text_tenant = "团队域名"
        if init_phone is not None and init_phone != "":
            self.fields['phone'].widget.attrs['readonly'] = True
            text_phone = init_phone
        if init_email is not None and init_email != "":
            self.fields['email'].widget.attrs['readonly'] = True
            text_email = init_email
        if init_tenant is not None and init_tenant != "":
            self.fields['tenant'].widget.attrs['readonly'] = True
            text_tenant = init_tenant
        if init_region is not None and init_region != "":
            self.fields['machine_region'].initial = init_region
            self.fields['machine_region'].widget.attrs['readonly'] = True
        if selected_region is not None and selected_region != "":
            self.fields['machine_region'].initial = selected_region

        init_region = RegionInfo.register_choices()[0][0]
        # 对于社区版注册表单进行处理
        is_private = sn.instance.is_private()
        tenant_name = None
        if is_private:
            tenant_num = Tenants.objects.count()
            if tenant_num == 1:
                tenant_list = Tenants.objects.all()
                tenant = tenant_list[0]
                tenant_name = tenant.tenant_name

        # if settings.MODULES["Sms_Check"]:
        if settings.MODULES["WeChat_Module"]:
            self.helper.layout = Layout(
                Div(
                    Field('tenant', "", placeholder='请输入团队名(可使用小写英文字母、数字、下划线及中划线)', css_class="form-control") if tenant_name is None else Field('tenant', "", placeholder='请输入团队名(可使用小写英文字母、数字、下划线及中划线)', css_class="form-control", readonly="readonly", value=tenant_name),
                    Field('nick_name', css_class="form-control", placeholder='请输入用户名(可使用小写英文字母、数字、下划线及中划线)'),
                    Field('email', css_class="form-control", placeholder='请输入邮箱(选填)'),
                    HTML("<hr/>"),
                    # 默认为ali-sh
                    Hidden('machine_region', value=init_region),
                    Hidden('next', value=next_url),
                    Hidden('origin', value=origin),
                    Field('password', css_class="form-control", placeholder='请设置密码，至少包含8位字符'),
                    Field('password_repeat', css_class="form-control", placeholder='请再输入一次密码'),
                    Field('phone', css_class="form-control", placeholder='请输入手机号'),
                    AppendedText('captcha_code', '<img id="captcha_code" src="/captcha" /> <a href="javascript:void(0)" onclick="refresh();">看不清，换一张</a>  ',
                                 css_class='input-xlarge', placeholder='图片验证码'),
                    AppendedText('phone_code', '<a href="javascript:void(0)" id="PhoneCodeBtn" onclick="getPhoneCode();">点击发送验证码</a>  ',
                                 css_class='input-xlarge', placeholder='手机验证码'),
                    HTML("""<div class="linkfw text-center">点击注册表示你已阅读并同意《<a href="http://www.goodrain.com/goodrainlaws.html" target="_blank">云帮服务条款</a>》</div>"""),
                    FormActions(Submit('register', u'注册', css_class='btn btn-lg btn-success btn-block')),
                    HTML("""<p class="text-center">或使用以下账号注册</p>"""),
                    HTML("""<a href="/wechat/login{0}" class="weixin"><img src="static/www/images/weixin.png">微信</a>""".format(prefix_url)),
                    HTML("""<div class="linkregister text-center">直接<a href="/login{0}">登录</a></div>""".format(prefix_url)),
                    # HTML("""<a href="http://www.goodrain.com/" class="linkgood text-center">goodrain.com</a>"""),
                    css_class="login-wrap"
                )
            )
        else:
            self.helper.layout = Layout(
                Div(
                    Field('tenant', "", placeholder='请输入团队名(可使用小写英文字母、数字、下划线及中划线)', css_class="form-control") if tenant_name is None else Field('tenant', "", placeholder='请输入团队名(可使用小写英文字母、数字、下划线及中划线)', css_class="form-control", readonly="readonly", value=tenant_name),
                    Field('nick_name', css_class="form-control", placeholder='请输入用户名(可使用小写英文字母、数字、下划线及中划线)'),
                    Field('email', css_class="form-control", placeholder='请输入邮箱(选填)'),
                    HTML("<hr/>"),
                    Hidden('machine_region', value=init_region),
                    Hidden('next', value=next_url),
                    Hidden('origin', value=origin),
                    Field('password', css_class="form-control", placeholder='请设置密码，至少包含8位字符'),
                    Field('password_repeat', css_class="form-control", placeholder='请再输入一次密码'),
                    Field('phone', css_class="form-control", placeholder='请输入手机号'),
                    AppendedText('captcha_code', '<img id="captcha_code" src="/captcha" /> <a href="javascript:void(0)" onclick="refresh();">看不清，换一张</a>  ',
                                 css_class='input-xlarge', placeholder='验证码'),
                    AppendedText('phone_code', '<a href="javascript:void(0)" id="PhoneCodeBtn" onclick="getPhoneCode();">点击发送验证码</a>  ',
                                 css_class='input-xlarge', placeholder='手机验证码'),
                    HTML("""<div class="linkfw text-center">点击注册表示你已阅读并同意《<a href="http://www.goodrain.com/goodrainlaws.html" target="_blank">云帮服务条款</a>》</div>"""),
                    FormActions(Submit('register', u'注册', css_class='btn btn-lg btn-success btn-block')),
                    HTML("""<div class="linkregister text-center">直接<a href="/login{0}">登录</a></div>""".format(prefix_url)),
                    # HTML("""<a href="http://www.goodrain.com/" class="linkgood text-center">goodrain.com</a>"""),
                    css_class="login-wrap"
                )
            )
        self.helper.form_id = 'form-normal-reg'
        self.helper.form_class = 'form-horizontal'

    def clean(self):
        email = self.cleaned_data.get('email')
        tenant = self.cleaned_data.get('tenant')
        nick_name = self.cleaned_data.get('nick_name')
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')
        phone = self.cleaned_data.get('phone')
        phone_code = self.cleaned_data.get('phone_code')
        captcha_code = self.cleaned_data.get('captcha_code')
        real_captcha_code = self.cleaned_data.get('real_captcha_code')
        invite_tag = self.cleaned_data.get('invite_tag')
        machine_region = self.cleaned_data.get('machine_region')

        # 校验邮箱,为空不做校验
        if email is not None and email != "":
            try:
                Users.objects.get(email=email)
                raise forms.ValidationError(
                    self.error_messages['email_used'],
                    code='email_used',
                    params={'email': email}
                )
            except Users.DoesNotExist:
                pass

        # 判断是否邀请注册,邀请注册不校验租户
        if invite_tag is None or invite_tag == "":
            try:
                Tenants.objects.get(tenant_name=tenant)
                if not sn.instance.is_private():
                    raise forms.ValidationError(
                        self.error_messages['tenant_used'],
                        code='tenant_used',
                        params={'tenant': tenant}
                    )
            except Tenants.DoesNotExist:
                pass

        # 数据中心不做校验,默认为ali-sh
        if machine_region is None or machine_region == "" or machine_region == "1":
            pass
            # machine_region = "ali-sh"
            # raise forms.ValidationError(
            #     self.error_messages['machine_region_error'],
            #     code='machine_region_error',
            # )

        try:
            Users.objects.get(nick_name=nick_name)
            raise forms.ValidationError(
                self.error_messages['nick_name_used'],
                code='nick_name_used'
            )
        except Users.DoesNotExist:
            pass

        if password_repeat != password:
            raise forms.ValidationError(
                self.error_messages['password_repeat'],
                code='password_repeat',
            )

        # 手机号码为空不做校验,不为空校验是否已经存在
        if phone is not None and phone != "":
            phoneNumber = Users.objects.filter(phone=phone).count()
            logger.debug('form_valid.register', phoneNumber)
            if phoneNumber > 0:
                raise forms.ValidationError(
                    self.error_messages['phone_used'],
                    code='phone_used'
                )
        else:
            pass
            # raise forms.ValidationError(
            #     self.error_messages['phone_empty'],
            #     code='phone_empty'
            # )

        if phone is not None and phone != "":
            if settings.MODULES["Sms_Check"]:
                phoneCodes = PhoneCode.objects.filter(phone=phone).order_by('-ID')[:1]
                if len(phoneCodes) > 0:
                    phoneCode = phoneCodes[0]
                    last = int(phoneCode.create_time.strftime("%s"))
                    now = int(time.time())
                    if now - last > 300:
                        logger.info('form_valid.register', phone + "too long time")
                        raise forms.ValidationError(
                            self.error_messages['phone_captch_error'],
                            code='phone_captch_error'
                        )
                    if phoneCode.code != phone_code:
                        logger.info('form_valid.register', phone + " different")
                        raise forms.ValidationError(
                            self.error_messages['phone_code_error'],
                            code='phone_code_error'
                        )
                else:
                    raise forms.ValidationError(
                        self.error_messages['phone_code_error'],
                        code='phone_code_error'
                    )
        else:
            logger.info('form_valid.register', " phone is None")
            pass
            # raise forms.ValidationError(
            #     self.error_messages['phone_empty'],
            #     code='phone_empty'
            # )

        if real_captcha_code is None or captcha_code is None or real_captcha_code.lower() != captcha_code.lower():
            raise forms.ValidationError(
                self.error_messages['captcha_code_error'],
                code='captcha_code_error'
            )

        return self.cleaned_data
