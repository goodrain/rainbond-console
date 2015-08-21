# -*- coding: utf8 -*-
import logging
import hashlib
import datetime

from django.http import HttpResponse, HttpResponseRedirect
from www.models import TenantRecharge, TenantConsume, TenantServiceInfo
from www.alipay_direct.alipay_api import *
from www.models import Tenants, Users
from django.shortcuts import redirect
from www.service_http import RegionServiceApi

import logging
logger = logging.getLogger('default')

BANKS = "zhifubao,BOCB2C,ICBCB2C,CMB,CCB,ABC,COMM"

def submit(request, tenantName):
    html = ""
    if request.method == 'POST':       
        try:
            paymethod = request.POST.get('optionsRadios', 'zhifubao')
            if BANKS.find(paymethod) < 0:
                return redirect('/apps/{0}/recharge/'.format(tenantName))
            logger.debug(paymethod)
            money = float(request.POST.get('recharge_money', '0'))
            if money > 0:      
                tenant = Tenants.objects.get(tenant_name=tenantName)      
                tenant_id = tenant.tenant_id
                uid = request.session.get("_auth_user_id")
                user = Users.objects.get(user_id=uid)
                nick_name = user.nick_name
                logger.debug(uid)
                logger.debug(nick_name)
                tenantRecharge = TenantRecharge()
                tenantRecharge.tenant_id = tenant_id
                tenantRecharge.user_id = uid
                tenantRecharge.user_name = nick_name
                orderno = str(uid) + str(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
                logger.debug(orderno)
                tenantRecharge.order_no = orderno
                tenantRecharge.recharge_type = "alipay"
                tenantRecharge.money = money
                tenantRecharge.subject = "好雨云平台充值"
                tenantRecharge.body = "好雨云平台充值"
                tenantRecharge.show_url = "http://user.goodrain.com/" + tenantName + "/recharge"
                tenantRecharge.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                tenantRecharge.status = "TRADE_UNFINISHED"
                tenantRecharge.save()
                html = '<p>订单已经提交，准备进入支付宝官方收银台 ...</p>'
                submit = Alipay_API()
                html = submit.alipay_submit(paymethod, tenantName, tenantRecharge.order_no, tenantRecharge.subject, str(tenantRecharge.money), tenantRecharge.body, tenantRecharge.show_url)
            else:
                return redirect('/apps/{0}/recharge/'.format(tenantName))
        except Exception as e:
            html = ("%s" % e)
            logger.exception(e)
    return HttpResponse(html)

def return_url(request, tenantName): 
    try:
        out_trade_no = request.GET.get('out_trade_no', '')
        trade_no = request.GET.get('trade_no', '')
        trade_status = request.GET.get('trade_status', '')
        logger.debug(out_trade_no)
        logger.debug(trade_no)
        logger.debug(trade_status)
        if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
            tenantRecharge = TenantRecharge.objects.get(order_no=out_trade_no)
            tenantRecharge.status = trade_status
            tenantRecharge.trade_no = trade_no
            tenantRecharge.save()
            # concurrent question
            tenant = Tenants.objects.get(tenant_id=tenantRecharge.tenant_id)
            tenant.balance = tenant.balance + tenantRecharge.money
            tenant.pay_type = 'payed'
            tenant.save()
            # charging owed money
            openServiceTag = True
            recharges = TenantConsume.objects.filter(tenant_id=tenantRecharge.tenant_id, pay_status="unpayed")
            if len(recharges) > 0:
                for recharge in recharges:
                    temTenant = Tenants.objects.get(tenant_id=tenantRecharge.tenant_id)
                    if recharge.cost_money <= temTenant.balance:
                        logger.debug(tenantRecharge.tenant_id + " charging owed money:" + str(recharge.cost_money))
                        temTenant.balance = float(temTenant.balance) - float(recharge.cost_money)
                        temTenant.save()
                        recharge.payed_money = recharge.cost_money
                        recharge.pay_status = "payed"
                        recharge.save()
                    else:
                        openServiceTag = False
            # if stop service,need to open
            tenantNew = Tenants.objects.get(tenant_id=tenantRecharge.tenant_id)
            if tenantNew.service_status == 2 and openServiceTag:
                tenantServices = TenantServiceInfo.objects.filter(tenant_id=tenantRecharge.tenant_id)
                if len(tenantServices) > 0:
                    client = RegionServiceApi()
                    for tenantService in tenantServices:
                        client.restart(tenantService.service_id)
                tenantNew.service_status = 1
                tenantNew.save()
        else:
            logger.debug(out_trade_no + " recharge trade_status=" + trade_status)          
    except Exception as e:
        logger.exception(e)
    return redirect('/apps/{0}/recharge/'.format(tenantName))
            
def notify_url(request, tenantName):
    try:
        out_trade_no = request.GET.get('out_trade_no', '')
        trade_no = request.GET.get('trade_no', '')
        trade_status = request.GET.get('trade_status', '')
        logger.debug(out_trade_no)
        logger.debug(trade_no)
        logger.debug(trade_status)
        if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
            tenantRecharge = TenantRecharge.objects.get(order_no=out_trade_no)
            tenantRecharge.status = trade_status
            tenantRecharge.trade_no = trade_no
            tenantRecharge.save()
            tenant = Tenants.objects.get(tenant_id=tenantRecharge.tenant_id)
            # tenant.balance = tenant.balance + tenantRecharge.money
            tenant.pay_type = 'payed'
            tenant.save()
        else:
            logger.debug(out_trade_no + " recharge trade_status=" + trade_status)          
    except Exception as e:
        logger.exception(e)
    return redirect('/apps/{0}/recharge/'.format(tenantName))
    
        

