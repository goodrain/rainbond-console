# -*- coding: utf-8 -*-

from django.http import JsonResponse


class UserCookieMiddleware(object):
    # 校验用户COOKIE信息的中间件
    def process_request(self, request):
        user = request.COOKIES.get('username')
        company = request.COOKIES.get('company')
        if not user:
            return JsonResponse({'msg': 'user does not exist', 'code': 400}, status=400)
        if not company:
            return JsonResponse({'msg': 'user information is imperfect', 'code': 405}, status=405)
        return JsonResponse({'msg': 'user information is complete', 'code': 200}, status=200)
