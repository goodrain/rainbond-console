from django.template.defaulttags import register
import datetime


@register.filter
def mkey(d, key):
    value = ""
    try:
        value = d[key]
    except Exception:
        pass
    return value


@register.filter
def mod(firstValue, factor):
    value = 0
    try:
        value = int(firstValue) % int(factor)
    except Exception:
        pass
    return value


@register.filter
def difftime(cur_date, sec):
    value = cur_date
    try:
        value = cur_date + datetime.timedelta(seconds=sec)
    except Exception:
        pass
    return value


@register.filter
def diffstrtime(cur_date, sec):
    
    value = cur_date
    try:
        st = datetime.datetime.strptime(cur_date, "%Y-%m-%d %H:%M:%S")
        tmp = st + datetime.timedelta(seconds=sec)
        value = tmp.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return value


