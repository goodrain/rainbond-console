# -*- coding: utf8 -*-
import re
from django import forms
from django.forms.widgets import Select
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Fieldset, ButtonHolder, HTML, Row
from crispy_forms.bootstrap import (AppendedText, FieldWithButtons, StrictButton, InlineField,
                                    PrependedText, FormActions, AccordionGroup, InlineCheckboxes)
from www.models import Users, Tenants, PhoneCode
from www.layout import Submit, Field
import widgets
import fields
from account import is_standard_word, is_sensitive, standard_regex_string

import logging
logger = logging.getLogger('default')


class ServicePublishForm(forms.Form):
    app_key = fields.CharField(
        required=True, max_length=32,
        validators=[is_standard_word, is_sensitive],
        min_length=3, ajax_check=True, pattern=standard_regex_string,
    )
    app_name = fields.CharField(
        required=True, max_length=40,
        min_length=3
    )
    app_version = fields.CharField(
        required=True, pattern="^\d+(\.\d+){1,2}"
    )
    app_info = fields.CharField(
        required=True, min_length=5, max_length=100,
        widget=widgets.Textarea(attrs={'cols': '20', 'rows': '3'})
    )
    pay_type = fields.ChoiceField(
        choices=(('free', u'免费'), ('pay', u'付费')),
        initial="free",
    )

    price = fields.DecimalField(
        required=False, min_value=0.00, initial=0.00,
        max_digits=4, decimal_places=2,
        widget=widgets.NumberInput(attrs={"step": 0.01})
    )

    change_log = fields.CharField(
        required=True, min_length=5, max_length=400,
        widget=widgets.Textarea(attrs={'cols': '20', 'rows': ''})
    )

    def __init__(self, *args, **kwargs):
        initial = kwargs.pop('initial', None)
        is_update = kwargs.pop('is_update', False)

        super(ServicePublishForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False

        if initial is not None:
            for field in initial:
                value = initial[field]['value']
                attrs = initial[field].get('attrs', {})
                self.fields[field].initial = value
                self.fields[field].widget.attrs.update(attrs)

        if is_update:
            del self.fields['app_key'].widget.attrs['data-remote']
            submit = Submit('update', u'更新', css_class='btn btn-lg btn-primary btn-block')
        else:
            submit = Submit('publish', u'发布', css_class='btn btn-lg btn-success btn-block')

        self.helper.layout = Div(
            Field('app_key', css_class="form-control", placeholder=u'应用'),
            Field('app_name', css_class="form-control", placeholder=u'应用名称'),
            Field('app_version', css_class="form-control", placeholder='应用版本'),
            Field('app_info', css_class="form-control", placeholder='应用描述'),
            Field('pay_type', css_class="form-control", placeholder='付费类型'),
            Field('price', css_class="form-control", placeholder='价格'),
            Field('change_log', css_class="form-control", placeholder='更新日志'),
            FormActions(submit),
            css_class='login-wrap',
            style="background: #FFFFFF;",
        )

        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.form_id = 'form-user-login'
        self.helper.form_class = 'form-horizontal'
