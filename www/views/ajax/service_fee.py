# -*- coding: utf8 -*-

import logging

from django.http import JsonResponse

from share.manager.region_provier import RegionProviderManager
from www.decorator import perm_required
from www.models.main import ServiceAttachInfo
from www.monitorservice.monitorhook import MonitorHook
from www.service_http import RegionServiceApi
from www.views import AuthedView

logger = logging.getLogger('default')

regionClient = RegionServiceApi()
monitorhook = MonitorHook()
rpmManager = RegionProviderManager()


class PayMethodView(AuthedView):
    """付费方式修改"""

    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", None)
        result = {}
        try:
            if action == 'memory_change':
                # 修改内存计费方式
                memory_pay_method = request.POST.get("memory_pay_method","")
                if memory_pay_method.strip() == "" or memory_pay_method.strip() == "":
                    return JsonResponse({'ok': False, 'info': "参数错误"})

                current_memory_method = request.POST.get("current_memory_method", "")
                new_memory_method = request.POST.get("new_memory_method", "")
                if current_memory_method.strip() == "" or new_memory_method.strip() == "":
                    return JsonResponse({'ok': False, 'info': "参数错误"})
                if current_memory_method == new_memory_method:
                    result['ok'] = True
                    result['info'] = '更改成功'
                else:
                    if new_memory_method == 'prepaid':
                        # 如果为预付费方式,选择预付费的时长 ????
                        pass
                    else:
                        pass
                    # 修改内存计费方式
                    ServiceAttachInfo.objects.filter(tenant_id=self.tenant.tenant_id,
                                                     service_id=self.service.service_id).update(
                        memory_pay_method=new_memory_method)

            elif action == 'disk_change':
                # 修改磁盘计费方式
                current_disk_method = request.POST.get("current_disk_method", "")
                new_disk_method = request.POST.get("new_disk_method", "")
                if current_disk_method.strip() == "" or new_disk_method.strip() == "":
                    return JsonResponse({'ok': False, 'info': "参数错误"})
                if current_disk_method == new_disk_method:
                    result['ok'] = True
                    result['info'] = '更改成功'
                else:
                    if new_disk_method == 'prepaid':
                        # 如果为预付费方式,选择预付费的时长 ????
                        pass
                    else:
                        pass
            else:
                result['ok'] = False
                result['info'] = "参数错误"
        except Exception as e:
            logger.exception(e)
        return JsonResponse(result)


class ExtendServiceView(AuthedView):
    """扩容修改"""

    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        node_num = request.POST.get("node_num", 1)
        memory = request.POST.get("memory", 128)
        try:

            original_memory = self.service.min_memory * self.service.min_node
            current_memory = int(memory) * int(node_num)
            service_attach_info = ServiceAttachInfo.objects.get(tenant_id=self.tenant.tenant_id,
                                                                service_id=self.service.service_id)
            if service_attach_info.memory_pay_method == "prepaid":
                # 预付费的用户只能扩容
                if original_memory >= current_memory:
                    return JsonResponse({"ok": False, "info": "预付费不支持缩容操作"})
                else:
                    regionBo = rpmManager.get_work_region_by_name(self.response_region)
                    need_pay_money = (current_memory - original_memory) * regionBo.memory_package_price

            self.service.min_node = node_num
            self.service.min_memory = memory

            # 1.计算扩容后的内存的差价,如果有差价,提示用户补全差价
            # 2.判断租户余额是否够用
        except Exception as e:
            logger.exception(e)


class PrePaidPostponeView(AuthedView):
    """预付费方式延期操作"""

    @perm_required("manage_service")
    def post(self, request, *args, **kwargs):
        # 将现有的end_time 加上新续费的月份,新加的期限需要判断balance是否够用

        pass
