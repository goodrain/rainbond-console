# -*- coding: utf8 -*-
from django.forms import fields as f
import widgets


class Field(f.Field):
    widget = widgets.TextInput

    def __init__(self, ajax_check=False, ajax_check_error=None, pattern=None, pattern_error=None, *args, **kwargs):
        self.ajax_check, self.ajax_check_error, self.pattern, self.pattern_error = ajax_check, ajax_check_error, pattern, pattern_error
        '''
        if self.ajax_check and self.ajax_check_error is None:
            self.ajax_check_error = u"不能使用"
        if self.pattern and self.pattern_error is None:
            self.pattern_error = u"格式不匹配"
        '''
        super(Field, self).__init__(*args, **kwargs)
        self.widget.help_block = self.help_text

    def widget_attrs(self, widget):
        attrs = super(Field, self).widget_attrs(widget)
        if self.ajax_check is True:
            attrs.update({'data-remote': '/ajax/form_valid'})
        if self.pattern is not None:
            attrs.update({'pattern': self.pattern})
        return attrs


class CharField(Field, f.CharField):

    def widget_attrs(self, widget):
        attrs = super(CharField, self).widget_attrs(widget)
        if self.max_length is not None:
            attrs.update({'maxlength': str(self.max_length)})
        if self.min_length is not None:
            attrs.update({'data-minlength': str(self.min_length)})
        return attrs


class EmailField(CharField, f.EmailField):
    widget = widgets.EmailInput


class IntegerField(Field, f.IntegerField):
    widget = widgets.NumberInput

    def widget_attrs(self, widget):
        attrs = super(IntegerField, self).widget_attrs(widget)
        if isinstance(widget, widgets.NumberInput):
            if self.min_value is not None:
                attrs['min'] = self.min_value
            if self.max_value is not None:
                attrs['max'] = self.max_value
        return attrs


class DecimalField(IntegerField, f.DecimalField):
    pass


class ChoiceField(f.ChoiceField):
    pass
