# -*- coding: utf8 -*-
from django.http import JsonResponse
import json
from www.views import AuthedView
from www.models import ThirdAppInfo
from www.third_app.cdn.upai.client import YouPaiApi
import logging

logger = logging.getLogger('default')
upai_client = YouPaiApi()


class UpdateAppView(AuthedView):
    def __init__(self, request, *args, **kwargs):
        
        self.app_id = kwargs.get('app_id', None)
        self.app_info = ThirdAppInfo.objects.get(bucket_name=self.app_id)
        AuthedView.__init__(self, request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """
        修改应用名
        """
        result = {}
        try:
            name = request.POST.get("name", "")
            if name == "":
                result["status"] = "failure"
                result["message"] = "应用名不能为空"
            else:
                self.app_info.name = name
                self.app_info.save()
                result["status"] = "success"
                result["message"] = "修改成功"
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = "修改失败"
        return JsonResponse(result)


class AppDomainView(AuthedView):
    def __init__(self, request, *args, **kwargs):
        
        self.app_id = kwargs.get('app_id', None)
        self.app_info = ThirdAppInfo.objects.get(bucket_name=self.app_id)
        AuthedView.__init__(self, request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            domain = request.POST.get("domain", "")
            if domain == "":
                result["status"] = "failure"
                result["message"] = "域名不能为空"
            else:
                body = {}
                body["domain"] = domain
                body["bucket_name"] = self.app_id
                res, rebody = upai_client.addDomain(json.dumps(body))
                if res.status == 200:
                    result["status"] = "success"
                    result["message"] = "添加成功"
                else:
                    if type(rebody) is str:
                        rebody = json.loads(rebody)
                    result["status"] = "failure"
                    result["message"] = rebody.message
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = "添加失败"
        return JsonResponse(result)


class AppDomainDeleteView(AuthedView):
    def __init__(self, request, *args, **kwargs):
        self.app_id = kwargs.get('app_id', None)
        self.app_info = ThirdAppInfo.objects.get(bucket_name=self.app_id)
        AuthedView.__init__(self, request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            domain = request.POST.get("domain", "")
            if domain == "":
                result["status"] = "failure"
                result["message"] = "域名不能为空"
            else:
                res, rebody = upai_client.deleteDomain(domain=domain, bucket=self.app_id)
                if res.status == 200:
                    result["status"] = "success"
                    result["message"] = "删除成功"
                else:
                    if type(rebody) is str:
                        rebody = json.loads(rebody)
                    result["status"] = "failure"
                    result["message"] = rebody.message
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = "删除失败"
        return JsonResponse(result)


class AppOperatorView(AuthedView):
    def __init__(self, request, *args, **kwargs):
        self.app_id = kwargs.get('app_id', None)
        self.app_info = ThirdAppInfo.objects.get(bucket_name=self.app_id)
        AuthedView.__init__(self, request, *args, **kwargs)
    
    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            pass
        
        try:
            import unicodedata
            unicodedata.numeric(s)
            return True
        except (TypeError, ValueError):
            pass
        
        return False
    
    def post(self, request, *args, **kwargs):
        """
        添加操作员并授权。
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        result = {}
        try:
            operator_name = request.POST.get("operator_name", "")
            password = request.POST.get("password", "")
            realname = request.POST.get("realname", "")
            if operator_name == "":
                result["status"] = "failure"
                result["message"] = "用户名不能为空"
                return JsonResponse(result)
            if len(password) < 9 or self.is_number(password):
                result["status"] = "failure"
                result["message"] = "密码8位以上且不能都为数字"
                return JsonResponse(result)
            if realname == "":
                result["status"] = "failure"
                result["message"] = "姓名不能为空"
                return JsonResponse(result)
            else:
                body = {}
                body["operator_name"] = operator_name
                body["password"] = password
                body["realname"] = realname
                res, rebody = upai_client.addOperator(json.dumps(body))
                if res.status == 201:
                    authBody = {}
                    authBody["bucket_name"] = self.app_id
                    authBody["operator_name"] = operator_name
                    res, rebody = upai_client.addOperatorAuth(json.dumps(authBody))
                    if res.status == 201:
                        result["status"] = "success"
                        result["message"] = "添加成功"
                    else:
                        if type(rebody) is str:
                            rebody = json.loads(rebody)
                        result["status"] = "failure"
                        result["message"] = rebody.message
                else:
                    if type(rebody) is str:
                        rebody = json.loads(rebody)
                    result["status"] = "failure"
                    result["message"] = rebody.message
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = "添加失败"
        return JsonResponse(result)


class AppOperatorDeleteView(AuthedView):
    def __init__(self, request, *args, **kwargs):
        self.app_id = kwargs.get('app_id', None)
        self.app_info = ThirdAppInfo.objects.get(bucket_name=self.app_id)
        AuthedView.__init__(self, request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        result = {}
        try:
            operator_name = request.POST.get("operator_name", "")
            if operator_name == "":
                result["status"] = "failure"
                result["message"] = "操作员用户名不能为空"
            res, rebody = upai_client.deleteOperatorAuth(self.app_id, operator_name)
            if res.status == 200:
                upai_client.deleteOperator(operator_name)
                result["status"] = "success"
                result["message"] = "删除成功"
            else:
                if type(rebody) is str:
                    rebody = json.loads(rebody)
                result["status"] = "failure"
                result["message"] = rebody.message
        except Exception, e:
            logger.exception(e)
            result["status"] = "failure"
            result["message"] = "删除失败"
        return JsonResponse(result)
