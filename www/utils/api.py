# -*- coding: utf8 -*-
from django.http import JsonResponse
from rest_framework.response import Response


def AjaxErrResponseJson(message, messagecn, code):
    result = {}
    result["code"] = code
    result["msg"] = message
    result["msgcn"] = messagecn
    return JsonResponse(result, status=200)


def AjaxSuccessResponseJson(bean=None,
                            list_data=None,
                            pageNumber=0,
                            pageSize=0,
                            total=0):
    result = {}
    result["code"] = 200
    result["body"] = {}
    result["body"]["bean"] = bean
    result["body"]["list"] = list_data
    result["body"]["pageNumber"] = pageNumber
    result["body"]["pageSize"] = pageSize
    result["body"]["total"] = total
    return JsonResponse(result, status=200)


def APISuccessResponseJson(bean=None,
                           list_data=None,
                           pageNumber=0,
                           pageSize=0,
                           total=0):
    result = {}
    result["code"] = 200
    result["body"] = {}
    result["body"]["bean"] = bean
    result["body"]["list"] = list_data
    result["body"]["pageNumber"] = pageNumber
    result["body"]["pageSize"] = pageSize
    result["body"]["total"] = total
    return Response(result, status=200)


def APIErrResponseJson(message, messagecn, code):
    result = {}
    result["code"] = code
    result["msg"] = message
    result["msgcn"] = messagecn
    return Response(result, status=200)