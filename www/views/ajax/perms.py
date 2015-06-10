# -*- coding: utf8 -*-
from django.http import JsonResponse
from www.views import AuthedView
from www.decorator import perm_required
from www.utils.crypt import AuthCode
from www.utils.mail import send_invite_mail
from www.utils.mail import send_invite_mail_withHtml

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
        link_url = 'http://{0}/invite?key={1}'.format(domain, mail_body)    
        content = u"尊敬的用户您好，"
        content = content + "<br/>"
        content = content + u"非常感谢您申请试用 好雨云平台！ 请点击下面的链接完成注册:"
        content = content + "<br/>"
        content = content + u"注册链接: " + link_url
        content = content + "<br/>"
        content = content + u"我们的服务在一定的资源范围内永久免费！内测阶段也可以申请增加免费资源，增加的资源在产品正式版上线后也不会另收费用哦！另外参与内测并提交问题报告的用户，正式上线后还会有更多的福利。"
        content = content + "<br/>"
        content = content + u"我们的文档及博客正在建设中，以后会陆续发布一系列好雨云平台的使用教程和技巧，欢迎关注！"
        content = content + "<br/>"
        content = content + u"您在使用过程中遇到的任何问题，或者对平台有任何建议，都可以通过以下途径提交反馈。对于提出高质量的反馈的用户，还有精美礼品等待您！"
        content = content + "<br/>"
        content = content + "Email： ares@goodrain.com"
        content = content + "<br/>"
        content = content + u"微信公众号：goodrain-cloud "
        content = content + "<br/>"
        content = content + u"联系电话：13621236261"
        content = content + "<br/>"
        content = content + u"再次感谢您关注我们的产品！"
        content = content + "<br/>"
        content = content + u"好雨科技 (Goodrain Inc.) CEO 刘凡"
        return content

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
            send_invite_mail_withHtml(email, self.invite_content(email, self.tenantName, self.serviceAlias, identity))
            result['desc'] = u'已向{0}发送邀请邮件'.format(email)

        return JsonResponse(result, status=200)


class InviteTenantUser(AuthedView):
    def init_request(self, *args, **kwargs):
        self.tenant_pk = Tenants.objects.get(tenant_name=self.tenantName).pk
        pass


    def invite_content(self, email, tenant_name, identity):
        domain = self.request.META.get('HTTP_HOST')
        mail_body = AuthCode.encode(','.join([email, tenant_name, identity]), 'goodrain')
        link_url = 'http://{0}/invite?key={1}'.format(domain, mail_body)        
        content = u"尊敬的用户您好，"
        content = content + "<br/>"
        content = content + u"非常感谢您申请试用 好雨云平台！ 请点击下面的链接完成注册:"
        content = content + "<br/>"
        content = content + u"注册链接: " + link_url
        content = content + "<br/>"
        content = content + u"我们的服务在一定的资源范围内永久免费！内测阶段也可以申请增加免费资源，增加的资源在产品正式版上线后也不会另收费用哦！另外参与内测并提交问题报告的用户，正式上线后还会有更多的福利。"
        content = content + "<br/>"
        content = content + u"我们的文档及博客正在建设中，以后会陆续发布一系列好雨云平台的使用教程和技巧，欢迎关注！"
        content = content + "<br/>"
        content = content + u"您在使用过程中遇到的任何问题，或者对平台有任何建议，都可以通过以下途径提交反馈。对于提出高质量的反馈的用户，还有精美礼品等待您！"
        content = content + "<br/>"
        content = content + "Email： ares@goodrain.com"
        content = content + "<br/>"
        content = content + u"微信公众号：goodrain-cloud "
        content = content + "<br/>"
        content = content + u"联系电话：13621236261"
        content = content + "<br/>"
        content = content + u"再次感谢您关注我们的产品！"
        content = content + "<br/>"
        content = content + u"好雨科技 (Goodrain Inc.) CEO 刘凡"
        return content

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
            # user = Users.objects.create(email=email, password='unset', is_active=False)
            # PermRelTenant.objects.create(user_id=user.user_id, tenant_id=self.tenant_pk, identity=identity)
            send_invite_mail(email, self.invite_content(email, self.tenantName))
            result['desc'] = u'已向{0}发送邀请邮件'.format(email)

        return JsonResponse(result, status=200)
