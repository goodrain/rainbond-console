# -*- coding: utf-8 -*-
import requests;
import json;
import logging
logger = logging.getLogger('default')

def send_phone_message(phone, phonecode):
    resp = requests.post(("http://api.weimi.cc/2/sms/send.html"),
    data={
        "uid": "aIrG6RTFJqrR ",
        "pas": "u49kq92r",
        "mob": phone,
        "cid": "fo92yWNMWIss",
        "p1":phonecode,
        "type": "json"
    }, timeout=3 , verify=False);    
    result = json.loads(resp.content)
    logger.debug(result)
