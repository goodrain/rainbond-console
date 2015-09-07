# -*- coding: utf8 -*-
import re
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Fieldset, ButtonHolder, HTML, Row
from crispy_forms.bootstrap import (AppendedText, FieldWithButtons, StrictButton, InlineField,
                                    PrependedText, FormActions, AccordionGroup, InlineCheckboxes)
from www.models import Users, Tenants, PhoneCode
from www.layout import Submit, Field
from www.forms import widgets
from django.http.request import HttpRequest
import time

import logging
logger = logging.getLogger('default')


def is_standard_word(value):
    r = re.compile(r'^[a-z0-9_\-]+[a-z0-9]$')
    if not r.match(value):
        raise forms.ValidationError(u"允许下列字符: 小写字母 数字 _ -")


def password_len(value):
    if len(value) < 8:
        raise forms.ValidationError(u"密码长度至少为8位")


def is_phone(value):
    r = re.compile(r'^1[358]\d{9}$|^147\d{8}$')
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
        'wrong_email': u"未注册的邮箱或手机号",
        'wrong_password': u"密码错误",
    }

    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Div(
            Field('email', css_class="form-control", placeholder=''),
            Field('password', css_class="form-control", placeholder=''),
            FormActions(Submit('login', u'登录', css_class='btn btn-lg btn-success btn-block')),
            HTML(u'''<div class="registration" style="float: left;">还没有帐户？<a class="" href="/register">创建一个帐户</a></div>'''),
            HTML(u'''<div class="forgetpass" style="float: right;"><a class="" href="/account/begin_password_reset">?忘记密码</a></div>'''),
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
                else:
                    user = Users.objects.get(phone=email)
                if not user.check_password(password):
                    logger.error('password {0} is not correct for user {1}'.format(password, email))
                    raise forms.ValidationError(
                        self.error_messages['wrong_password'],
                        code='wrong_password',
                        params={'email': email}
                    )
            except Users.DoesNotExist:
                logger.error('user {0} does not exist'.format(email))
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
        label=u"邮箱或手机号",
        validators=[is_account],
    )

    def __init__(self, *args, **kwargs):
        super(PasswordResetBeginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Div(
            Field('account', css_class="form-control"),
            FormActions(Submit('next', u'下一步', css_class='btn btn-lg btn-primary btn-block')),
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
                    Users.objects.get(email=account)
                else:
                    Users.objects.get(phone=account)
            except Users.DoesNotExist:
                logger.error('account {0} does not exist'.format(account))
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


class RegisterForm(forms.Form):

    '''
    邀请注册表单
    '''
    email = forms.EmailField(
        required=True, max_length=32, label="",
    )
    tenant = forms.CharField(
        required=True, max_length=40, label="",
        validators=[is_standard_word]
    )
    nick_name = forms.CharField(
        required=True, max_length=24, label="",
        validators=[is_standard_word]
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
    phone_code = forms.CharField(
        required=True, label='',
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

    checkboxes = forms.MultipleChoiceField(
        label="",
        choices=(
            (1, '我已阅读并同意好雨云平台使用协议'),
        ),
        initial='1',
        widget=forms.CheckboxSelectMultiple,
        help_text="",
    )

    machine_region = forms.ChoiceField(
        label="",
        choices=(
            ('1', '机房'),
            ('ucloud-bj-1', 'UCloud北京')
        ),
        widget=forms.Select
    )

    error_messages = {
        'nick_name_used': u"该用户名已存在",
        'email_used': u"邮件地址已被注册",
        'tenant_used': u"团队名已存在",
        'password_repeat': u"两次输入的密码不一致",
        'phone_used': u"手机号已存在",
        'phone_empty': u"手机号为空",
        'phone_code_error': u"手机验证码已失效",
        'captcha_code_error': u"验证码有误",
        'machine_region_error': u"请选择机房",
    }

    def __init__(self, *args, **kwargs):
        init_phone = ""
        init_email = ""
        init_tenant = ""
        init_region = ""
        if len(kwargs) > 0 and kwargs["initial"] is not None:
            init_phone = kwargs["initial"]["phone"]
            init_email = kwargs["initial"]["email"]
            init_tenant = kwargs["initial"]["tenant"]
            init_region = kwargs["initial"]["region"]

        super(RegisterForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        if init_phone is not None and init_phone != "":
            self.fields['phone'].widget.attrs['readonly'] = True
        if init_email is not None and init_email != "":
            self.fields['email'].widget.attrs['readonly'] = True
        if init_tenant is not None and init_tenant != "":
            self.fields['tenant'].widget.attrs['readonly'] = True
        if init_region is not None and init_region != "":
            self.fields['machine_region'].widget.attrs['readonly'] = True

        self.helper.layout = Layout(
            Div(
                Field('nick_name', css_class="form-control", placeholder='请输入用户名'),
                Field('email', css_class="form-control", placeholder='请输入邮箱地址'),
                HTML("<hr/>"),
                # Field('tenant', css_class="form-control teamdomain", placeholder='团队域名'),
                AppendedText('tenant', '.goodrain.net', placeholder='团队域名', css_class='teamdomain'),

                Field('machine_region'),
                # HTML('<input type="text" name="tenant" id="tenant" value="" class="teamdomain" placeholder="团队域名"> .goodrain.net'),
                Field('password', css_class="form-control", placeholder='请输入至少8位数密码'),
                Field('password_repeat', css_class="form-control", placeholder='请再输入一次密码'),

                AppendedText('captcha_code', '<img id="captcha_code" src="/captcha" /> <a href="javascript:void(0)" onclick="refresh();">看不清，换一张</a>  ',
                             css_class='input-xlarge', placeholder='验证码'),

                Field('phone', css_class="form-control", placeholder='手机号'),
                AppendedText('phone_code', '<button class="btn btn-primary" id="PhoneCodeBtn" onclick="getPhoneCode();return false;">发送验证码</button>',
                             css_class='input-xlarge', placeholder='手机验证码'),

                # PrependedText('prepended_text','captcha'),

                # Field('phone_code', 'Serial #', '<button class=\"btn btn-primary\">获取验证码</button>', css_class="form-control", placeholder='验证码'),
                # StrictButton('Submit', type='submit', css_class='btn-primary')
                # FieldWithButtons('phone_code', StrictButton('获取验证码', type='submit', css_class='form-control')),
                Field('checkboxes', placeholder='机房'),

                # Field('appended_text'),
                # PrependedText('appended_text', '我已阅读并同意<a href="" target="_blank">好雨云平台使用协议</a>',active=True),

                # InlineCheckboxes('checkbox_inline'),
                # Field('checkboxes', css_class="form-control"),
                # AppendedText('checkboxes'),
                # Field('checkboxes', style="background: #FAFAFA; padding: 10px;"),
                # HTML('<a href="" target="_blank">好雨云平台使用协议</a>'),
                # help_text = '<a href="" target="_blank">好雨云平台使用协议</a>',

                FormActions(Submit('register', u'注册', css_class='btn btn-lg btn-success btn-block')),

                HTML("<hr/>"),

                HTML(u'''<div style="font-size: 14px">已经有帐号，请<a class="" href="/login">登录</a></div>'''),
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
        try:
            Users.objects.get(email=email)
            raise forms.ValidationError(
                self.error_messages['email_used'],
                code='email_used',
                params={'email': email}
            )
        except Users.DoesNotExist:
            pass

        if invite_tag is None or invite_tag == "":
            try:
                Tenants.objects.get(tenant_name=tenant)
                raise forms.ValidationError(
                    self.error_messages['tenant_used'],
                    code='tenant_used',
                    params={'tenant': tenant}
                )
            except Tenants.DoesNotExist:
                pass

        if machine_region is None or machine_region == "" or machine_region == "1":
            raise forms.ValidationError(
                self.error_messages['machine_region_error'],
                code='machine_region_error',
            )

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

        if phone is not None and phone != "":
            phoneNumber = Users.objects.filter(phone=phone).count()
            logger.debug(phoneNumber)
            if phoneNumber > 0:
                raise forms.ValidationError(
                    self.error_messages['phone_used'],
                    code='phone_used'
                )
        else:
            raise forms.ValidationError(
                self.error_messages['phone_empty'],
                code='phone_empty'
            )

        if phone is not None and phone != "":
            phoneCodes = PhoneCode.objects.filter(phone=phone).order_by('-ID')[:1]
            if len(phoneCodes) > 0:
                phoneCode = phoneCodes[0]
                last = int(phoneCode.create_time.strftime("%s"))
                now = int(time.time())
                if now - last > 1800:
                    logger.debug(phone + "too long time")
                    raise forms.ValidationError(
                        self.error_messages['phone_code_error'],
                        code='phone_code_error'
                    )
                if phoneCode.code != phone_code:
                    logger.debug(phone + " different")
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
            logger.debug(phone + " is None")
            raise forms.ValidationError(
                self.error_messages['phone_code_error'],
                code='phone_code_error'
            )

        if real_captcha_code != captcha_code:
            raise forms.ValidationError(
                self.error_messages['captcha_code_error'],
                code='captcha_code_error'
            )

        return self.cleaned_data
