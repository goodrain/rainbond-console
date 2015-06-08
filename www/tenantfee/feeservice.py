# -*- coding: utf8 -*-
import datetime
import time
import json

from www.db import BaseConnection
from www.models import TenantServiceStatics, TenantConsume, TenantRecharge

import logging
logger = logging.getLogger('default')

class TenantFeeService(object):
    
    def dateToTimeStamp(self, date):
        timeArray = time.strptime(a, "%Y-%m-%d %H:%M:%S")
        timeStamp = int(time.mktime(timeArray))
        return timeStamp
    
    def byteToKilo(self, byte):
        return int(round(byte / 1024))
    
    def staticsFee(self):  
        # data = {}
        try:
            dsn = BaseConnection()
            tenant_sql = '''select tenant_id from tenant_info;'''
            tenantIds = dsn.query(tenant_sql)
            for tenant_id in tenantIds:
                query_lastTime_sql = "select time from tenant_consume where tenant_id='" + tenant_id + "' order by id desc limit 1;"
                lastTime = dsn.query(query_lastTime_sql)
                curTimeStamp = 0
                if len(lastTime) > 0:
                    logger.debug(lastTime)
                    last_time = lastTime["time"].strftime('%Y-%m-%d %H:%M:%S')
                    curTimeStamp = self.dateToTimeStamp(last_time)                              
                query_sql = "select AVG(container_cpu+pod_cpu) as cpu ,AVG(container_memory+pod_memory) as memory,AVG(container_disk+storage_disk) as disk ,AVG(net_in) as net_in,AVG(net_out) as net_out, AVG(node_num) as node_num,service_id from tenant_service_statics where tenant_id='" + tenant_id + "' time_stamp>=" + str(curTimeStamp) + " group by service_id;"
                data = dsn.query(query_sql)
                if len(data) > 0:
                    time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    for statics in data:
                        tenantConsume = TenantConsume()
                        tenantConsume.tenant_id = tenant_id
                        tenantConsume.service_id = statics["service_id"]
                        tenantConsume.node_num = int(statics["node_num"])
                        tenantConsume.cpu = int(statics["cpu"])
                        tenantConsume.memory = self.byteToKilo(int(statics["memory"]))
                        tenantConsume.disk = self.byteToKilo(int(statics["disk"]))
                        net_in = self.byteToKilo(int(statics["net_in"]))
                        net_out = self.byteToKilo(int(statics["net_out"]))
                        if net_in > net_out:
                            tenantConsume.net = net_in
                        else:
                            tenantConsume.net = net_out                    
                        self.calculateFee(tenantConsume)
                        tenantConsume.time = time
                        num = TenantRecharge.objects.filter(tenant_id=tenant_id).count()
                        if num == 1:
                            tenantRecharge = TenantRecharge.objects.get(tenant_id=tenant_id)
                            tenantRecharge.money = tenantRecharge.money - tenantConsume.money
                            tenantRecharge.save()
                        tenantConsume.save()
        except Exception as e:
            logger.exception(e) 
        # return data
        
    def calculateFee(self, tenantConsume):
        try:
            rule = '{"disk":0.1,"net":10,"unit_money":1}'
            ruleJson = json.loads(rule)
            total_memory = tenantConsume.memory + (tenantConsume.disk + tenantConsume.node_num * 200 * 1024) * float(ruleJson['disk']) + tenantConsume.net * float(ruleJson['disk'])
            money = float(ruleJson['unit_money']) * total_memory / 1024
            tenantConsume.total_memory = total_memory
            tenantConsume.money = money 
            tenantConsume.fee_rule = rule    
        except Exception as e:
            logger.exception(e) 
            

