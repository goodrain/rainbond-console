# encoding=utf-8
import json


def attrlist2json(attr_list):

    dict = {}
    for attr in attr_list:
        if attr.attr_type == "boolean":
            if attr.attr_val.lower() == "true":
                dict[attr.attr_name] = True
            else:
                dict[attr.attr_name] = False
        elif attr.attr_type == "int":
            dict[attr.attr_name] = int(attr.attr_val)
        elif attr.attr_type == "float":
            dict[attr.attr_name] = float(attr.attr_val)
        else:
            dict[attr.attr_name] = attr.attr_val
    return json.dumps(dict, ensure_ascii=False)

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False