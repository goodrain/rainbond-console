# -*- coding: utf8 -*-
import datetime
import json
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache

from share.manager.region_provier import RegionProviderManager
from www.models import ServiceAttachInfo, ServiceFeeBill
from www.models.main import TenantServiceInfo
from www.tenantservice.baseservice import ServiceAttachInfoManage
from www.views import AuthedView, LeftSideBarMixin, JsonResponse

logger = logging.getLogger('default')
rpmManager = RegionProviderManager()
attachManage = ServiceAttachInfoManage()

class BatchRenewView(LeftSideBarMixin, AuthedView):
    def __init__(self, *args, **kwargs):
        super(BatchRenewView, self).__init__(*args, **kwargs)
        tenant_id = self.tenant.tenant_id
        self.service_list = TenantServiceInfo.objects.filter(tenant_id=tenant_id,
                                                             service_region=self.response_region).values("service_id",
                                                                                                         "service_cname",
                                                                                                         "service_alias",
                                                                                                         "min_memory",
                                                                                                         "min_node")
        self.service_id_list = [elem["service_id"] for elem in self.service_list]
        self.id_name_map = {elem["service_id"]: elem["service_cname"] for elem in self.service_list}
        self.id_alias_map = {elem["service_id"]: elem["service_alias"] for elem in self.service_list}
        self.id_service_map = {elem["service_id"]: {"min_memory": elem["min_memory"], "min_node": elem["min_node"]}
                               for elem in self.service_list}

        regionBo = rpmManager.get_work_region_by_name(self.response_region)
        self.pre_paid_memory_price = regionBo.memory_package_price
        self.pre_paid_disk_price = regionBo.disk_package_price

    def update_service_attach_info(self, attach_info):
        if not attachManage.is_during_monthly_payment(attach_info):
            service_map = self.id_service_map[attach_info.service_id]
            service_min_memory = service_map["min_memory"]
            service_min_node = service_map["min_node"]
            attach_info.memory_pay_method = "postpaid"
            attach_info.disk_pay_method = "postpaid"
            attach_info.save()
            if attachManage.is_need_to_update(attach_info, service_min_memory, service_min_node):
                attach_info.min_memory = service_min_memory
                attach_info.min_node = service_min_node
                attach_info.save()

    @never_cache
    def get(self, request, *args, **kwargs):
        action = request.GET.get("action", None)
        try:

            common_info = {}
            common_info["tenant_name"] = self.tenant.tenant_name
            common_info["batchRenew"] = "active"
            common_info["myFinanceStatus"] = "active"
            common_info["cur_balance"] = self.tenant.balance
            if not action:
                # 所有数据
                attach_info_list = self.get_all_attach_info()
                result = self.generate_result("0000", "success", "查询成功", bean=common_info, list=attach_info_list)
                return JsonResponse(result, status=200)
            else:
                # 有包月项目的应用
                if action == "batch":
                    attach_info_list = self.get_prepaid_service_attach()
                    result = self.generate_result("0000", "success", "查询成功", bean=common_info, list=attach_info_list)
                    return JsonResponse(result, status=200)
                elif action == "batch-memory":
                    type = request.GET.get("type", "prepaid_disk")
                    attach_info_list = self.get_unprepaid_memory_service_attach(type)
                    result = self.generate_result("0000", "success", "查询成功", bean=common_info, list=attach_info_list)
                    return JsonResponse(result, status=200)
                elif action == "batch-disk":
                    type = request.GET.get("type", "prepaid_memory")
                    attach_info_list = self.get_unprepaid_disk_service_attach(type)
                    result = self.generate_result("0000", "success", "查询成功", bean=common_info, list=attach_info_list)
                    return JsonResponse(result, status=200)
                else:
                    result = self.generate_result("9999", "params error", "参数错误")
                    return JsonResponse(result, status=200)
        except Exception as e:
            logger.exception(e)
            return JsonResponse({}, status=500)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", None)
        if not action:
            result = self.generate_result("9999", "params error", "参数错误")
            return JsonResponse(result, status=200)
        json_data = request.POST.get("data", "")
        if not json_data:
            result = self.generate_result("9999", "params error", "参数错误")
            return JsonResponse(result, status=200)
        try:
            data = json.loads(json_data)
            res = None
            if action == "batch":
                res = self.batch_renew(data)
            elif action == "batch-memory":
                type = request.POST.get("type", "prepaid_disk")
                res = self.batch_memory_renew(data, type)
            elif action == "batch-disk":
                type = request.POST.get("type", "prepaid_memory")
                res = self.batch_disk_renew(data, type)
            if res and res["ok"]:
                result = self.generate_result("0000", "success", "批量操作成功")
            else:
                result = self.generate_result("9999", res["status"], res["msg"])
            return JsonResponse(result, status=200)

        except Exception as e:
            logger.exception(e)
            return JsonResponse({}, status=500)

    def get_all_attach_info(self):
        """
        获取当前租户的所有应用的付费信息
        :return:
        """
        service_attach_list = ServiceAttachInfo.objects.filter(service_id__in=self.service_id_list).order_by("buy_end_time")
        attach_info_list = []
        for attach_info in service_attach_list:
            self.update_service_attach_info(attach_info)
            attach_info_map = {}
            info_dict = attach_info.to_dict()
            attach_info_map.update(info_dict)
            attach_info_map["service_cname"] = self.id_name_map.get(attach_info.service_id)
            attach_info_map["service_alias"] = self.id_alias_map.get(attach_info.service_id)
            attach_info_map["unit_memory_fee"] = self.pre_paid_memory_price
            attach_info_map["unit_disk_fee"] = self.pre_paid_disk_price
            attach_info_map["tenant_name"] = self.tenant.tenant_name
            attach_info_list.append(attach_info_map)
        return attach_info_list

    def get_prepaid_service_attach(self):
        """
        获取内存或磁盘中任意一类包月的项目
        :return:
        """
        service_attach_list = ServiceAttachInfo.objects.filter(service_id__in=self.service_id_list)
        # 内存预付费
        prepay_memory = Q(memory_pay_method="prepaid")
        # 磁盘预付费
        prepay_disk = Q(disk_pay_method="prepaid")
        # 付费期内
        now = datetime.datetime.now()
        during_payment = Q(buy_end_time__gt=now)
        prepay_services = service_attach_list.filter((prepay_memory | prepay_disk) & during_payment).order_by("buy_end_time")
        attach_info_list = []
        for attach_info in prepay_services:
            self.update_service_attach_info(attach_info)
            attach_info_map = {}
            info_dict = attach_info.to_dict()
            attach_info_map.update(info_dict)
            attach_info_map["service_cname"] = self.id_name_map.get(attach_info.service_id)
            attach_info_map["service_alias"] = self.id_alias_map.get(attach_info.service_id)
            attach_info_map["unit_memory_fee"] = self.pre_paid_memory_price
            attach_info_map["unit_disk_fee"] = self.pre_paid_disk_price
            attach_info_map["tenant_name"] = self.tenant.tenant_name
            need_money = Decimal(0)
            if attach_info.memory_pay_method == "prepaid":
                memory_fee = (int(attach_info.min_memory) * int(attach_info.min_node)) / 1024.0 * float(
                    self.pre_paid_memory_price)
                need_money += Decimal(memory_fee)
            if attach_info.disk_pay_method == "prepaid":
                disk_fee = attach_info.disk / 1024.0 * float(self.pre_paid_disk_price)
                need_money += Decimal(disk_fee)
            attach_info_map["need_money"] = round(need_money,5)

            attach_info_list.append(attach_info_map)
        return attach_info_list

    def get_unprepaid_memory_service_attach(self, type):
        """
        批量内存包月(应用内存未包月)
        :param type: 类型
        :return:
        """
        service_attach_list = ServiceAttachInfo.objects.filter(service_id__in=self.service_id_list)
        # 内存预付费
        prepay_memory = Q(memory_pay_method="prepaid")
        # 磁盘预付费
        prepay_disk = Q(disk_pay_method="prepaid")
        now = datetime.datetime.now()
        during_payment = Q(buy_end_time__gt=now)
        if type == "prepaid_disk":
            attach_list = service_attach_list.filter(~prepay_memory & prepay_disk & during_payment).order_by("buy_end_time")
            attach_info_list = []
            for attach_info in attach_list:
                self.update_service_attach_info(attach_info)
                attach_info_map = {}
                info_dict = attach_info.to_dict()
                attach_info_map.update(info_dict)
                attach_info_map["service_cname"] = self.id_name_map.get(attach_info.service_id)
                attach_info_map["service_alias"] = self.id_alias_map.get(attach_info.service_id)
                attach_info_map["unit_memory_fee"] = self.pre_paid_memory_price
                attach_info_map["unit_disk_fee"] = self.pre_paid_disk_price
                attach_info_map["tenant_name"] = self.tenant.tenant_name
                left_hours = int((attach_info.buy_end_time - now).total_seconds() / 3600)
                memory = Decimal(attach_info.min_memory * attach_info.min_node)
                need_money = round(float(memory * self.pre_paid_memory_price) / 1024.0, 5)
                attach_info_map["need_money"] = need_money
                attach_info_map["hours"] = left_hours
                attach_info_list.append(attach_info_map)
            return attach_info_list

        elif type == "postpaid_disk":
            attach_list = service_attach_list.filter(~prepay_memory & ~prepay_disk).order_by("buy_end_time")
            attach_info_list = []
            for attach_info in attach_list:
                self.update_service_attach_info(attach_info)
                attach_info_map = {}
                info_dict = attach_info.to_dict()
                attach_info_map.update(info_dict)
                attach_info_map["service_cname"] = self.id_name_map.get(attach_info.service_id)
                attach_info_map["service_alias"] = self.id_alias_map.get(attach_info.service_id)
                attach_info_map["tenant_name"] = self.tenant.tenant_name
                memory = Decimal(attach_info.min_memory * attach_info.min_node)
                need_money = round(float(memory * self.pre_paid_memory_price) / 1024.0, 5)
                attach_info_map["need_money"] = need_money
                attach_info_map["unit_memory_fee"] = self.pre_paid_memory_price
                attach_info_map["unit_disk_fee"] = self.pre_paid_disk_price
                attach_info_list.append(attach_info_map)
            return attach_info_list

    def get_unprepaid_disk_service_attach(self, type):
        """
        批量磁盘包月
        :param type: 类型
        :return:
        """
        service_attach_list = ServiceAttachInfo.objects.filter(service_id__in=self.service_id_list)
        # 内存预付费
        prepay_memory = Q(memory_pay_method="prepaid")
        # 磁盘预付费
        prepay_disk = Q(disk_pay_method="prepaid")
        now = datetime.datetime.now()
        during_payment = Q(buy_end_time__gt=now)

        if type == "prepaid_memory":
            attach_list = service_attach_list.filter(prepay_memory & ~prepay_disk & during_payment).order_by("buy_end_time")
            attach_info_list = []
            for attach_info in attach_list:
                self.update_service_attach_info(attach_info)
                attach_info_map = {}
                info_dict = attach_info.to_dict()
                attach_info_map.update(info_dict)
                attach_info_map["service_cname"] = self.id_name_map.get(attach_info.service_id)
                attach_info_map["service_alias"] = self.id_alias_map.get(attach_info.service_id)
                attach_info_map["tenant_name"] = self.tenant.tenant_name
                attach_info_map["unit_memory_fee"] = self.pre_paid_memory_price
                attach_info_map["unit_disk_fee"] = self.pre_paid_disk_price
                left_hours = int((attach_info.buy_end_time - now).total_seconds() / 3600)

                disk = Decimal(attach_info.disk)
                need_money = round(float(disk * self.pre_paid_disk_price) / 1024.0, 5)
                attach_info_map["hours"] = left_hours
                attach_info_map["need_money"] = need_money
                attach_info_list.append(attach_info_map)
            return attach_info_list
        elif type == "postpaid_memory":
            attach_list = service_attach_list.filter(~prepay_disk & ~prepay_memory).order_by("buy_end_time")
            attach_info_list = []
            for attach_info in attach_list:
                self.update_service_attach_info(attach_info)
                attach_info_map = {}
                info_dict = attach_info.to_dict()
                attach_info_map.update(info_dict)
                attach_info_map["service_cname"] = self.id_name_map.get(attach_info.service_id)
                attach_info_map["service_alias"] = self.id_alias_map.get(attach_info.service_id)
                attach_info_map["tenant_name"] = self.tenant.tenant_name
                disk = Decimal(attach_info.disk)
                need_money = round(float(disk * self.pre_paid_disk_price) / 1024.0, 5)
                attach_info_map["need_money"] = need_money
                attach_info_map["unit_memory_fee"] = self.pre_paid_memory_price
                attach_info_map["unit_disk_fee"] = self.pre_paid_disk_price
                attach_info_list.append(attach_info_map)
            return attach_info_list

    def batch_renew(self, data):
        """将包月应用延期"""
        result = {}
        id_extendTime_map = {elem["service_id"]: elem["month_num"] for elem in data}
        service_id_list = id_extendTime_map.keys()
        renew_attach_infos = ServiceAttachInfo.objects.filter(service_id__in=service_id_list)
        renew_attach_infos = list(renew_attach_infos)

        total_money = Decimal(0)
        create_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bills = []
        try:
            for ps in renew_attach_infos:
                renew_money = Decimal(0)
                if ps.memory_pay_method == "prepaid":
                    memory_fee = (int(ps.min_memory) * int(ps.min_node)) / 1024.0 * float(self.pre_paid_memory_price)
                    renew_money += Decimal(memory_fee)
                if ps.disk_pay_method == "prepaid":
                    disk_fee = ps.disk / 1024.0 * float(self.pre_paid_disk_price)
                    renew_money += Decimal(disk_fee)
                extend_time = id_extendTime_map.get(ps.service_id)
                service_renew_money = Decimal(renew_money * 24 * int(extend_time) * 30)

                bill = ServiceFeeBill(tenant_id=self.tenant.tenant_id,
                                      service_id=ps.service_id,
                                      prepaid_money=service_renew_money,
                                      pay_status="payed",
                                      cost_type="renew",
                                      node_memory=ps.min_memory,
                                      node_num=ps.min_node,
                                      disk=ps.disk,
                                      buy_period=int(extend_time) * 24 * 30,
                                      create_time=create_time,
                                      pay_time=create_time)
                bills.append(bill)
                total_money += service_renew_money
            total_money = Decimal(str(round(total_money, 2)))
            # 如果钱不够
            if total_money > self.tenant.balance:
                result["ok"] = False
                result["status"] = "not_enough"
                result['msg'] = "账户余额不足以批量续费"
                return result
            sid = transaction.savepoint()
            ServiceFeeBill.objects.bulk_create(bills)
            for ps in renew_attach_infos:
                extend_time = int(id_extendTime_map.get(ps.service_id))
                ps.buy_end_time = ps.buy_end_time + datetime.timedelta(
                    days=extend_time * 30)
                ps.save()
            self.tenant.balance -= total_money
            self.tenant.save()
            transaction.savepoint_commit(sid)
            result["ok"] = True
            result["status"] = "success"
            result["msg"] = "续费成功"
            return result
        except Exception as e:
            if sid:
                transaction.savepoint_rollback(sid)
            raise e

    def batch_memory_renew(self, data, type):
        """
        内存未包月的应用
        """
        service_id_list = [elem["service_id"] for elem in data]
        renew_attach_infos = ServiceAttachInfo.objects.filter(service_id__in=service_id_list)
        renew_attach_infos = list(renew_attach_infos)
        now = datetime.datetime.now()
        result = {}
        create_time = now.strftime("%Y-%m-%d %H:%M:%S")
        sid = None
        try:
            if type == "prepaid_disk":
                # 如果磁盘已包月
                # id_memory_map = {elem["service_id"]: int(elem["memory"]) for elem in data}
                total_money = Decimal(0)
                bills = []
                for info in renew_attach_infos:
                    left_hours = int((info.buy_end_time - now).total_seconds() / 3600)
                    memory = info.min_memory * info.min_node
                    need_money = float(self.pre_paid_memory_price * Decimal(int(memory))) / 1024.0 * left_hours

                    bill = ServiceFeeBill(tenant_id=self.tenant.tenant_id,
                                          service_id=info.service_id,
                                          prepaid_money=need_money,
                                          pay_status="payed",
                                          cost_type="renew",
                                          node_memory=info.min_memory,
                                          node_num=info.min_node,
                                          disk=info.disk,
                                          buy_period=left_hours,
                                          create_time=create_time,
                                          pay_time=create_time)
                    bills.append(bill)
                    total_money += Decimal(need_money)
                total_money = Decimal(str(round(total_money, 2)))
                # 如果钱不够
                if total_money > self.tenant.balance:
                    result["ok"] = False
                    result["status"] = "not_enough"
                    result['msg'] = "账户余额不足以批量续费"
                    return result
                sid = transaction.savepoint()
                ServiceFeeBill.objects.bulk_create(bills)

                for ps in renew_attach_infos:
                    ps.memory_pay_method = "prepaid"
                    ps.save()
                self.tenant.balance -= total_money
                self.tenant.save()
                transaction.savepoint_commit(sid)
                result["ok"] = True
                result["status"] = "success"
                result["msg"] = "续费成功"
                return result
            elif type == 'postpaid_disk':
                # 如果磁盘未包月
                # id_memory_map = {elem["service_id"]: int(elem["memory"]) for elem in data}
                id_extendTime_map = {elem["service_id"]: int(elem["month_num"]) for elem in data}
                total_money = Decimal(0)
                bills = []
                for info in renew_attach_infos:
                    # memory = id_memory_map.get(info.service_id)
                    memory = info.min_memory * info.min_node
                    month = int(id_extendTime_map.get(info.service_id))
                    need_money = self.pre_paid_memory_price * Decimal(memory / 1024.0 * 24 * 30 * month)
                    bill = ServiceFeeBill(tenant_id=self.tenant.tenant_id,
                                          service_id=info.service_id,
                                          prepaid_money=need_money,
                                          pay_status="payed",
                                          cost_type="renew",
                                          node_memory=info.min_memory,
                                          node_num=info.min_node,
                                          disk=info.disk,
                                          buy_period=int(24 * 30 * month),
                                          create_time=create_time,
                                          pay_time=create_time)
                    bills.append(bill)
                    total_money += need_money
                total_money = Decimal(str(round(total_money, 2)))
                # 如果钱不够
                if total_money > self.tenant.balance:
                    result["ok"] = False
                    result["status"] = "not_enough"
                    result['msg'] = "账户余额不足以批量续费"
                    return result
                sid = transaction.savepoint()
                ServiceFeeBill.objects.bulk_create(bills)
                for ps in renew_attach_infos:
                    month = int(id_extendTime_map.get(ps.service_id))
                    ps.memory_pay_method = "prepaid"
                    ps.buy_start_time = now
                    ps.buy_end_time = ps.buy_start_time + datetime.timedelta(
                        days=month * 30)
                    ps.save()

                self.tenant.balance -= total_money
                self.tenant.save()
                transaction.savepoint_commit(sid)
                result["ok"] = True
                result["status"] = "success"
                result["msg"] = "续费成功"
                return result
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            raise e

    def batch_disk_renew(self, data, type):
        """
        磁盘未包月应用批量磁盘包月
        """
        service_id_list = [elem["service_id"] for elem in data]
        renew_attach_infos = ServiceAttachInfo.objects.filter(service_id__in=service_id_list)
        renew_attach_infos = list(renew_attach_infos)
        now = datetime.datetime.now()
        result = {}
        create_time = now.strftime("%Y-%m-%d %H:%M:%S")
        sid = None
        try:
            if type == "prepaid_memory":
                # 如果内存已包月
                id_disk_map = {elem["service_id"]: int(elem["disk"]) for elem in data}
                total_money = Decimal(0)
                bills = []
                for info in renew_attach_infos:
                    left_hours = int((info.buy_end_time - now).total_seconds() / 3600)
                    disk = id_disk_map.get(info.service_id)
                    need_money = self.pre_paid_disk_price * Decimal(int(disk)) * left_hours
                    bill = ServiceFeeBill(tenant_id=self.tenant.tenant_id,
                                          service_id=info.service_id,
                                          prepaid_money=need_money,
                                          pay_status="payed",
                                          cost_type="renew",
                                          node_memory=info.min_memory,
                                          node_num=info.min_node,
                                          disk=disk,
                                          buy_period=left_hours,
                                          create_time=create_time,
                                          pay_time=create_time)
                    bills.append(bill)
                    total_money += need_money
                total_money = Decimal(str(round(total_money, 2)))

                # 如果钱不够
                if total_money > self.tenant.balance:
                    result["ok"] = False
                    result["status"] = "not_enough"
                    result['msg'] = "账户余额不足以批量续费"
                    return result
                sid = transaction.savepoint()
                ServiceFeeBill.objects.bulk_create(bills)

                for ps in renew_attach_infos:
                    ps.disk_pay_method = "prepaid"
                    ps.save()
                self.tenant.balance -= total_money
                self.tenant.save()
                transaction.savepoint_commit(sid)
                result["ok"] = True
                result["status"] = "success"
                result["msg"] = "续费成功"
                return result
            elif type == "postpaid_memory":
                # 如果内存未包月
                id_disk_map = {elem["service_id"]: int(elem["disk"]) for elem in data}
                id_extendTime_map = {elem["service_id"]: int(elem["month_num"]) for elem in data}
                logger.debug("  id_disk_map {}".format(id_disk_map))
                total_money = Decimal(0)
                bills = []
                for info in renew_attach_infos:
                    disk = id_disk_map.get(info.service_id)
                    month = id_extendTime_map.get(info.service_id)
                    need_money = self.pre_paid_disk_price * Decimal(disk * 24 * 30 * month)
                    bill = ServiceFeeBill(tenant_id=self.tenant.tenant_id,
                                          service_id=info.service_id,
                                          prepaid_money=need_money,
                                          pay_status="payed",
                                          cost_type="renew",
                                          node_memory=info.min_memory,
                                          node_num=info.min_node,
                                          disk=disk * 1024,
                                          buy_period=int(24 * 30 * month),
                                          create_time=create_time,
                                          pay_time=create_time)
                    bills.append(bill)
                    total_money += need_money
                total_money = Decimal(str(round(total_money, 2)))

                # 如果钱不够
                if total_money > self.tenant.balance:
                    result["ok"] = False
                    result["status"] = "not_enough"
                    result['msg'] = "账户余额不足以批量续费"
                    return result

                sid = transaction.savepoint()
                ServiceFeeBill.objects.bulk_create(bills)
                for ps in renew_attach_infos:
                    month = int(id_extendTime_map.get(ps.service_id))
                    ps.disk_pay_method = "prepaid"
                    ps.disk = int(id_disk_map.get(ps.service_id)) * 1024
                    ps.buy_start_time = now
                    ps.buy_end_time = ps.buy_start_time + datetime.timedelta(
                        days=month * 30)
                    ps.save()
                self.tenant.balance -= total_money
                self.tenant.save()
                transaction.savepoint_commit(sid)
                result["ok"] = True
                result["status"] = "success"
                result["msg"] = "续费成功"
                return result
        except Exception as e:
            logger.exception(e)
            if sid:
                transaction.savepoint_rollback(sid)
            raise e

    def generate_result(self, code, msg, msg_show, bean={}, list=[], *args, **kwargs):
        result = {}
        data = {}
        result["code"] = code
        result["msg"] = msg
        result["msg_show"] = msg_show
        data["bean"] = bean
        data["list"] = list
        data.update(kwargs)
        result["data"] = data
        return result

    def generate_error_result(self):
        return self.generate_result("9999", "system error", "系统异常")
