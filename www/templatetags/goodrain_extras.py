from django.template.defaulttags import register

@register.filter
def mkey(d, key):
    value=""
    try:
        value = d[key]
    except Exception:
        pass
    return value
