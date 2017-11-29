# -*- coding: utf8 -*-
from django.forms import widgets as w


class Input(w.Input):
    errors = {}
    help_block = None

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = self.errors
        else:
            attrs = dict(self.errors, **attrs)
        if self.is_required:
            attrs['required'] = True
        input_html = super(Input, self).render(name, value, attrs)
        if self.help_block is not None:
            return input_html + u'''<span class="help-block with-errors">{0}</span>'''.format(self.help_block)
        else:
            return input_html + u'''<div class="help-block with-errors"></div>'''


class TextInput(Input):
    input_type = 'text'
    errors = {"data-error": u"不合法"}

    def __init__(self, attrs=None):
        if attrs is not None:
            self.input_type = attrs.pop('type', self.input_type)
        super(TextInput, self).__init__(attrs)


class NumberInput(TextInput):
    input_type = 'number'


class EmailInput(TextInput):
    input_type = 'email'
    errors = {"data-error": u"邮件地址不正确"}


class URLInput(TextInput):
    input_type = 'url'
    errors = {"data-error": u"URL不合法"}


class PasswordInput(TextInput):
    input_type = 'password'

    def __init__(self, attrs=None, render_value=False):
        super(PasswordInput, self).__init__(attrs)
        self.render_value = render_value

    def render(self, name, value, attrs=None):
        if not self.render_value:
            value = None
        return super(PasswordInput, self).render(name, value, attrs)


class HiddenInput(Input):
    input_type = 'hidden'


class FileInput(Input):
    input_type = 'file'
    needs_multipart_form = True

    def render(self, name, value, attrs=None):
        return super(FileInput, self).render(name, None, attrs=attrs)

    def value_from_datadict(self, data, files, name):
        "File widgets take data from FILES, not POST"
        return files.get(name, None)


class Textarea(w.Textarea):

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        if self.is_required:
            attrs['required'] = True
        return super(Textarea, self).render(name, value, attrs)
