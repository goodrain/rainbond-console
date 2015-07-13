from django.template.defaulttags import register

@register.filter
def mkey(d, key):
    value=""
    try:
        value = d[key]
    except Exception:
        pass
    return value

@register.filter
def mod(firstValue, factor):
    value=0
    try:
        value = int(firstValue) % int(factor)
    except Exception:
        pass
    return value

