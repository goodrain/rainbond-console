# -*- coding: utf8 -*-
import datetime
import json

from django.http import HttpResponse

from www.apiclient.regionapi import RegionInvokeApi
from www.models import Tenants, Users, TenantRegionInfo, TenantRecharge, TenantConsume, TenantServiceInfo, TenantPaymentNotify
from www.alipay_direct.alipay_api import *
from django.shortcuts import redirect
from www.service_http import RegionServiceApi
from www.utils.url import get_redirect_url
from www.monitorservice.monitorhook import MonitorHook
from www.models.activity import TenantActivity
import logging
logger = logging.getLogger('default')

BANKS = "zhifubao,BOCB2C,ICBCB2C,CMB,CCB,ABC,COMM"

monitorhook = MonitorHook()
region_api = RegionInvokeApi()

def submit(request, tenantName):
    html = ""
    if request.method == 'POST':
        try:
            paymethod = request.POST.get('optionsRadios', 'zhifubao')
            if BANKS.find(paymethod) < 0:
                path = '/apps/{0}/recharge/'.format(tenantName)
                return redirect(get_redirect_url(path, request))
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
                orderno = str(
                    uid) + str(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
                logger.debug(orderno)
                tenantRecharge.order_no = orderno
                tenantRecharge.recharge_type = "alipay"
                tenantRecharge.money = money
                tenantRecharge.subject = "好雨云平台充值"
                tenantRecharge.body = "好雨云平台充值"
                tenantRecharge.show_url = "https://user.goodrain.com/apps/" + \
                    tenantName + "/recharge"
                tenantRecharge.time = datetime.datetime.now().strftime(
                    '%Y-%m-%d %H:%M:%S')
                tenantRecharge.status = "TRADE_UNFINISHED"
                tenantRecharge.save()
                html = '<p>订单已经提交，准备进入支付宝官方收银台 ...</p>'
                submit = Alipay_API()
                html = submit.alipay_submit(paymethod, tenantName, tenantRecharge.order_no, tenantRecharge.subject, str(
                    tenantRecharge.money), tenantRecharge.body, tenantRecharge.show_url)
            else:
                path = '/apps/{0}/recharge/'.format(tenantName)
                return redirect(get_redirect_url(path, request))
        except Exception as e:
            html = ("%s" % e)
            logger.exception(e)
    return HttpResponse(html)


def notify_url(request, tenantName):
    try:
        out_trade_no = request.POST.get('out_trade_no', '')
        trade_no = request.POST.get('trade_no', '')
        trade_status = request.POST.get('trade_status', '')
            
        logger.debug("out_trade_no=" + out_trade_no)
        logger.debug("trade_no=" + trade_no)
        logger.debug("trade_status=" + trade_status)
        if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
            tenantRecharge = TenantRecharge.objects.get(order_no=out_trade_no)
            if tenantRecharge.trade_no is None or tenantRecharge.trade_no == "":
                tenantRecharge.status = trade_status
                tenantRecharge.trade_no = trade_no
                tenantRecharge.save()
                tempMoney = 0
                # recharge send money
                # tempMoney = int(tenantRecharge.money) / 100 * 50
                # if tempMoney > 0:
                #    sendRecharge = TenantRecharge()
                #    sendRecharge.tenant_id = tenantRecharge.tenant_id
                #    sendRecharge.user_id = tenantRecharge.user_id
                #    sendRecharge.user_name = tenantRecharge.user_name
                #    sendRecharge.order_no = tenantRecharge.order_no
                #    sendRecharge.recharge_type = "100send50"
                #    sendRecharge.money = tempMoney
                #    sendRecharge.subject = "充100值送50"
                #    sendRecharge.body = "充100值送50"
                #    sendRecharge.show_url = ""
                #    sendRecharge.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                #    sendRecharge.status = "TRADE_SUCCESS"
                #    sendRecharge.save()
                # concurrent question
                tenant = Tenants.objects.get(tenant_id=tenantRecharge.tenant_id)
                tenant.balance = tenant.balance + tenantRecharge.money + tempMoney
                if tenant.pay_type == "free":
                    tenant.pay_type = 'payed'
                tenant.save()
                # 删除activity998,结束后需要删除
                if tenantRecharge.money >= 500:
                    TenantActivity.objects.filter(tenant_id=tenantRecharge.tenant_id).delete()

                # charging owed money
                last_money = 0.0
                openServiceTag = True
                recharges = TenantConsume.objects.filter(
                    tenant_id=tenantRecharge.tenant_id, pay_status="unpayed")
                if len(recharges) > 0:
                    for recharge in recharges:
                        temTenant = Tenants.objects.get(
                            tenant_id=tenantRecharge.tenant_id)
                        last_money = recharge.cost_money
                        if recharge.cost_money <= temTenant.balance:
                            logger.debug(
                                tenantRecharge.tenant_id + " charging owed money:" + str(recharge.cost_money))
                            temTenant.balance = float(
                                temTenant.balance) - float(recharge.cost_money)
                            temTenant.save()
                            recharge.payed_money = recharge.cost_money
                            recharge.pay_status = "payed"
                            recharge.save()
                        else:
                            openServiceTag = False
                # if stop service,need to open
                tenantNew = Tenants.objects.get(tenant_id=tenantRecharge.tenant_id)
                if openServiceTag and last_money < tenantNew.balance:
                    tenant_regions = TenantRegionInfo.objects.filter(
                        tenant_id=tenantRecharge.tenant_id, is_active=True)
                    for tenant_region in tenant_regions:
                        if tenant_region.service_status == 2:
                            tenantServices = TenantServiceInfo.objects.filter(
                                tenant_id=tenantRecharge.tenant_id, service_region=tenant_region.region_name)
                            for tenantService in tenantServices:
                                tenantService.deploy_version = datetime.datetime.now().strftime(
                                    '%Y%m%d%H%M%S')
                                tenantService.save()
                                body = {
                                    "deploy_version": tenantService.deploy_version,"enterprise_id":tenant.enterprise_id}

                                region_api.start_service(tenantService.service_region, tenantNew.tenant_name,
                                                         tenantService.service_alias, body)
                            tenant_region.service_status = 1
                            tenant_region.save()
                            # update notify
                    TenantPaymentNotify.objects.filter(
                        tenant_id=tenantRecharge.tenant_id).update(status='unvalid')
                monitorhook.rechargeMonitor(tenantRecharge.user_name, tenantRecharge.user_id, "recharge")
            else:
                logger.debug(out_trade_no + " recharge return result again")
        else:
            logger.debug(
                out_trade_no + " recharge trade_status=" + trade_status)
    except Exception as e:
        logger.exception(e)
    # path = '/apps/{0}/recharge/'.format(tenantName)
    # return redirect(get_redirect_url(path, request))
    return HttpResponse("success")


def return_url(request, tenantName):
    try:
        out_trade_no = request.GET.get('out_trade_no', '')
        trade_no = request.GET.get('trade_no', '')
        trade_status = request.GET.get('trade_status', '')
        logger.debug("out_trade_no=" + out_trade_no)
        logger.debug("trade_no=" + trade_no)
        logger.debug("trade_status=" + trade_status)
#        if trade_status == 'TRADE_SUCCESS' or trade_status == 'TRADE_FINISHED':
#            # tenantRecharge = TenantRecharge.objects.get(order_no=out_trade_no)
#            # tenantRecharge.status = trade_status
#            # tenantRecharge.trade_no = trade_no
#            # tenantRecharge.save()
#            # tenant = Tenants.objects.get(tenant_id=tenantRecharge.tenant_id)
#            # tenant.balance = tenant.balance + tenantRecharge.money
#            # tenant.pay_type = 'payed'
#            # tenant.save()
#        else:
#            logger.debug(
#                out_trade_no + " recharge trade_status=" + trade_status)
    except Exception as e:
        logger.exception(e)
    path = '/apps/{0}/recharge/'.format(tenantName)
    return redirect(get_redirect_url(path, request))
