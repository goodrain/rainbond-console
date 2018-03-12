# -*- coding: utf8 -*-
import time
import datetime
import json

from rest_framework.response import Response
from api.views.base import APIView
from www.apiclient.regionapi import RegionInvokeApi
from www.models import TenantServiceStatics, Tenants, TenantRegionInfo, TenantServiceInfo, TenantServiceEnv, \
    ServiceEvent, AppService, TenantServiceInfoDelete, TenantServiceAuth, ServiceDomain, TenantServiceRelation, \
    TenantServiceEnvVar, TenantServiceMountRelation, TenantServicesPort, TenantServiceVolume, ServiceGroupRelation, \
    ServiceAttachInfo, ServiceCreateStep, ServiceProbe, ServicePaymentNotify
from www.monitorservice.monitorhook import MonitorHook
from www.db import BaseConnection
from django.conf import settings

import logging

from www.utils.crypt import make_uuid
from www.utils.mnssdk.mns.account import Account
from www.utils.mnssdk.mns.topic import DirectSMSInfo, TopicMessage
from www.utils.mnssdk.mns.mns_exception import MNSExceptionBase

logger = logging.getLogger('default')

monitorhook = MonitorHook()
region_api = RegionInvokeApi()

class TenantServiceStaticsView(APIView):
    '''
    计费基础数据统计
    '''
    allowed_methods = ('POST',)
    
    def post(self, request, format=None):
        """
        统计租户服务
        ---
        parameters:
            - name: data
              description: 数据列表
              required: true
              type: string
              paramType: body
        """
        datas = request.data
        beginTime = time.time()
        logger.debug("statistic.perf", "total data: {}".format(len(datas)))
        for data in datas:
            try:
                tenant_id = data["tenant_id"]
                service_id = data["service_id"]
                node_num = data.get("node_num", 0)
                node_memory = data.get("node_memory", 0)
                time_stamp = data["time_stamp"]
                storage_disk = data.get("storage_disk", 0)
                net_in = data.get("net_in", 0)
                net_out = data.get("net_out", 0)
                flow = data.get("flow", 0)
                region = data["region"]
                runing_status = data["status"]
                start_time = time.time()
                if runing_status and int(runing_status) == 3:
                    logger.debug('statistic.perf', data)
                    tenant_id = 'system'
                    service_id = region
                cnt = TenantServiceStatics.objects.filter(service_id=service_id, time_stamp=time_stamp).count()
                if cnt < 1:
                    ts = TenantServiceStatics(tenant_id=tenant_id, service_id=service_id, node_num=node_num,
                                              node_memory=node_memory,
                                              time_stamp=time_stamp, storage_disk=storage_disk, net_in=net_in,
                                              net_out=net_out, status=runing_status, flow=flow, region=region)
                    ts.save()
                end_time = time.time()
                logger.debug('statistic.perf', "sql execute time: {0}".format(end_time - start_time))
            except Exception as e:
                logger.debug('statistic.perf', data)
                logger.exception(e)
            endTime = time.time()
            logger.debug('statistic.perf', "total use time: {0}".format(endTime - beginTime))
        return Response({"ok": True}, status=200)


class TenantHibernateView(APIView):
    '''
    租户休眠
    '''
    allowed_methods = ('put', 'post')
    
    def put(self, request, format=None):
        """
        休眠容器(pause,systemPause,unpause)
        ---
        parameters:
            - name: tenant_id
              description: 租户ID
              required: true
              type: string
              paramType: form
            - name: action
              description: 动作
              required: true
              type: string
              paramType: form
        """
        tenant_id = request.data.get('tenant_id', "")
        action = request.data.get('action', "")
        region = request.data.get('region', None)
        if region is None:
            return Response({"ok": False, "info": "need region field"}, status=400)
        
        logger.debug("tenant.pause", request.data)
        try:
            return Response({"ok": True}, status=200)
        except TenantRegionInfo.DoesNotExist:
            logger.error("tenant.pause", "object not find, region: {0}, tenant_id: {1}".format(region, tenant_id))
            return Response({"ok": False, "info": "region not found"}, status=400)
        except Exception, e:
            logger.exception("tenant.pause", e)
            return Response({"ok": False, "info": e.__str__()}, status=500)
    
    def post(self, request, format=None):
        """
        休眠容器(pause,unpause)
        ---
        parameters:
            - name: tenant_name
              description: 租户名
              required: true
              type: string
              paramType: form
            - name: action
              description: 动作
              required: true
              type: string
              paramType: form
        """
        tenant_name = request.data.get('tenant_name', "")
        action = request.data.get('action', "")
        region = request.data.get('region', None)
        if region is None:
            return Response({"ok": False, "info": "need region field"}, status=400)
        
        logger.debug("tenant.pause", request.data)
        try:
            pass
        except Exception as e:
            logger.exception(e)
        return Response({"ok": True}, status=200)


class AllTenantView(APIView):
    '''
    租户信息
    '''
    allowed_methods = ('post',)
    
    def post(self, request, format=None):
        """
        获取所有租户信息
        ---
        parameters:
            - name: service_status
              description: 服务状态
              required: true
              type: string
              paramType: form
            - name: pay_type
              description: 租户类型
              required: true
              type: string
              paramType: form
            - name: region
              description: 区域中心
              required: true
              type: string
              paramType: form
            - name: day
              description: 相差天数
              required: false
              type: string
              paramType: form

        """
        service_status = request.data.get('service_status', "1")
        pay_type = request.data.get('pay_type', "free")
        region = request.data.get('region', "")
        query_day = request.data.get('day', "0")
        diff_day = int(query_day)
        data = {}
        try:
            if region != "":
                dsn = BaseConnection()
                query_sql = ""
                if diff_day != 0:
                    end_time = datetime.datetime.now() + datetime.timedelta(days=-1 * diff_day)
                    str_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
                    query_sql = '''select ti.tenant_id,ti.tenant_name from tenant_info ti left join tenant_region tr on ti.tenant_id=tr.tenant_id where tr.is_init=1 and tr.service_status="{service_status}" and ti.pay_type="{pay_type}" and tr.region_name="{region}" and tr.update_time <= "{end_time}"
                        '''.format(service_status=service_status, pay_type=pay_type, region=region, end_time=str_time)
                else:
                    query_sql = '''select ti.tenant_id,ti.tenant_name from tenant_info ti left join tenant_region tr on ti.tenant_id=tr.tenant_id where tr.is_init=1 and tr.service_status="{service_status}" and ti.pay_type="{pay_type}" and tr.region_name="{region}"
                        '''.format(service_status=service_status, pay_type=pay_type, region=region)
                if query_sql != "":
                    sqlobjs = dsn.query(query_sql)
                    if sqlobjs is not None and len(sqlobjs) > 0:
                        for sqlobj in sqlobjs:
                            data[sqlobj['tenant_id']] = sqlobj['tenant_name']
        except Exception as e:
            logger.exception(e)
        return Response(data, status=200)


class TenantView(APIView):
    '''
    租户信息
    '''
    allowed_methods = ('post',)
    
    def post(self, request, format=None):
        """
        获取某个租户信息(tenant_id或者tenant_name)
        ---
        parameters:
            - name: tenant_id
              description: 租户ID
              required: false
              type: string
              paramType: form
            - name: tenant_name
              description: 租户名
              required: false
              type: string
              paramType: form

        """
        data = {}
        try:
            print request.data
            tenant_id = request.data.get('tenant_id', "")
            tenant_name = request.data.get('tenant_name', "")
            tenant = None
            if tenant_id != "":
                tenant = Tenants.objects.get(tenant_id=tenant_id)
            if tenant is None:
                if tenant_name != "":
                    tenant = Tenants.objects.get(tenant_name=tenant_name)
            if tenant is not None:
                data["tenant_id"] = tenant.tenant_id
                data["tenant_name"] = tenant.tenant_name
                tenantRegionList = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id, is_active=True)
                regions = []
                for tenantRegion in tenantRegionList:
                    region_data = {}
                    region_data["region_name"] = tenantRegion.region_name
                    region_data["service_status"] = tenantRegion.service_status
                    regions.append(region_data)
                data["regions"] = regions
                data["pay_type"] = tenant.pay_type
        except Exception as e:
            logger.exception(e)
        return Response(data, status=200)


class GitCheckCodeView(APIView):
    def get_language_env(self,language):
        """
        根据指定的语言找到对应的ENV
        :param language: 语言
        :return:
        """
        checkJson={}
        if language == "docker":
            checkJson["language"] = 'docker'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Python":
            checkJson["language"] = 'Python'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Ruby":
            checkJson["language"] = 'Ruby'
            checkJson["runtimes"] = "2.0.0"
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "PHP":
            checkJson["language"] = 'PHP'
            checkJson["runtimes"] = "5.6.11"
            checkJson["procfile"] = "apache"
            dependencies = {"ext-bcmath": "*", "ext-redis": "*", "ext-apcu": "*", "ext-calendar": "*",
                            "ext-blackfire": "*", "ext-gettext": "*", "ext-pcntl": "*", "ext-xmlrpc": "*",
                            "ext-mongo": "*", "ext-imagick": "*", "ext-xsl": "*", "ext-gd": "*", "ext-exif": "*",
                            "ext-pdo_sqlite": "*", "ext-intl": "*", "ext-oauth": "*", "ext-soap": "*",
                            "ext-memcached": "*", "ext-shmop": "*", "ext-mbstring": "*", "ext-newrelic": "*",
                            "ext-ftp": "*", "ext-sqlite3": "*"}
            checkJson["dependencies"] = dependencies
        elif language == "Java-maven":
            checkJson["language"] = 'Java-maven'
            checkJson["runtimes"] = "1.8"
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Java-war":
            checkJson["language"] = 'Java-war'
            checkJson["runtimes"] = "1.8"
            checkJson["procfile"] = "tomcat7"
            checkJson["dependencies"] = {}
        elif language == "Java-jar":
            checkJson["language"] = 'Java-jar'
            checkJson["runtimes"] = "1.8"
            checkJson["procfile"] = "tomcat7"
            checkJson["dependencies"] = {}
        elif language == "Node.js":
            checkJson["language"] = 'Node.js'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "static":
            checkJson["language"] = 'static'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = "apache"
            checkJson["dependencies"] = {}
        elif language == "Clojure":
            checkJson["language"] = 'Clojure'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Go":
            checkJson["language"] = 'Go'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Gradle":
            checkJson["language"] = 'Gradle'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Play":
            checkJson["language"] = 'Play'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Grails":
            checkJson["language"] = 'Grails'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        elif language == "Scala":
            checkJson["language"] = 'Scala'
            checkJson["runtimes"] = ""
            checkJson["procfile"] = ""
            checkJson["dependencies"] = {}
        return checkJson

    def create_service_event(self, tenant, service):

        try:
            import datetime
            event = ServiceEvent(event_id=make_uuid(), service_id=service.service_id,
                                 tenant_id=tenant.tenant_id, type="upgrade",
                                 deploy_version=service.deploy_version,
                                 old_deploy_version=service.deploy_version,
                                 user_name="system", start_time=datetime.datetime.now())
            event.save()
            self.event = event
            return event.event_id
        except Exception as e:
            self.event = None
            raise e


    def post(self, request, format=None):
        """
    代码检测
        ---
        parameters:
            - name: service_id
              description: 租户ID
              required: false
              type: string
              paramType: form
            - name: condition
              description: 检测条件
              required: false
              type: string
              paramType: form

    """
        data = {}
        try:
            service_id = request.data.get('service_id', "")
            dependency = request.data.get("condition", "")
            check_type = request.data.get('check_type', 'first_check')
            logger.debug(service_id + "=" + dependency)
            if service_id != "" and dependency != "":
                if check_type == 'first_check':
                    dps = json.loads(dependency)
                    language = dps["language"]
                    if language is not None and language != "" and language != "no":
                        try:
                            tse = TenantServiceEnv.objects.get(service_id=service_id)
                            tse.language = language
                            tse.check_dependency = dependency
                            tse.save()
                        except Exception:
                            tse = TenantServiceEnv(service_id=service_id, language=language, check_dependency=dependency)
                            tse.save()
                        service = TenantServiceInfo.objects.get(service_id=service_id)
                        if language != "false":
                            if language.find("Java") > -1 and service.min_memory < 512:
                                service.min_memory = 512
                            service.language = language
                            service.save()
                elif check_type == 'git_change':
                    code_version = request.data.get("code_version", "master")
                    git_project_id = request.data.get("git_project_id", "0")
                    code_from = request.data.get("code_from", "gitlab_manual")
                    url_repos = request.data.get("url_repos")
                    dps = json.loads(dependency)
                    language = dps["language"]

                    if language is not None and language != "" and language != "no" and language != "false":
                        tenantService = TenantServiceInfo.objects.get(service_id=service_id)
                        try:
                            if tenantService.language != language:
                                tenantService.language = language
                                tenantService.code_version = code_version
                                tenantService.git_project_id = git_project_id
                                tenantService.code_from = code_from
                                tenantService.git_url = url_repos
                                tenantService.save()
                                tse = TenantServiceEnv.objects.get(service_id=service_id)
                                tse.language = language
                                tse.check_dependency = dependency
                                checkJson = self.get_language_env(language)
                                tse.user_dependency = json.dumps(checkJson)
                                tse.save()
                                if language.find("Java") > -1 and tenantService.min_memory < 512:
                                    tenantService.min_memory = 512
                                    data = {}
                                    data["language"] = "java"
                                    tenant = Tenants.objects.get(tenant_id=tenantService.tenant_id)
                                    event_id = self.create_service_event(tenant,tenantService)
                                    data["event_id"] = event_id
                                    data["enterprise_id"] = tenant.enterprise_id
                                    region_api.change_memory(tenantService.service_region, tenant.tenant_name, tenantService.service_alias,
                                                             data)

                                tenantService.language = language
                                tenantService.save()


                            else:
                                tenantService.code_version = code_version
                                tenantService.git_project_id = git_project_id
                                tenantService.code_from = code_from
                                tenantService.git_url = url_repos
                                tenantService.save()
                            
                        except TenantServiceEnv.DoesNotExist:
                            tse = TenantServiceEnv(service_id=service_id, language=language, check_dependency=dependency)
                            tse.save()
            data["status"] = "success"
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return Response(data, status=200)


class UpdateServiceExpireTime(APIView):
    allowed_methods = ('put',)
    
    def put(self, request, format=None):
        """

        更新租户服务过期时间和最大内存
        ---
        parameters:
            - name: service_id
              description: 服务ID
              required: true
              type: string
              paramType: form
            - name: expired_days
              description: 剩余过期天数
              required: false
              type: int
              paramType: form

        """
        data = {}
        status = 200
        try:
            service_id = request.data.get("service_id", "")
            expired_days = request.data.get("expired_days", 7)
            service = TenantServiceInfo.objects.get(service_id=service_id)
            if expired_days.strip():
                if service.expired_time:
                    service.expired_time = service.expired_time + datetime.timedelta(days=int(expired_days))
                else:
                    service.expired_time = datetime.datetime.now() + datetime.timedelta(days=int(expired_days))
            service.save()
            data["status"] = "success"
        except TenantServiceInfo.DoesNotExist:
            logger.error("service_id :{0} is not found".format(service_id))
            data["status"] = "failure"
            status = 404
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
            status = 500
        return Response(data, status=status)


class ServiceEventUpdate(APIView):
    allowed_methods = ('put',)
    
    def put(self, request, format=None):
        """

        更新服务操作状态
        ---
        parameters:
            - name: event_id
              description: 操作ID
              required: true
              type: string
              paramType: form
            - name: status
              description: 操作状态
              required: false
              type: string
              paramType: form
            - name: message
              description: 操作说明
              required: false
              type: string
              paramType: form
        """
        data = {}
        status = 200
        try:
            event_id = request.data.get("event_id", "")
            if not event_id:
                data["status"] = "failure"
                status = 404
                return Response(data, status=status)
            event_status = request.data.get("status", "failure")
            message = request.data.get("message", "")
            event = ServiceEvent.objects.get(event_id=event_id)
            if event:
                event.status = event_status
                event.final_status = "complete"
                event.message = message
                event.end_time = datetime.datetime.now()
                if event.status == "failure" and event.type == "callback":
                    event.deploy_version = event.old_deploy_version
                event.save()
                data["status"] = "success"
        
        except ServiceEvent.DoesNotExist:
            data["status"] = "failure"
            status = 404
        except Exception as e:
            logger.exception(e)
            logger.error("api", u"更新操作结果发生错误." + e.message)
            data["status"] = "failure"
            status = 500
        return Response(data, status=status)


class ServiceEventCodeVersionUpdate(APIView):
    allowed_methods = ('put',)
    
    def put(self, request, format=None):
        """

        更新服务操作状态
        ---
        parameters:
            - name: event_id
              description: 操作ID
              required: true
              type: string
              paramType: form
            - name: code_version
              description: 代码版本
              required: false
              type: string
              paramType: form
        """
        data = {}
        status = 200
        try:
            event_id = request.data.get("event_id", "")
            if not event_id:
                data["status"] = "failure"
                status = 404
                return Response(data, status=status)
            code_version = request.data.get("code_version", "")
            event = ServiceEvent.objects.get(event_id=event_id)
            if event:
                event.code_version = code_version
                event.save()
                data["status"] = "success"
        except ServiceEvent.DoesNotExist:
            data["status"] = "failure"
            status = 404
        except Exception as e:
            logger.exception(e)
            logger.error("api", u"更新操作结果发生错误." + e.message)
            data["status"] = "failure"
            status = 500
        return Response(data, status=status)


class ServiceStopView(APIView):
    allowed_methods = ('post',)

    def post(self, request, format=None):
        """

        停止服务
        ---
        parameters:
            - name: service_id
              description: 操作ID
              required: true
              type: string
              paramType: form
            - name: region
              description: 数据中心
              required: true
              type: string
              paramType: form
            - name: action
              description: 操作
              required: false
              type: string
              paramType: form
        """
        data = {}
        try:
            service_id = request.data.get("service_id")
            service_region = request.data.get("region")
            action = request.data.get("action", "own_money")
            service = TenantServiceInfo.objects.get(service_region=service_region,service_id=service_id)
            tenant = Tenants.objects.get(tenant_id=service.tenant_id)
            body = region_api.check_service_status(service_region, tenant.tenant_name, service.service_alias,tenant.enterprise_id)
            bean = body["bean"]

            status = bean["cur_status"]
            if status not in ('closed', 'undeploy', 'deploying'):
                event_id = make_uuid()
                service = TenantServiceInfo.objects.get(service_id=service_id)
                event = ServiceEvent(event_id=event_id, service_id=service_id,
                                     tenant_id=service.tenant_id, type=action,
                                     deploy_version=service.deploy_version, old_deploy_version=service.deploy_version,
                                     user_name="system", start_time=datetime.datetime.now())
                event.save()
                body = {}
                body["operator"] = str("system")
                body["event_id"] = event_id
                body["enterprise_id"] = tenant.enterprise_id

                region_api.stop_service(service.service_region,
                                        tenant.tenant_name,
                                        service.service_alias,
                                        body)
            data["status"] = "success"
        except TenantServiceInfo.DoesNotExist as ex:
            logger.exception(ex)
            logger.error("service is not exist")
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return Response(data, status=200)


class SendMessageView(APIView):
    allowed_methods = ('post',)
    # 余额不足
    PREPAY_TEMPLATE_CODE = "SMS_70100593"
    # 应用过期提醒
    EXPIRED_TEMPLATE_CODE = "SMS_90260009"
    # 服务欠费通知
    OWNED_TEMPLATE_CODE = "SMS_90185012"

    def send_message(self, phone, service_cname, notify_type, days):

        account_id = settings.ALIYUN_MNS['ACCOUNTID']
        if account_id is None:
            return False, None
        access_id = settings.ALIYUN_MNS['ACCESSKEYID']
        access_key = settings.ALIYUN_MNS['ACCESSKEYSECRET']
        end_point = settings.ALIYUN_MNS['ENDPOINT']
        topic_name = settings.ALIYUN_MNS['TOPICNAME']
        sign_name = settings.ALIYUN_MNS['SIGNNAME']

        now = datetime.datetime.now()
        end_time = now + datetime.timedelta(days=int(days))
        end_time_str = end_time.strftime("%Y年%m月%d日 %H时")
        template_code = None
        # 阿里字符长度替换最长为15个字符
        params = {}
        if notify_type == "prepay":
            template_code = self.PREPAY_TEMPLATE_CODE
        elif notify_type == "charge":
            # 应用过期
            template_code = self.EXPIRED_TEMPLATE_CODE
            params = {"service_cname": service_cname, "days": str(days), "end_time": end_time_str}
        elif notify_type == "owed":
            # 应用欠费
            template_code = self.OWNED_TEMPLATE_CODE
            params = {"service_cname": service_cname, "days": str(days), "end_time": end_time_str}

        my_account = Account(end_point, access_id, access_key)
        my_topic = my_account.get_topic(topic_name)

        msg_body = str("[注册码]")
        direct_sms_attr = DirectSMSInfo(free_sign_name=sign_name, template_code=template_code, single=False)
        if params:
            direct_sms_attr.add_receiver(receiver=phone, params=params)
        else:
            direct_sms_attr.add_receiver(receiver=phone)

        msg = TopicMessage(msg_body, direct_sms=direct_sms_attr)
        try:
            # Step 6. 发布SMS消息
            re_msg = my_topic.publish_message(msg)
            logger.debug("Publish Message Succeed. MessageID:{0}".format(re_msg.message_id))
            return True, re_msg.message_id
        except MNSExceptionBase, e:
            if e.type == "TopicNotExist":
                logger.error('ali yun mns topic not exist, please create it!')
            logger.error("Publish Message Fail. Exception:%s" % e)
        return False, None

    def post(self, request, format=None):
        """

        发送短信服务
        ---
        parameters:
            - name: phone
              description: 手机号码
              required: true
              type: string
              paramType: form
            - name: service_cname
              description: 服务名
              required: true
              type: string
              paramType: form
            - name: notify_type
              description: 提示类型
              required: true
              type: string
              paramType: form
            - name: days
              description: 剩余天数
              required: false
              type: string
              paramType: form
        """
        data = {}
        try:
            phone = request.data.get("phone")
            service_cname = request.data.get("service_cname")
            if len(service_cname) > 15:

                if isinstance(service_cname, unicode):
                    service_cname = service_cname[0:7]+"..."+service_cname[-5:]
                else:
                    service_cname = service_cname.decode('utf8')[0:7] + "..."+service_cname.decode('utf8')[-5:]
            notify_type = request.data.get("notify_type")
            days = request.data.get("days", None)
            logger.debug("send message phone {0},service_cname {1}, notify_type {2},days {3}".format(phone, service_cname, notify_type, days))
            self.send_message(phone, service_cname, notify_type, days)
            data["status"] = "success"
        except Exception as e:
            logger.exception(e)
            data["status"] = "failure"
        return Response(data, status=200)


class DeleteServiceView(APIView):
    allowed_methods = ('delete',)

    def delete(self, request, format=None):
        """
        系统删除服务接口
        ---
        parameters:
            - name: tenant_id
              description: 租户id
              required: true
              type: string
              paramType: form
            - name: service_id
              description: 服务id
              required: true
              type: string
              paramType: form
            - name: use_name
              description: 删除人
              required: true
              type: string
              paramType: form

        """
        data = {}
        service_id = request.data.get("service_id")
        tenant_id = request.data.get("tenant_id")
        user_name = request.data.get("user_name", 'system')
        tenant = None
        service = None
        try:
            service = TenantServiceInfo.objects.get(service_id=service_id)
        except TenantServiceInfo.DoesNotExist:
            logger.error("api.services", "service_id不存在!")
            return Response(status=406, data={"success": False, "msg": u"服务不存在"})
        try:
            tenant = Tenants.objects.get(tenant_id=tenant_id)
        except Tenants.DoesNotExist:
            logger.error("api.services", "租户不存在!")
            return Response(status=408, data={"success": False, "msg": u"租户不存在"})

        if service.service_origin != "cloud":
            logger.debug("api.services", "now remove assistant service")
            status, success, msg = self.delete_service(tenant, service, user_name)

            return Response(status=status, data={"success": success, "msg": msg})
        return Response(status=200, data={"success": "success", "msg": "删除成功"})

    def delete_service(self, tenant, service, user_name):
        try:
            published = AppService.objects.filter(service_id=service.service_id).count()
            if published:
                logger.debug("api.services",
                             "services has related published!".format(tenant.tenant_name, service.service_cname))
                return 409, False, u"关联了已发布服务, 不可删除"
            # 删除服务
            # 备份删除数据
            data = service.toJSON()
            tenant_service_info_delete = TenantServiceInfoDelete(**data)
            tenant_service_info_delete.save()

            # 删除region服务
            try:
                region_api.delete_service(service.service_region,tenant.tenant_name,service.service_alias,tenant.enterprise_id)
            except region_api.CallApiError as e:
                if e.status != 404:
                    logger.exception("api.services", e)
                    return 412, False, u"删除失败"

            # 删除console服务
            TenantServiceInfo.objects.get(service_id=service.service_id).delete()
            # env/auth/domain/relationship/envVar delete
            TenantServiceEnv.objects.filter(service_id=service.service_id).delete()
            TenantServiceAuth.objects.filter(service_id=service.service_id).delete()
            ServiceDomain.objects.filter(service_id=service.service_id).delete()
            TenantServiceRelation.objects.filter(service_id=service.service_id).delete()
            TenantServiceEnvVar.objects.filter(service_id=service.service_id).delete()
            TenantServiceMountRelation.objects.filter(service_id=service.service_id).delete()
            TenantServicesPort.objects.filter(service_id=service.service_id).delete()
            TenantServiceVolume.objects.filter(service_id=service.service_id).delete()
            ServiceGroupRelation.objects.filter(service_id=service.service_id).delete()
            ServiceAttachInfo.objects.filter(service_id=service.service_id).delete()
            ServiceCreateStep.objects.filter(service_id=service.service_id).delete()

            events = ServiceEvent.objects.filter(service_id=service.service_id)

            ServiceEvent.objects.filter(service_id=service.service_id).delete()
            # 删除应用检测数据
            ServiceProbe.objects.filter(service_id=service.service_id).delete()
            # 删除应用提示消息
            ServicePaymentNotify.objects.filter(service_id=service.service_id).delete()

            monitorhook.serviceMonitor(user_name, service, 'app_delete', True)
            logger.debug("api.services", "delete service.result:success")
            return 200, True, u"删除成功"

        except Exception as e:
            logger.exception("api.services", e)
            logger.debug("api.services", "delete service.result:failure")
            return 412, False, u"删除失败"


class GetDeletedServiceView(APIView):
    allowed_methods = ('get',)

    def get(self, request, day_num, format=None):
        """
        获取已删除服务接口
        ---
        parameters:
            - name: day_num
              description: 日期(从今天起多少天以前)
              required: true
              type: string
              paramType: path

        """
        if not day_num:
            return Response(status=406, data={"success": False, "msg": u"没有指定天数"})
        try:
            day_num = int(day_num)
        except Exception as e:
            return Response(status=403, data={"success": False, "msg": u"参数不为整数"})
        try:
            days_before = datetime.datetime.now() + datetime.timedelta(days=-day_num)
            deleted_service_list = TenantServiceInfoDelete.objects.filter(delete_time__gte=days_before).values(
                "tenant_id", "service_id", "delete_time", "service_region").order_by("delete_time")
            return Response(status=200, data={"success": True, "msg": list(deleted_service_list)})
        except Exception as e:
            logger.exception(e)
            return Response(status=500, data={"success": False, "msg": u"系统异常"})
