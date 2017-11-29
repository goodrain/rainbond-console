# -*- coding: utf8 -*-

import logging
from decimal import Decimal

from django.http import JsonResponse

from share.manager.region_provier import RegionProviderManager
from www.decorator import perm_required
from www.models import ServiceExtendMethod
from www.models.main import ServiceAttachInfo, ServiceFeeBill
from www.monitorservice.monitorhook import MonitorHook
from www.service_http import RegionServiceApi
from www.views import AuthedView
from django.views.decorators.cache import never_cache
import datetime
import json

logger = logging.getLogger('default')

monitorhook = MonitorHook()
rpmManager = RegionProviderManager()


class MemoryPayMethodView(AuthedView):
    """内存付费方式修改"""

    @never_cache
    @perm_required("manage_service")
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            service_fee_bill_list = ServiceFeeBill.objects.filter(tenant_id=self.tenant.tenant_id, service_id=self.service.service_id, pay_status="unpayed")
            if service_fee_bill_list:
                result["status"] = "unsupport"
                result["info"] = "磁盘包月包年尚未支付,请前往概览页支付"
                return JsonResponse(result,status=200)
            regionBo = rpmManager.get_work_region_by_name(self.service.service_region)
            memory_unit_fee = regionBo.memory_package_price
            now = datetime.datetime.now()
            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                service_id=self.service.service_id)
            # 如果磁盘为预付费
            if service_attach_info.disk_pay_method == "prepaid":
                buy_end_time = service_attach_info.buy_end_time
                # 计算剩余的预付费时间
                if buy_end_time > now:
                    left_hours = int((buy_end_time - now).total_seconds() / 3600)
                    # 不可选择
                    result["choosable"] = False
                    memory = Decimal(self.service.min_memory*self.service.min_node)
                    memory_fee = round(memory * memory_unit_fee * Decimal(left_hours) / 1024, 2)
                    result["memory_fee"] = memory_fee
                    result["left_hours"] = left_hours
                    result["memory_unit_fee"] = memory_unit_fee
                else:
                    result["choosable"] = True
                    result["memory_unit_fee"] = memory_unit_fee
            else:
                result["choosable"] = True
                result["memory_unit_fee"] = memory_unit_fee
            result["status"] = "success"
            result["memory"] = self.service.min_memory * self.service.min_node
        except Exception as e:
            result["status"] = "faliure"
            result["info"] = "操作失败"
            logger.exception(e)
        return JsonResponse(result, status=200)

    @never_cache
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        # pay_money = Decimal(request.POST.get("pay_money", 0.0))
        pay_period = int(request.POST.get("pay_period", 0))
        buy_days = pay_period
        change_method = request.POST.get("update_method", None)
        result = {}
        now = datetime.datetime.now()
        try:
            if not change_method:
                return JsonResponse({"status": "failure", "info": "参数错误"})

            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                service_id=self.service.service_id)
            # 如果为预付费改后付费
            if change_method == "pre2post":
                if service_attach_info.buy_end_time > now:
                    return JsonResponse({"status": "not_now", "info": "请在包月包年({0})结束后进行修改".format(
                        service_attach_info.buy_end_time.strftime("%Y-%m-%d %H:%M:%S"))}, status=200)
                else:
                    service_attach_info.memory_pay_method = "postpaid"
                    service_attach_info.save()
                    return JsonResponse({"status": "success", "info": "修改成功"}, status=200)
            # 后付费改预付费
            # service_fee_bill_list = ServiceFeeBill.objects.filter(tenant_id=self.tenant.tenant_id, service_id=self.service.service_id, pay_status="unpayed")
            # if service_fee_bill_list:
            #     result["status"] = "unsupport"
            #     result["info"] = "包月包年尚未支付,无法操作"
            #     return JsonResponse(result,status=200)
            regionBo = rpmManager.get_work_region_by_name(self.service.service_region)
            memory_unit_fee = regionBo.memory_package_price
            need_money = Decimal(0)
            memory = Decimal(self.service.min_memory*self.service.min_node)
            # 用来标识period为小时还是天
            is_period_hour = False
            if service_attach_info.disk_pay_method == "prepaid":
                buy_end_time = service_attach_info.buy_end_time
                is_period_hour = True
                # 计算剩余的预付费时间
                if buy_end_time > now:
                    left_hours = int((buy_end_time - now).total_seconds() / 3600)
                    need_money = memory_unit_fee * memory / 1024 * left_hours
                    pay_period = left_hours
                else:
                    is_period_hour = False
                    need_money = memory_unit_fee * memory / 1024 * 24 * 30 * pay_period
            else:
                is_period_hour = False
                need_money = memory_unit_fee * memory / 1024 * 24 * 30 * pay_period

            if need_money > 0:
                balance = self.tenant.balance
                if balance < need_money:
                    return JsonResponse({"status": "not_enough"}, status=200)
                else:
                    if not is_period_hour:
                        pay_period = pay_period * 24 * 30
                    create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    service_fee_bill = {"tenant_id": self.service.tenant_id, "service_id": self.service.service_id,
                                        "prepaid_money": need_money, "pay_status": "payed", "cost_type": "change_memory",
                                        "node_memory": self.service.min_memory, "node_num": self.service.min_node,
                                        "disk": 0, "buy_period": pay_period, "create_time": create_time,
                                        "pay_time": create_time}
                    ServiceFeeBill.objects.create(**service_fee_bill)
                    service_attach_info.memory_pay_method = "prepaid"
                    if not is_period_hour:
                        if service_attach_info.pre_paid_period <= 0:
                            service_attach_info.pre_paid_period = buy_days
                        service_attach_info.buy_start_time = now
                        days = buy_days * 30
                        service_attach_info.buy_end_time = now + datetime.timedelta(days=days)
                    service_attach_info.save()
                    self.tenant.balance = balance - need_money
                    self.tenant.save()
                    result["status"] = "success"
            result["status"] = "success"

        except Exception as e:
            result["status"] = "failure"
            result["info"] = "修改失败"
            logger.exception(e)
        return JsonResponse(result, status=200)


class DiskPayMethodView(AuthedView):
    """磁盘付费方式修改"""

    @never_cache
    @perm_required("manage_service")
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            service_fee_bill_list = ServiceFeeBill.objects.filter(tenant_id=self.tenant.tenant_id, service_id=self.service.service_id, pay_status="unpayed")
            if service_fee_bill_list:
                result["status"] = "unsupport"
                result["info"] = "内存包月包年尚未支付,请前往概览页支付"
                return JsonResponse(result,status=200)
            regionBo = rpmManager.get_work_region_by_name(self.service.service_region)
            disk_unit_fee = regionBo.disk_package_price
            now = datetime.datetime.now()
            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                service_id=self.service.service_id)
            if service_attach_info.memory_pay_method == "prepaid":
                buy_end_time = service_attach_info.buy_end_time
                # 计算剩余的预付费时间
                if buy_end_time > now:
                    left_hours = int((buy_end_time - now).total_seconds() / 3600)
                    # 时长不可选择
                    result["choosable"] = False
                    result["disk_unit_fee"] = disk_unit_fee
                    result["left_hours"] = left_hours
                else:
                    result["choosable"] = True
                    result["disk_unit_fee"] = disk_unit_fee
            else:
                result["choosable"] = True
                result["disk_unit_fee"] = disk_unit_fee
            result["status"] = "success"
        except Exception as e:
            result["status"] = "failure"
            logger.exception(e)
        return JsonResponse(result, status=200)

    @never_cache
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        # pay_money = request.POST.get("pay_money", 0.0)
        pay_period = int(request.POST.get("pay_period", 1))
        buy_disk = int(request.POST.get("pay_disk", 1))
        change_method = request.POST.get("update_method", None)

        buy_days = pay_period
        result = {}
        try:
            if not change_method:
                return JsonResponse({"status": "failure", "info": "参数错误"}, status=200)
            now = datetime.datetime.now()
            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                service_id=self.service.service_id)
            # 如果为预付费改后付费
            if change_method == "pre2post":
                if service_attach_info.buy_end_time > now:
                    return JsonResponse({"status": "not_now", "info": "请在包月包年({0})结束后进行修改".format(
                        service_attach_info.buy_end_time.strftime("%Y-%m-%d %H:%M:%S"))}, status=200)
                else:
                    service_attach_info.memory_pay_method = "postpaid"
                    service_attach_info.save()
                    return JsonResponse({"status": "success", "info": "修改成功"}, status=200)

            # # 判断是否有未付款订单
            # service_fee_bill_list = ServiceFeeBill.objects.filter(tenant_id=self.tenant.tenant_id, service_id=self.service.service_id, pay_status="unpayed")
            # if service_fee_bill_list:
            #     result["status"] = "unsupport"
            #     result["info"] = "内存包月包年尚未支付,无法操作"
            #     return JsonResponse(result, status=200)

            need_pay_money = Decimal(0)
            regionBo = rpmManager.get_work_region_by_name(self.service.service_region)
            disk_unit_fee = regionBo.disk_package_price
            disk_fee = 0.0
            is_period_hour = False
            if service_attach_info.memory_pay_method == "prepaid":
                buy_end_time = service_attach_info.buy_end_time
                # 计算剩余的预付费时间
                if buy_end_time >= now:
                    is_period_hour = True
                    left_hours = int((buy_end_time - now).total_seconds() / 3600)
                    disk_fee = float(disk_unit_fee) * buy_disk * left_hours
                    need_pay_money = Decimal(disk_fee)
                    pay_period = left_hours
                else:
                    disk_fee = buy_disk * disk_unit_fee * buy_days * 24 * 30
                    need_pay_money = Decimal(disk_fee)
            else:
                disk_fee = buy_disk * disk_unit_fee * buy_days * 24 * 30
                need_pay_money = Decimal(disk_fee)
            if not is_period_hour:
                pay_period = pay_period * 24 * 30

            if need_pay_money > 0:
                balance = self.tenant.balance
                if balance < need_pay_money:
                    return JsonResponse({"status": "not_enough"}, status=200)
                else:
                    create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    service_fee_bill = {"tenant_id": self.service.tenant_id, "service_id": self.service.service_id,
                                        "prepaid_money": need_pay_money, "pay_status": "payed", "cost_type": "change_disk",
                                        "node_memory": self.service.min_memory, "node_num": self.service.min_node,
                                        "disk": buy_disk*1024, "buy_period": pay_period,
                                        "create_time": create_time, "pay_time": create_time}
                    ServiceFeeBill.objects.create(**service_fee_bill)
                    service_attach_info.disk_pay_method = "prepaid"
                    service_attach_info.disk = buy_disk*1024
                    if not is_period_hour:
                        service_attach_info.pre_paid_period = buy_days
                        service_attach_info.buy_start_time = now
                        days = buy_days * 30
                        service_attach_info.buy_end_time = now+datetime.timedelta(days=days)
                    service_attach_info.save()
                    self.tenant.balance = balance - need_pay_money
                    self.tenant.save()
                    result["status"] = "success"
            result["status"] = "success"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
        return JsonResponse(result, status=200)


class ExtendServiceView(AuthedView):
    """扩容修改"""
    @never_cache
    @perm_required("manage_service")
    def get(self,request, *args, **kwargs):
        result = {}
        try:
            service_fee_bill_list = ServiceFeeBill.objects.filter(tenant_id=self.tenant.tenant_id, service_id=self.service.service_id, pay_status="unpayed")
            if service_fee_bill_list:
                result["status"] = "unsupport"
                result["info"] = "包月包年尚未支付,请前往概览页支付"
                return JsonResponse(result, status=200)

            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                service_id=self.service.service_id)
            regionBo = rpmManager.get_work_region_by_name(self.service.service_region)
            memory_unit_fee = regionBo.memory_package_price
            now = datetime.datetime.now()
            buy_end_time = service_attach_info.buy_end_time
            service_type = self.service.service_type
            result["node_choosable"] = False

            # 获取对应扩展数
            app_min_memory = 128
            app_max_memory = 65536
            sem = None
            try:
                sem = ServiceExtendMethod.objects.get(service_key=self.service.service_key, app_version=self.service.version)
            except ServiceExtendMethod.DoesNotExist:
                pass
            if sem:
                app_min_memory = sem.min_memory
                app_max_memory = sem.max_memory

            if service_type == "application" :
                result["node_choosable"] = True
            if service_attach_info.memory_pay_method == "prepaid" and buy_end_time > now:
                left_hours =int((buy_end_time - now).total_seconds()/3600)
                result["show_money"] = True
                result["status"] = "success"
                result["min_memory"] = self.service.min_memory
                result["min_node"] = self.service.min_node
                result["left_hours"] = left_hours
                result["memory_unit_fee"] = memory_unit_fee
                result["service_memory"] = service_attach_info.min_memory * self.service.min_node
                result["app_min_memory"] = service_attach_info.min_memory
                result["app_max_memory"] = app_max_memory
            else:
                result["show_money"] = False
                result["status"] = "success"
                result["memory_unit_fee"] = memory_unit_fee
                result["app_min_memory"] = app_min_memory
                result["app_max_memory"] = app_max_memory

        except Exception as e:
            result["status"] = "failure"
            result["info"] = "操作失败"
            logger.exception(e)
        return JsonResponse(result, status=200)

    @never_cache
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        node_num = int(request.POST.get("node_num", 1))
        node_memory = int(request.POST.get("node_memory", 128))
        result = {}
        balance = self.tenant.balance
        try:
            regionBo = rpmManager.get_work_region_by_name(self.service.service_region)
            memory_unit_fee = regionBo.memory_package_price
            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                service_id=self.service.service_id)
            cur_memory = service_attach_info.min_memory * service_attach_info.min_node
            now = datetime.datetime.now()
            buy_end_time = service_attach_info.buy_end_time
            need_pay_money = 0.0
            new_memory = node_num * node_memory
            if service_attach_info.memory_pay_method == "prepaid" and buy_end_time > now:
                if cur_memory > new_memory:
                    result["status"] = "failure"
                    result["info"] = "包月包年不支持缩容"
                    return JsonResponse(result, status=200)
                # if service_attach_info.min_memory == node_memory and cur_memory == node_num * node_memory:
                #     result["status"] = "no_change"
                #     result["info"] = "内存未发生修改"
                #     return JsonResponse(result, status=200)
                left_hours = int((buy_end_time - now).total_seconds() / 3600)
                memory_fee = float(memory_unit_fee) * (node_num * node_memory - cur_memory) / 1024.0 * left_hours
                need_pay_money = round(memory_fee, 2)
                if balance < need_pay_money:
                    result["status"] = "not_enough"
                    result["info"] = "账户余额不足"
                    return JsonResponse(result, status=200)
            # horizontal 水平扩容
            if node_num >= 0 and self.service.min_node != node_memory:
                body = {}
                body["node_num"] = node_num
                body["deploy_version"] = self.service.deploy_version
                body["operator"] = str(self.user.nick_name)
                # 费用也不进行真实扩容操作,只记录
                self.service.min_node = node_num
                self.service.save()
            # vertical 垂直扩容
            new_cpu = 20 * (node_memory / 128)
            old_cpu = self.service.min_cpu
            if new_cpu != old_cpu or self.service.min_memory != node_memory:
                if node_memory > 0:
                    body = {}
                    body["container_memory"] = node_memory
                    body["deploy_version"] = self.service.deploy_version
                    body["container_cpu"] = new_cpu
                    body["operator"] = str(self.user.nick_name)
                    logger.info("invocke region to verticalUpgrade")
                    self.service.min_memory = node_memory
                    self.service.min_cpu = new_cpu
                    self.service.save()

            service_attach_info.min_node = node_num
            service_attach_info.min_memory = node_memory
            service_attach_info.save()
            if service_attach_info.memory_pay_method == "prepaid" and buy_end_time > now:
                # 预付费期间扩容,扣钱
                create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                service_fee_bill = {"tenant_id": self.service.tenant_id, "service_id": self.service.service_id,
                                    "prepaid_money": need_pay_money, "pay_status": "payed", "cost_type": "extend",
                                    "node_memory": int(node_memory), "node_num": int(node_num),
                                    "disk": 0, "buy_period": 0, "create_time": create_time, "pay_time": create_time}
                ServiceFeeBill.objects.create(**service_fee_bill)
                if need_pay_money > 0:
                    self.tenant.balance = balance - Decimal(need_pay_money)
                    self.tenant.save()
                result["status"] = "success"
            else:
                result["status"] = "success"

        except Exception as e:
            result["status"] = "failure"
            result["info"] = "操作失败"
            logger.exception(e)
        return JsonResponse(result, status=200)


class PrePaidPostponeView(AuthedView):
    """预付费方式延期操作"""

    @never_cache
    @perm_required("manage_service")
    def get(self, request, *args, **kwargs):
        result = {}
        try:
            service_attach_info = ServiceAttachInfo.objects.get(service_id=self.service.service_id,
                                                                tenant_id=self.tenant.tenant_id)
            memory_pay_method = service_attach_info.memory_pay_method
            disk_pay_method = service_attach_info.disk_pay_method
            need_money = Decimal(0)
            service_fee_bill_list = ServiceFeeBill.objects.filter(tenant_id=self.tenant.tenant_id, service_id=self.service.service_id, pay_status="unpayed")
            if service_fee_bill_list:
                result["status"] = "unsupport"
                result["info"] = "包月包年尚未支付,请前往概览页支付"
                return JsonResponse(result,status=200)
            if memory_pay_method == "postpaid" and disk_pay_method == "postpaid":
                result["status"] = "no_prepaid"
                result["info"] = "没有包月包年项目无法延期"
                return JsonResponse(result, status=200)
            else:
                regionBo = rpmManager.get_work_region_by_name(self.service.service_region)
                pre_paid_memory_price = regionBo.memory_package_price
                pre_paid_disk_price = regionBo.disk_package_price
                if memory_pay_method == "prepaid":
                    memory_fee = (int(service_attach_info.min_memory) * int(service_attach_info.min_node)) / 1024.0 * float(pre_paid_memory_price)
                    need_money += Decimal(memory_fee)
                if disk_pay_method == "prepaid":
                    disk_fee = service_attach_info.disk / 1024.0 * float(pre_paid_disk_price)
                    need_money += Decimal(disk_fee)
            result["status"] = "success"
            result["unit_price"] = need_money
        except Exception as e:
            result["status"] = "failure"
            logger.exception(e)
        return JsonResponse(result, status=200)

    @never_cache
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        # 将现有的end_time 加上新续费的月份,新加的期限需要判断balance是否够用
        balance = Decimal(self.tenant.balance)
        extend_time = int(request.POST.get("pay_period", None))
        result = {}
        try:
            service_attach_info = ServiceAttachInfo.objects.get(service_id=self.service.service_id,
                                                                tenant_id=self.tenant.tenant_id)
            memory_pay_method = service_attach_info.memory_pay_method
            disk_pay_method = service_attach_info.disk_pay_method
            need_money = Decimal(0)
            # 没有预付费项目
            if memory_pay_method == "postpaid" and disk_pay_method == "postpaid":
                result["status"] = "no_prepaid"
                result["info"] = "没有包月包年项目无法延期"
                return JsonResponse(result, status=200)
            else:
                regionBo = rpmManager.get_work_region_by_name(self.service.service_region)
                pre_paid_memory_price = regionBo.memory_package_price
                pre_paid_disk_price = regionBo.disk_package_price
                if memory_pay_method == "prepaid":
                    memory_fee = int(service_attach_info.min_memory) * int(service_attach_info.min_node) / 1024.0 * float(pre_paid_memory_price)
                    need_money += Decimal(memory_fee)
                if disk_pay_method == "prepaid":
                    disk_fee = service_attach_info.disk / 1024.0 * float(pre_paid_disk_price)
                    need_money += Decimal(disk_fee)
                need_money = need_money * 24 * extend_time * 30
            if balance < need_money:
                result["status"] = "not_enough"
                return JsonResponse(result, status=200)
            create_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            service_fee_bill = {"tenant_id": self.service.tenant_id, "service_id": self.service.service_id,
                                "prepaid_money": need_money, "pay_status": "payed", "cost_type": "renew",
                                "node_memory": service_attach_info.min_memory, "node_num": service_attach_info.min_node,
                                "disk": service_attach_info.disk, "buy_period": extend_time * 30 * 24,
                                "create_time": create_time,"pay_time": create_time}
            ServiceFeeBill.objects.create(**service_fee_bill)
            now = datetime.datetime.now()
            if service_attach_info.buy_end_time < now:
                service_attach_info.buy_start_time = now
                service_attach_info.buy_end_time = now + datetime.timedelta(days=extend_time * 30)
                service_attach_info.save()
            else:
                service_attach_info.buy_end_time = service_attach_info.buy_end_time + datetime.timedelta(
                    days=extend_time * 30)
                service_attach_info.save()
            self.tenant.balance = balance - need_money
            self.tenant.save()

            result["status"] = "success"
            result["info"] = "修改成功"
        except Exception as e:
            logger.exception(e)
            result["status"] = "failure"
            result["info"] = "修改失败"
        return JsonResponse(result, status=200)


class PayPrepaidMoney(AuthedView):

    @never_cache
    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        service_id = self.service.service_id
        tenant_id = self.tenant.tenant_id
        balance = self.tenant.balance
        result = {}
        try:
            service_fee_bill = None
            service_fee_bill_list = ServiceFeeBill.objects.filter(tenant_id=tenant_id,service_id=service_id,pay_status="unpayed")
            if service_fee_bill_list:
                service_fee_bill = service_fee_bill_list[0]
            if service_fee_bill:
                need_to_pay_money = service_fee_bill.prepaid_money
                if balance < need_to_pay_money:
                    result["status"] = "not_enough"
                    result["info"] = "账户余额不足"
                    return JsonResponse(result, status=200)
                else:
                    service_fee_bill.pay_status = "payed"
                    service_fee_bill.save()
                    self.tenant.balance = balance - need_to_pay_money
                    self.tenant.save()
                    result["status"] = "success"
                    result["info"] = "付款成功"
        except Exception as e:
            result["status"] = "failure"
            result["info"] = "修改失败"
            logger.exception(e)
        return JsonResponse(result, status=200)