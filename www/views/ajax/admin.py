# -*- coding:utf-8 -*-

import logging

from django.http import JsonResponse

from www.models.main import SuperAdminUser, Users, Tenants, TenantEnterprise, TenantRegionInfo, PermRelTenant, \
    TenantEnterpriseToken, TenantRegionResource
from www.views.base import BaseView

logger = logging.getLogger('default')


class UsersDetailView(BaseView):
    def get(self, request):
        """
        获取用户信息详情接口
        ---
        parameters:
            - name: name
              description: 用户名
              required: false
              type: string
              paramType: query
        """
        if not SuperAdminUser.objects.filter(email=request.user.email).exists():
            return JsonResponse({'ok': False, 'message': 'Permission Denied!'})

        nick_name = request.GET.get('nick_name')
        if not nick_name:
            return JsonResponse({'ok': False, 'message': 'Bad Request, nick_name not specified!'})

        data = {}
        try:
            user = Users.objects.get(nick_name=nick_name)
            data.update(user.to_dict())
        except Users.DoesNotExist as e:
            return JsonResponse({'ok': False, 'message': 'user {} does not existed!'.format(nick_name)})

        enterprise_data = dict()
        try:
            enter = TenantEnterprise.objects.get(enterprise_id=user.enterprise_id)
            enterprise_data.update(enter.to_dict())
        except TenantEnterprise.DoesNotExist as e:
            pass

        tenants = Tenants.objects.filter(creater=user.user_id)
        tenant_list_data = list()
        for tenant in tenants:
            tenant_data = dict()
            tenant_data.update(tenant.to_dict())

            tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id)
            tenant_data.update({
                'tenant_regions': [tenant_region.to_dict() for tenant_region in tenant_regions]
            })

            tenant_res = TenantRegionResource.objects.filter(tenant_id=tenant.tenant_id)
            tenant_data.update({
                'tenant_res': [res.to_dict() for res in tenant_res]
            })

            tenant_list_data.append(tenant_data)
        enterprise_data.update({'tenants': tenant_list_data})

        enter_tokens = [enter_token.to_dict() for enter_token in TenantEnterpriseToken.objects.filter(enterprise_id=enter.ID)]
        enterprise_data.update({'tokens': enter_tokens})

        data.update({'enterprise': enterprise_data})

        perms = PermRelTenant.objects.filter(user_id=user.user_id)
        data.update({
            'perms': [perm.to_dict() for perm in perms]
        })

        return JsonResponse({'ok': True, 'message': 'ok', 'data': data})


class TenantsDetailView(BaseView):
    def get(self, request):
        """
        获取租户信息详情接口
        ---
        parameters:
            - name: tenant_name
              description: 租户名
              required: false
              type: string
              paramType: query
        """
        if not SuperAdminUser.objects.filter(email=request.user.email).exists():
            return JsonResponse({'ok': False, 'message': 'Permission Denied!'})

        tenant_name = request.GET.get('tenant_name')
        if not tenant_name:
            return JsonResponse({'ok': False, 'message': 'Bad Request, tenant_name not specified!'})

        data = {}
        try:
            tenant = Tenants.objects.get(tenant_name=tenant_name)

            tenant_data = dict()
            tenant_data.update(tenant.to_dict())

            tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id)
            tenant_data.update({
                'tenant_regions': [tenant_region.to_dict() for tenant_region in tenant_regions]
            })

            perms = PermRelTenant.objects.filter(tenant_id=tenant.ID)
            tenant_data.update({
                'perms': [perm.to_dict() for perm in perms]
            })

            tenant_res = TenantRegionResource.objects.filter(tenant_id=tenant.tenant_id)
            tenant_data.update({
                'tenant_res': [res.to_dict() for res in tenant_res]
            })

            data.update(tenant_data)
        except Tenants.DoesNotExist as e:
            return JsonResponse({'ok': False, 'message': 'tenant {} does not existed!'.format(tenant_name)})

        try:
            user = Users.objects.get(user_id=tenant.creater)
            data.update({'creater': user.to_dict()})
        except Users.DoesNotExist as e:
            data.update({'creater': dict()})

        try:
            enter = TenantEnterprise.objects.get(enterprise_id=user.enterprise_id)
            data.update({'enterprise': enter.to_dict()})

            enter_tokens = [enter_token.to_dict() for enter_token in
                            TenantEnterpriseToken.objects.filter(enterprise_id=enter.ID)]
            data.get('enterprise').update({'tokens': enter_tokens})
        except TenantEnterprise.DoesNotExist as e:
            data.update({'enterprise': dict()})

        return JsonResponse({'ok': True, 'message': 'ok', 'data': data})


class EntersDetailView(BaseView):
    def get(self, request):
        """
        获取企业信息详情接口
        ---
        parameters:
            - name: nick_name
              description: 用户名
              required: false
              type: string
              paramType: query
        """
        if not SuperAdminUser.objects.filter(email=request.user.email).exists():
            return JsonResponse({'ok': False, 'message': 'Permission Denied!'})

        enter_name = request.GET.get('enter_name')
        if not enter_name:
            return JsonResponse({'ok': False, 'message': 'Bad Request, enter_name not specified!'})

        data = {}
        try:
            enter = TenantEnterprise.objects.get(enterprise_name=enter_name)
            data.update(enter.to_dict())

            enter_tokens = [enter_token.to_dict() for enter_token in
                            TenantEnterpriseToken.objects.filter(enterprise_id=enter.ID)]
            data.update({'tokens': enter_tokens})
        except TenantEnterprise.DoesNotExist as e:
            return JsonResponse({'ok': False, 'message': 'enter {} does not existed!'.format(enter_name)})

        try:
            users = Users.objects.filter(enterprise_id=enter.enterprise_id)
            data.update({'users': [user.to_dict() for user in users]})
        except Users.DoesNotExist as e:
            data.update({'users': []})

        tenants = Tenants.objects.filter(enterprise_id=enter.enterprise_id)
        tenant_list_data = list()
        for tenant in tenants:
            tenant_data = dict()
            tenant_data.update(tenant.to_dict())

            tenant_regions = TenantRegionInfo.objects.filter(tenant_id=tenant.tenant_id)
            tenant_data.update({
                'tenant_regions': [tenant_region.to_dict() for tenant_region in tenant_regions]
            })

            tenant_res = TenantRegionResource.objects.filter(tenant_id=tenant.tenant_id)
            tenant_data.update({
                'tenant_res': [res.to_dict() for res in tenant_res]
            })

            tenant_list_data.append(tenant_data)

        data.update({'tenants': tenant_list_data})

        perms = PermRelTenant.objects.filter(enterprise_id=enter.ID)
        data.update({
            'perms': [perm.to_dict() for perm in perms]
        })

        return JsonResponse({'ok': True, 'message': 'ok', 'data': data})