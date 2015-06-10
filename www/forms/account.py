# -*- coding: utf8 -*-
import re
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Fieldset, ButtonHolder, HTML, Row
from crispy_forms.bootstrap import (AppendedText, FieldWithButtons, StrictButton, InlineField,
    PrependedText, FormActions, AccordionGroup, InlineCheckboxes)
from www.models import Users, Tenants
from www.layout import Submit, Field
from www.forms import widgets

import logging
logger = logging.getLogger('default')


def is_standard_word(value):
    r = re.compile(r'^[a-z0-9_\-]+[a-z0-9]$')
    if not r.match(value):
        raise forms.ValidationError(u"允许下列字符: 小写字母 数字 _ -")


def password_len(value):
    if len(value) < 8:
        raise forms.ValidationError(u"密码长度至少为8位")


class UserLoginForm(forms.Form):
    '''
    用户登录表单
    '''
    email = forms.EmailField(
        required=True, max_length=32,
        label=u"邮件",
        #placeholder=u"邮箱",
        #widget=widgets.EmailInput
    )
    password = forms.CharField(
        required=True, label=u'密码',
        #min_length=8,
        widget=forms.PasswordInput,
        #widget = widgets.AdminTextareaWidget
        validators=[password_len]
    )
    remember = forms.BooleanField(
        required=False, label=u'记住我',
        initial=False,
    )

    error_messages = {
        'wrong_email': u"未注册的email",
        'wrong_password': u"密码错误",
    }

    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Div(
            Field('email', 'password'),
            FormActions(Submit('login', u'登录', css_class='btn btn-success btn-lg btn-block')),
            HTML(u'''<div class="registration">还没有帐户？<a class="" href="/register">创建一个帐户
                </a></div>'''),
            css_class='login-wrap'
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
                user = Users.objects.get(email=email)
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
            #params={'username': self.username_field.verbose_name},

        return self.cleaned_data


class InviteUserForm(forms.Form):
    '''
    邀请用户表单
    '''
    email = forms.EmailField(
        required=True, max_length=32, label=u'邮件地址',
        #validators = [check_appname],
    )
    tenant = forms.CharField(
        required=True, max_length=40, label=u"团队名称",
    )

    def __init__(self, *args, **kwargs):
        super(InviteUserForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            InlineField('email', 'tenant'),
            FormActions(Submit('commit', u'邀请')),
        )

        self.helper.form_id = 'form-invite-user'
        self.helper.form_class = 'form-horizontal'

    def clean(self):
        email = self.cleaned_data.get('email')
        tenant = self.cleaned_data.get('tenant')

        try:
            t = Tenants.objects.get(tenant_name=tenant)
            is_member = t.users.filter(email=email)
            if is_member:
                raise forms.ValidationError(
                    u"已经是团队成员了",
                    code='401'
                )
        except Tenants.DoesNotExist:
            raise forms.ValidationError(
                u'不存在的团队名',
                code='401'
            )

        return self.cleaned_data


class RegisterForm(forms.Form):
    '''
    邀请注册表单
    '''
    email = forms.EmailField(
        required=True, max_length=32, label=u'邮件地址',
    )
    tenant = forms.CharField(
        required=True, max_length=40, label=u"团队名",
        validators=[is_standard_word]
    )
    nick_name = forms.CharField(
        required=True, max_length=24, label=u'用户名',
        validators=[is_standard_word]
    )
    password = forms.CharField(
        required=True, label=u'密码',
        widget=forms.PasswordInput,
        validators=[password_len]
    )
    password_repeat = forms.CharField(
        required=True, label=u'确认密码',
        widget=forms.PasswordInput,
        validators=[password_len]
    )
    aggree = forms.BooleanField(
        required=False, label=u'我同意'
    )

    error_messages = {
        'nick_name_used': u"该用户名已存在",
        'email_used': u"邮件地址已被注册",
        'tenant_used': u"团队名已存在",
        'password_repeat': u"两次输入的密码不一致",
    }

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML(u'''<div class="photobox"><img src="/static/www/img/okooo/photobg.jpg" alt=""><p><a href="">上传头像</a></p></div>'''),
            Div(
                'email',
                'tenant',
                #AppendedText('tenant', '.myapps.com', placeholder=u"团队名称"),
                'nick_name', 'password', 'password_repeat',
                #template="widgets/register_field.html"
                FormActions(Submit('register', u'提交', css_class='btn btn-success btn-lg btn-block')),
                HTML(u'''<div class="registration">已经有账号的,<a class="" href="/login">登录</a></div>'''),
                css_class='login-wrap'
            ),

        )

        self.helper.form_id = 'form-normal-reg'
        self.helper.form_class = 'form-horizontal'

    def clean(self):
        email = self.cleaned_data.get('email')
        tenant = self.cleaned_data.get('tenant')
        nick_name = self.cleaned_data.get('nick_name')
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')

        try:
            Users.objects.get(email=email)
            raise forms.ValidationError(
                self.error_messages['email_used'],
                code='email_used',
                params={'email': email}
            )
        except Users.DoesNotExist:
            pass

        try:
            Tenants.objects.get(tenant_name=tenant)
            raise forms.ValidationError(
                self.error_messages['tenant_used'],
                code='tenant_used',
                params={'tenant': tenant}
            )
        except Tenants.DoesNotExist:
            pass
            #params={'username': self.username_field.verbose_name},

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
        return self.cleaned_data


class InviteRegForm(forms.Form):
    '''
    邀请注册表单
    '''
    nick_name = forms.CharField(
        required=True, max_length=24, label=u'用户名',
        validators=[is_standard_word]
    )

    password = forms.CharField(
        required=True, label=u'密码',
        validators=[password_len],
        widget=forms.PasswordInput,
    )
    password_repeat = forms.CharField(
        required=True, label=u'确认密码',
        validators=[password_len],
        widget=forms.PasswordInput,
    )
    aggree = forms.BooleanField(
        required=False, label=u'我同意'
    )

    error_messages = {
        'nick_name_used': u"此用户名已被占用",
    }

    def __init__(self, *args, **kwargs):
        super(InviteRegForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                'nick_name', 'password', 'password_repeat',
                FormActions(Submit('register', u'提交', css_class='btn btn-success btn-lg btn-block')),
                HTML(u'''<div class="registration">已经有账号的,<a class="" href="/login">登录</a></div>'''),
                css_class='login-wrap'
            ),

        )

        self.helper.form_id = 'form-normal-reg'
        self.helper.form_class = 'form-horizontal'

    def clean(self):
        nick_name = self.cleaned_data.get('nick_name')
        try:
            Users.objects.get(nick_name=nick_name)
            raise forms.ValidationError(
                self.error_messages['nick_name_used'],
                code='nick_name_used'
            )
        except Users.DoesNotExist:
            pass

        return self.cleaned_data


class InviteRegForm2(InviteRegForm):
    tenant = forms.CharField(
        required=True, max_length=40, label=u"团队名",
        validators=[is_standard_word]
    )

    def __init__(self, *args, **kwargs):
        super(InviteRegForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                'tenant', 'nick_name', 'password', 'password_repeat',
                FormActions(Submit('register', u'提交', css_class='btn btn-success btn-lg btn-block')),
                HTML(u'''<div class="registration">已经有账号的,<a class="" href="/login">登录</a></div>'''),
                css_class='login-wrap'
            ),

        )

        self.helper.form_id = 'form-normal-reg'
        self.helper.form_class = 'form-horizontal'


class SendInviteForm(forms.Form):
    email = forms.EmailField(
        required=True, max_length=32, label=u'邮件地址',
    )
    error_messages = {
        'email_used': u"邮件地址已被注册",
    }

    def __init__(self, *args, **kwargs):
        super(SendInviteForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                'email',
                FormActions(Submit('register', u'提交', css_class='btn btn-success btn-lg btn-block')),
                css_class='login-wrap'
            ),
        )

    def clean(self):
        email = self.cleaned_data.get('email')

        try:
            Users.objects.get(email=email)
            raise forms.ValidationError(
                self.error_messages['email_used'],
                code='email_used',
                params={'email': email}
            )
        except Users.DoesNotExist:
            pass
