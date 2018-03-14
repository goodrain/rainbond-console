# -*- coding: utf-8 -*-
import re
from django import forms
from django.forms.forms import Form

from www.models import Users

SENSITIVE_WORDS = (
    'root', 'goodrain', 'builder', 'app', 'tenant', 'tenants', 'service', 'services'
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
        raise forms.ValidationError(u"只可以使用小写英文字母、数字、中划线。")


def is_sensitive(value):
    if value in SENSITIVE_WORDS:
        raise forms.ValidationError(u"不允许的用户名")


def password_len(value):
    if len(value) < 8:
        raise forms.ValidationError(u"密码长度至少为8位")


class RegisterForm(Form):

    user_name = forms.CharField(
        required=True, max_length=24, label="",
        validators=[is_standard_word, is_sensitive]
    )

    email = forms.EmailField(
        required=True, max_length=32, label=""
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

    captcha_code = forms.CharField(
        required=True, label='',
    )

    real_captcha_code = forms.CharField(
        required=False, label='',
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

    def clean(self):
        # tenant_name = self.cleaned_data.get('tenant_name')
        nick_name = self.cleaned_data.get('user_name')
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')
        captcha_code = self.cleaned_data.get('captcha_code')
        real_captcha_code = self.cleaned_data.get('real_captcha_code')
        # invite_tag = self.cleaned_data.get('invite_tag')
        # machine_region = self.cleaned_data.get('machine_region')

        try:
            Users.objects.get(nick_name=nick_name)
            raise forms.ValidationError(
                self.error_messages['nick_name_used'],
                code='nick_name_used'
            )
        except Users.DoesNotExist:
            pass

        # 校验邮箱,为空不做校验
        try:
            Users.objects.get(email=email)
            raise forms.ValidationError(
                self.error_messages['email_used'],
                code='email_used',
                params={'email': email}
            )
        except Users.DoesNotExist:
            pass

        if password_repeat != password:
            raise forms.ValidationError(
                self.error_messages['password_repeat'],
                code='password_repeat',
            )

        if real_captcha_code is None or captcha_code is None or real_captcha_code.lower() != captcha_code.lower():
            raise forms.ValidationError(
                self.error_messages['captcha_code_error'],
                code='captcha_code_error'
            )

        # 判断是否邀请注册,邀请注册不校验租户
        # if invite_tag is None or invite_tag == "":
        #     try:
        #         Tenants.objects.get(tenant_name=tenant)
        #         if not sn.instance.is_private():
        #             raise forms.ValidationError(
        #                 self.error_messages['tenant_used'],
        #                 code='tenant_used',
        #                 params={'tenant': tenant}
        #             )
        #     except Tenants.DoesNotExist:
        #         pass

        # 数据中心不做校验,默认为ali-sh
        # if machine_region is None or machine_region == "" or machine_region == "1":
        #     pass
        # machine_region = "ali-sh"
        # raise forms.ValidationError(
        #     self.error_messages['machine_region_error'],
        #     code='machine_region_error',
        # )

        return self.cleaned_data
