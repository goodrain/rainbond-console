import logging
logger = logging.getLogger('default')

from django.conf import settings
from www.models import TenantConsume, TenantPaymentNotify, TenantServiceStatics, TenantServiceInfo
from influxdb.influxdb08 import InfluxDBClient
import datetime

class InflexdbService(object):
    
    def serviceContainerMemoryStatics(self, timeStamp):
        try:
            inflexdb_info = settings.INFLEXDB
            client = InfluxDBClient(inflexdb_info.get('host'), inflexdb_info.get('port'), inflexdb_info.get('user'), inflexdb_info.get('password'), 'cadvisor')
            result = client.query("select mean(memory_usage) as memory_usage,mean(memory_working_set) as memory_working_set,DERIVATIVE(cpu_cumulative_usage) as cpu_cumulative_usage from stats group by serviceId,podId,tenantId  where time > " + timeStamp + "  and memory_usage>0 and serviceId <> '' and serviceId <>'POD'")
            for json in result:
                columns = json["columns"]
                points = json["points"]
                for number, point in enumerate(points):
                    d = {}
                    for index, column in enumerate(columns):
                        d[column] = point[index]
                    if len(d) > 0: 
                        count = TenantServiceStatics.objects.filter(service_id=d['serviceId'], time_stamp=timeStamp).count()
                        if count < 1:
                            tenantServiceInfo = TenantServiceInfo.objects.get(service_id=d['serviceId'])
                            tss = TenantServiceStatics()
                            tss.tenant_id = d['tenantId']
                            tss.service_id = d['serviceId']
                            tss.time_stamp = timeStamp
                            tss.node_num = tenantServiceInfo.min_node
                            tss.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            tss = TenantServiceStatics.objects.get(service_id=d['serviceId'], time_stamp=timeStamp)
                        tss.pod_id = d['podId']
                        tss.container_memory = int(round(d['memory_usage']) / 1024)                    
                        tss.container_memory_working = int(round(d['memory_working_set']) / 1024)
                        tss.container_cpu = int(round(d['cpu_cumulative_usage']) / 1000)
                        tss.save()
        except Exception as e:
            logger.exception(e)
    
    def serviceContainerDiskStatics(self, timeStamp):
        try:
            inflexdb_info = settings.INFLEXDB
            client = InfluxDBClient(inflexdb_info.get('host'), inflexdb_info.get('port'), inflexdb_info.get('user'), inflexdb_info.get('password'), 'cadvisor')
            result = client.query("select mean(fs_usage) as fs_usage from stats group by serviceId,podId,tenantId where time > " + timeStamp + " and fs_usage>=0 and serviceId <> '' and serviceId <>'POD'")
            for json in result:
                columns = json["columns"]
                points = json["points"]
                for number, point in enumerate(points):
                    d = {}
                    for index, column in enumerate(columns):
                        d[column] = point[index]
                    if len(d) > 0:
                        count = TenantServiceStatics.objects.filter(service_id=d['serviceId'], time_stamp=timeStamp).count()
                        if count < 1:
                            tenantServiceInfo = TenantServiceInfo.objects.get(service_id=d['serviceId'])
                            tss = TenantServiceStatics()
                            tss.tenant_id = d['tenantId']
                            tss.service_id = d['serviceId']
                            tss.time_stamp = timeStamp
                            tss.node_num = tenantServiceInfo.min_node
                            tss.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            tss = TenantServiceStatics.objects.get(service_id=d['serviceId'], time_stamp=timeStamp)
                        tss.container_disk = int(round(d['fs_usage']) / 1024)
                        tss.save()
        except Exception as e:
            logger.exception(e)
    
    
    def servicePodMemoryStatics(self, timeStamp):
        try:
            inflexdb_info = settings.INFLEXDB
            client = InfluxDBClient(inflexdb_info.get('host'), inflexdb_info.get('port'), inflexdb_info.get('user'), inflexdb_info.get('password'), 'cadvisor')
            result = client.query("select mean(memory_usage) as memory_usage,mean(memory_working_set) as memory_working_set,DERIVATIVE(cpu_cumulative_usage) as cpu_cumulative_usage from stats group by podId where time > " + timeStamp + " and memory_usage>0 and serviceId ='POD'")
            for json in result:
                columns = json["columns"]
                points = json["points"]
                for number, point in enumerate(points):
                    d = {}
                    for index, column in enumerate(columns):
                        d[column] = point[index]
                    if len(d) > 0:
                        count = TenantServiceStatics.objects.filter(pod_id=d['podId'], time_stamp=timeStamp).count()
                        if count > 0:
                            tss = TenantServiceStatics.objects.get(pod_id=d['podId'])                        
                            tss.pod_memory = int(round(d['memory_usage']) / 1024)                       
                            tss.pod_memory_working = int(round(d['memory_working_set']) / 1024)
                            tss.pod_cpu = int(round(d['cpu_cumulative_usage']) / 1000)
                            tss.save()
        except Exception as e:
            logger.exception(e)
            
            
            
    def serviceDiskStatics(self, timeStamp):
        try:
            inflexdb_info = settings.INFLEXDB
            client = InfluxDBClient(inflexdb_info.get('host'), inflexdb_info.get('port'), inflexdb_info.get('user'), inflexdb_info.get('password'), 'statistic')
            result = client.query("select mean(disk) as disk,mean(bytesout) as bytesout, mean(bytesin) as bytesin  from service_stat group by service_id,tenant_id  where time > " + timeStamp)
            for json in result:
                columns = json["columns"]
                points = json["points"]
                for number, point in enumerate(points):
                    d = {}
                    for index, column in enumerate(columns):
                        d[column] = point[index]
                    if len(d) > 0:              
                        count = TenantServiceStatics.objects.filter(service_id=d['service_id'], time_stamp=timeStamp).count()
                        if count < 1:
                            tenantServiceInfo = TenantServiceInfo.objects.get(service_id=d['service_id'])
                            tss = TenantServiceStatics()
                            tss.tenant_id = d['tenant_id']
                            tss.service_id = d['service_id']
                            tss.time_stamp = timeStamp
                            tss.node_num = tenantServiceInfo.min_node
                            tss.time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            tss = TenantServiceStatics.objects.get(service_id=d['service_id'], time_stamp=timeStamp)
                        tss.storage_disk = int(round(d['disk']) / 1024)
                        tss.net_in = int(round(d['bytesin']))
                        tss.net_out = int(round(d['bytesout']))
                        tss.save()
        except Exception as e:
            logger.exception(e)
