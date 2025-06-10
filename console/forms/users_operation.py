# -*- coding: utf-8 -*-
import logging
import re

from django import forms
from django.forms.forms import Form
from www.models.main import Users

logger = logging.getLogger("default")
SENSITIVE_WORDS = ('root', 'goodrain', 'builder', 'app', 'tenant', 'tenants', 'service', 'services')

standard_regex_string = "^[a-z0-9][a-z0-9_\-]+[a-z0-9]$"
standard_regex_string_extend = "^[a-z0-9][a-z0-9\-]+[a-z0-9]$"


def is_standard_word(value):
    r = re.compile(standard_regex_string)
    if not r.match(value):
        raise forms.ValidationError("用户名只可以使用小写英文字母、数字、下划线、中划线。")


def is_standard_word_extend(value):
    r = re.compile(standard_regex_string_extend)
    if not r.match(value):
        raise forms.ValidationError("用户名只可以使用小写英文字母、数字、中划线。")


def is_sensitive(value):
    if value in SENSITIVE_WORDS:
        raise forms.ValidationError("不允许的用户名")


def password_len(value):
    if len(value) < 8:
        raise forms.ValidationError("密码长度至少为8位")


class RegisterForm(Form):

    user_name = forms.CharField(required=True, max_length=24, label="", validators=[is_standard_word, is_sensitive])

    email = forms.EmailField(required=True, max_length=64, label="")

    phone = forms.CharField(required=False, max_length=15, label="")

    real_name = forms.CharField(required=False, max_length=64, label="")

    password = forms.CharField(required=True, label='', widget=forms.PasswordInput, validators=[password_len])

    password_repeat = forms.CharField(required=True, label='', widget=forms.PasswordInput, validators=[password_len])

    error_messages = {
        'nick_name_used': "该用户名已存在",
        'email_used': "邮件地址已被注册",
        'tenant_used': "团队名已存在",
        'password_repeat': "两次输入的密码不一致",
        'phone_used': "手机号已存在",
        'phone_empty': "手机号为空",
        'phone_captch_error': "手机验证码已失效",
        'phone_code_error': "手机验证码错误",
        'machine_region_error': "请选择数据中心",
    }

    def clean(self):
        nick_name = self.cleaned_data.get('user_name')
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')
        phone = self.cleaned_data.get('phone')

        try:
            Users.objects.get(nick_name=nick_name)
            raise forms.ValidationError(self.error_messages['nick_name_used'], code='nick_name_used')
        except Users.DoesNotExist:
            pass
        except Users.MultipleObjectsReturned:
            raise forms.ValidationError(self.error_messages['nick_name_used'], code='nick_name_used')

        # 校验邮箱,为空不做校验
        try:
            Users.objects.get(email=email)
            raise forms.ValidationError(self.error_messages['email_used'], code='email_used', params={'email': email})
        except Users.DoesNotExist:
            pass
        except Users.MultipleObjectsReturned:
            raise forms.ValidationError(self.error_messages['email_used'], code='email_used', params={'email': email})

        # check phone
        try:
            if phone:
                Users.objects.get(phone=phone)
                raise forms.ValidationError(self.error_messages['phone_used'], code='phone_used', params={'phone': phone})
        except Users.DoesNotExist:
            pass
        except Users.MultipleObjectsReturned:
            raise forms.ValidationError(self.error_messages['phone_used'], code='phone_used', params={'phone': phone})

        if password_repeat != password:
            raise forms.ValidationError(
                self.error_messages['password_repeat'],
                code='password_repeat',
            )

        return self.cleaned_data
