# -*- coding: utf8 -*-
import logging
import hashlib
import datetime

from django.http import HttpResponse, HttpResponseRedirect
from www.models import TenantRecharge
from www.alipay_direct.alipay_api import *

import logging
logger = logging.getLogger('default')

def submit(request,tenantName):
    html = ""
    if request.method == 'POST':       
        try:
            money = float(request.POST.get('recharge_money', '0'))
            if money > 0:            
                tenant_id = self.tenant.tenant_id
                uid = self.user.pk
                nick_name = self.user.nick_name
                tenantRecharge = TenantRecharge()
                tenantRecharge.tenant_id = tenant_id
                tenantRecharge.user_id = uid
                tenantRecharge.user_name = nick_name
                tenantRecharge.order_no = str(uid) + datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                tenantRecharge.recharge_type = "alipay"
                tenantRecharge.money = money
                tenantRecharge.subject = "好雨云平台充值"
                tenantRecharge.body = "好雨云平台充值"
                tenantRecharge.show_url = "http://user.goodrain.com/" + self.tenantName + "/recharge"
                tenantRecharge.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                tenantRecharge.save()
                html = '<p>订单已经提交，准备进入支付宝官方收银台 ...</p>'
                submit = Alipay_API()
                html = submit.alipay_submit(self.tenantName, tenantRecharge.order_no, tenantRecharge.subject, tenantRecharge.money, tenantRecharge.body, tenantRecharge.show_url)
        except Exception as e:
            html = ("%s" % e)
            logger.exception(e)
    return HttpResponse(html)

def return_url(request,tenantName): 
    html = "error"
    try:
        out_trade_no = request.GET.get('out_trade_no', '')
        trade_no = request.GET.get('trade_no', '')
        trade_status = request.GET.get('trade_status', '')
        if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
            tenantRecharge = TenantRecharge.objects.get(order_no=out_trade_no)
            tenantRecharge.status = trade_status
            tenantRecharge.trade_no = trade_no
            tenantRecharge.save()
            html = "ok"
        else:
            logger.debug(out_trade_no + " recharge trade_status=" + trade_status)          
    except Exception as e:
        html = ("%s" % e)
        logger.exception(e)
    return HttpResponse(html)
            
def notify_url(request,tenantName):
    html = "error"
    try:
        out_trade_no = request.GET.get('out_trade_no', '')
        trade_no = request.GET.get('trade_no', '')  # 支付宝交易号
        trade_status = request.GET.get('trade_status', '')
        if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
            tenantRecharge = TenantRecharge.objects.get(order_no=out_trade_no)
            tenantRecharge.status = trade_status
            tenantRecharge.trade_no = trade_no
            tenantRecharge.save()
            html = "ok"
        else:
            logger.debug(out_trade_no + " recharge trade_status=" + trade_status)          
    except Exception as e:
        html = ("%s" % e)
        logger.exception(e)
    return HttpResponse(html)
    
        

