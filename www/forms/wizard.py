# -*- coding: utf8 -*-
import re
from django import forms
from django.conf import settings
from django.forms.widgets import Select
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Fieldset, ButtonHolder, HTML, Hidden
from crispy_forms.bootstrap import (AppendedText,
                                    Field,
                                    FieldWithButtons,
                                    StrictButton,
                                    InlineField,
                                    PrependedText,
                                    FormActions,
                                    AccordionGroup,
                                    InlineCheckboxes)

from www.region import RegionInfo

import time
import logging
logger = logging.getLogger('default')

SENSITIVE_WORDS = (
    'admin',
    'root',
    'goodrain',
    'builder',
    'app',
    'tenant',
    'tenants',
    'service',
    'services'
)

standard_regex_string = "^[a-z0-9][a-z0-9_\-]+[a-z0-9]$"
standard_regex_string_extend = "^[a-z0-9][a-z0-9\-]+[a-z0-9]$"


def is_standard_word(value):
    r = re.compile(standard_regex_string)
    if not r.match(value):
        raise forms.ValidationError(u"允许下列字符: 小写字母 数字 _ -")


def is_standard_word_extend(value):
    r = re.compile(standard_regex_string_extend)
    if not r.match(value):
        raise forms.ValidationError(u"允许下列字符: 小写字母 数字 _ -")


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


class AdminForm(forms.Form):
    """向导注册管理员"""
    email = forms.EmailField(
        required=True, max_length=32, label="",
        # ajax_check=False,
        # widget=widgets.EmailInput(attrs={"data-remote-error": u"邮件地址已存在"})
    )
    nick_name = forms.CharField(
        required=True, max_length=24, label="",
        validators=[is_standard_word, is_sensitive],
        # pattern=standard_regex_string, ajax_check=True,
        # widget=widgets.TextInput(attrs={"data-remote-error": u"昵称已存在"})
    )
    enter_alias = forms.CharField(
        required=True, max_length=32, label="",
        validators=[is_sensitive],
        # pattern=standard_regex_string, ajax_check=True,
        # widget=widgets.TextInput(attrs={"data-remote-error": u"昵称已存在"})
    )
    password = forms.CharField(
        required=True,
        label='',
        min_length=8,
        widget=forms.PasswordInput,
        validators=[password_len]
    )
    password_repeat = forms.CharField(
        required=True,
        label='',
        min_length=8,
        widget=forms.PasswordInput,
        validators=[password_len]
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
        'machine_region_error': u"请选择数据中心",
    }

    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        # 获取region
        init_region = RegionInfo.register_choices()[0][0]

        self.helper.layout = Layout(
            Div(
                Field('enter_alias', css_class="form-control", placeholder=u"企业名称"),
                Field('nick_name', css_class="form-control", placeholder=u"用户名(英文)"),
                Field('email', css_class="form-control", placeholder=u"管理员邮箱"),
                Hidden('machine_region', value=init_region),
                Field('password', css_class="form-control", placeholder=u"请输入至少8位数密码"),
                Field('password_repeat', css_class="form-control", placeholder=u"请再输入一次密码"),
                HTML("""<div class="form-group" style="text-align:left;"><a href="http://doc.goodrain.com/cloudbang-agreement/201656" target="_blank">《云帮企业版用户服务协议》</a></div>"""),
                FormActions(Submit('register', u'同意协议，创建账号', css_class='btn btn-lg btn-success btn-block')),
                css_class="login-wrap"
            )
        )
        self.helper.form_id = 'form-normal-reg'
        self.helper.form_class = 'form-horizontal'

    def clean(self):
        email = self.cleaned_data.get('email')
        nick_name = self.cleaned_data.get('nick_name')
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')
        machine_region = self.cleaned_data.get('machine_region')

        # 检查密码与确认密码是否一致
        if password_repeat != password:
            raise forms.ValidationError(
                self.error_messages['password_repeat'],
                code='password_repeat',
            )

        return self.cleaned_data
