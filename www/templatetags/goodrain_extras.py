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
def strToInt(value):
    return int(value)

@register.filter
def hasvalue(list,key):
    value = False;
    try:
        if key in list:
            value = True
    except Exception:
        pass
    return value

@register.filter
def multiply(num1, num2):
    value = 0
    try:
        value = num1 * num2
    except Exception:
        pass
    return value