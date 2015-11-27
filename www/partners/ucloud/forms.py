# -*- coding: utf8 -*-
from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div
from crispy_forms.bootstrap import FormActions
from www.layout import Submit

from www.forms import fields, widgets
from www.forms.account import is_standard_word, is_sensitive, standard_regex_string


class AppendInfoForm(forms.Form):

    nick_name = fields.CharField(
        required=True, max_length=24, label="昵称",
        validators=[is_standard_word, is_sensitive],
        pattern=standard_regex_string, ajax_check=True,
        widget=widgets.TextInput(attrs={"data-remote-error": u"昵称已存在"})
    )

    tenant = fields.CharField(
        required=True, max_length=40, label="团队名称",
        validators=[is_standard_word, is_sensitive],
        min_length=3, ajax_check=True, pattern=standard_regex_string,
        widget=widgets.TextInput(attrs={"data-remote-error": u"已存在"})
    )

    password = fields.CharField(
        required=True, label='git仓库密码',
        min_length=8, max_length=30,
        widget=widgets.PasswordInput(attrs={"id": "git-passwd", "data-toggle": "validator"}),
    )

    password_repeat = fields.CharField(
        required=True, label='确认密码',
        min_length=8, max_length=30,
        widget=widgets.PasswordInput(attrs={"id": "git-passwd-repeat", "data-match": "#git-passwd", "data-match-error": u"两次输入的密码不一致"}),
    )

    def __init__(self, *args, **kwargs):
        super(AppendInfoForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Div(
            'nick_name',
            'tenant',
            'password',
            'password_repeat',
            FormActions(Submit('commit', u'提交', css_class='btn btn-lg btn-primary btn-block')),
            css_class='login-wrap',
            style="background: #FFFFFF;",
        )

        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
