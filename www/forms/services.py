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
from www.models import TenantServiceEnvVar
from www.layout import Submit, Field
import widgets
import fields
from account import is_standard_word, is_sensitive, standard_regex_string

import logging

logger = logging.getLogger('default')


class ServicePublishForm(forms.Form):
    service_key = fields.CharField(
        required=False, max_length=32,
        validators=[is_standard_word, is_sensitive],
        min_length=3, ajax_check=True, pattern=standard_regex_string,
        label=u"应用key",
    )
    app_name = fields.CharField(
        required=True, max_length=40,
        min_length=3, ajax_check=True,
        label=u"应用名称",
    )
    app_version = fields.CharField(
        required=True, pattern="^\d+(\.\d+){1,2}",
        label=u"应用版本",
    )
    
    app_info = fields.CharField(
        required=True, min_length=5, max_length=100,
        widget=widgets.Textarea(attrs={'cols': '20', 'rows': '3'}),
        label=u"应用描述",
    )
    pay_type = fields.ChoiceField(
        choices=(('free', u'免费'), ('pay', u'付费')),
        initial="free",
        label=u"付费类型",
    )
    
    price = fields.DecimalField(
        required=False, min_value=0.00, initial=0.00,
        max_digits=4, decimal_places=2,
        widget=widgets.NumberInput(attrs={"step": 0.01}),
        label=u"价格",
    )
    
    change_log = fields.CharField(
        required=True, min_length=5, max_length=400,
        widget=widgets.Textarea(attrs={'cols': '20', 'rows': ''}),
        label=u"更新日志",
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
            del self.fields['service_key'].widget.attrs['data-remote']
            submit = Submit('update', u'更新', css_class='btn btn-lg btn-primary btn-block')
        else:
            submit = Submit('publish', u'发布', css_class='btn btn-lg btn-success btn-block')
        
        self.helper.layout = Layout(
            Field('service_key'),
            Field('app_name'),
            Field('app_version'),
            Field('app_info'),
            Field('pay_type'),
            Field('price'),
            Field('change_log'),
            FormActions(submit),
        )
        
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'


SENSITIVE_ENV_NAMES = (
    'TENANT_ID', 'SERVICE_ID', 'TENANT_NAME', 'SERVICE_NAME', 'SERVICE_VERSION', 'MEMORY_SIZE', 'SERVICE_EXTEND_METHOD',
    'SLUG_URL', 'DEPEND_SERVICE', 'REVERSE_DEPEND_SERVICE', 'POD_ORDER', 'PATH', 'PORT', 'POD_NET_IP', 'LOG_MATCH'
)


class EnvCheckForm(forms.ModelForm):
    class Meta:
        model = TenantServiceEnvVar
        fields = ('name', 'attr_name', 'attr_value')
    
    def clean(self):
        attr_name = self.cleaned_data.get("attr_name")
        
        if attr_name in SENSITIVE_ENV_NAMES:
            self.add_error('attr_name', u"不允许的变量名")
        
        if not re.match(r'^[A-Z][A-Z0-9_]*$', attr_name):
            self.add_error('attr_name', u"变量名称不符合规范")


class PublishServiceForm(forms.Form):
    """ 服务发布表单step1 """
    
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
            del self.fields['service_key'].widget.attrs['data-remote']
            submit = Submit('update', u'更新', css_class='btn btn-lg btn-primary btn-block')
        else:
            submit = Submit('publish', u'发布', css_class='btn btn-lg btn-success btn-block')
        
        self.helper.layout = Layout(
            Field('service_key'),
            Field('app_name'),
            Field('app_version'),
            Field('app_info'),
            Field('pay_type'),
            Field('price'),
            Field('change_log'),
            FormActions(submit),
        )
        
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
