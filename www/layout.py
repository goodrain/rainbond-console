from crispy_forms import layout
from crispy_forms import bootstrap


class Field(layout.Field):
    #template = 'widgets/field.html'
    pass


class InlineField(bootstrap.InlineField):
    #template = 'widgets/inline_field.html'
    pass


class Submit(layout.Submit):
    #field_classes = ''
    pass
