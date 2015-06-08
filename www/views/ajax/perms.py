# -*- coding: utf8 -*-
from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required
from www.utils.crypt import AuthCode
from www.utils.mail import send_invite_mail

from www.models import Users, Tenants, TenantServiceInfo, PermRelService, PermRelTenant, service_identity, tenant_identity
from www.gitlab_http import GitlabApi

import logging
logger = logging.getLogger('default')

gitClient = GitlabApi()


def get_identity_name(name, identity):
    if name == 'tenant':
        for item in tenant_identity:
            if item[1] == identity:
                return item[0]

    if name == 'service':
        for item in service_identity:
            if item[1] == identity:
                return item[0]

    return "Unknown"


class ServiceIdentity(AuthedView):
    def init_request(self, *args, **kwargs):
        tenant_id = Tenants.objects.get(tenant_name=self.tenantName).tenant_id
        self.service_pk = TenantServiceInfo.objects.get(tenant_id=tenant_id, service_alias=self.serviceAlias).pk

    @perm_required('perm_setting')
    def post(self, request, *args, **kwargs):
        nick_name = request.POST.get('user')
        identity = request.POST.get('identity')
        user_id = Users.objects.get(nick_name=nick_name).pk
        service_perm = PermRelService.objects.get(user_id=user_id, service_id=self.service_pk)
        service_perm.identity = identity
        service_perm.save()

        my_alias = get_identity_name('service', identity)
        desc = u"调整用户{0}的身份为{1}".format(nick_name, my_alias)
        result = {"ok": True, "user": nick_name, "desc": desc}
        return JsonResponse(result, status=200)


class TenantIdentity(AuthedView):
    def init_request(self, *args, **kwargs):
        self.tenant_pk = Tenants.objects.get(tenant_name=self.tenantName).pk

    @perm_required('tenant.perm_setting')
    def post(self, request, *args, **kwargs):
        nick_name = request.POST.get('user')
        identity = request.POST.get('identity')
        user_id = Users.objects.get(nick_name=nick_name).pk
        tenant_perm = PermRelTenant.objects.get(user_id=user_id, tenant_id=self.tenant_pk)
        tenant_perm.identity = identity
        tenant_perm.save()

        my_alias = get_identity_name('tenant', identity)
        desc = u"调整用户{0}的团队身份为{1}".format(nick_name, my_alias)
        result = {"ok": True, "user": nick_name, "desc": desc}
        return JsonResponse(result, status=200)


class InviteServiceUser(AuthedView):
    def init_request(self, *args, **kwargs):
        tenant = Tenants.objects.get(tenant_name=self.tenantName)
        self.service = TenantServiceInfo.objects.get(tenant_id=tenant.tenant_id, service_alias=self.serviceAlias)
        self.service_pk = self.service.pk
        self.tenant_pk = tenant.pk

    def invite_content(self, email, tenant_name, service_alias, identity):
        domain = self.request.META.get('HTTP_HOST')
        mail_body = AuthCode.encode(','.join([email, tenant_name, service_alias, identity]), 'goodrain')
        return 'http://{0}/invite?key={1}'.format(domain, mail_body)

    @perm_required('perm_setting')
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        identity = request.POST.get('identity')

        result = {"ok": True, "email": email, "identity": identity, "desc": None}

        try:
            user = Users.objects.get(email=email)
            try:
                PermRelService.objects.get(user_id=user.pk, service_id=self.service_pk)
                result['desc'] = u"{0}已经有应用权限了".format(user.nick_name)
            except PermRelService.DoesNotExist:
                PermRelService.objects.create(user_id=user.pk, service_id=self.service_pk, identity=identity)
                try:
                    PermRelTenant.objects.get(user_id=user.pk, tenant_id=self.tenant_pk)
                except PermRelTenant.DoesNotExist:
                    PermRelTenant.objects.create(user_id=user.pk, tenant_id=self.tenant_pk, identity='access')
                result['desc'] = u"已向{0}授权".format(user.nick_name)

                # add gitlab project member
                git_project_id = self.service.git_project_id
                if git_project_id > 0 and user.git_user_id > 0:
                    gitClient.addProjectMember(git_project_id, user.git_user_id)

        except Users.DoesNotExist:
            send_invite_mail(email, self.invite_content(email, self.tenantName, self.serviceAlias, identity))
            result['desc'] = u'已向{0}发送邀请邮件'.format(email)

        return JsonResponse(result, status=200)


class InviteTenantUser(AuthedView):
    def init_request(self, *args, **kwargs):
        self.tenant_pk = Tenants.objects.get(tenant_name=self.tenantName).pk
        pass

    def invite_content(self, email, tenant_name, identity):
        domain = self.request.META.get('HTTP_HOST')
        mail_body = AuthCode.encode(','.join([email, tenant_name, identity]), 'goodrain')
        return 'http://{0}/invite?key={1}'.format(domain, mail_body)

    @perm_required('tenant.perm_setting')
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        identity = request.POST.get('identity')

        result = {"ok": True, "email": email, "identity": identity, "desc": None}

        try:
            user = Users.objects.get(email=email)
            try:
                PermRelTenant.objects.get(user_id=user.user_id, tenant_id=self.tenant_pk)
                result['desc'] = u"{0}已经是项目成员了".format(user.nick_name)
            except PermRelTenant.DoesNotExist:
                PermRelTenant.objects.create(user_id=user.user_id, tenant_id=self.tenant_pk, identity=identity)
                result['desc'] = u"已向{0}授权".format(user.nick_name)
        except Users.DoesNotExist:
            #user = Users.objects.create(email=email, password='unset', is_active=False)
            #PermRelTenant.objects.create(user_id=user.user_id, tenant_id=self.tenant_pk, identity=identity)
            send_invite_mail(email, self.invite_content(email, self.tenantName))
            result['desc'] = u'已向{0}发送邀请邮件'.format(email)

        return JsonResponse(result, status=200)
