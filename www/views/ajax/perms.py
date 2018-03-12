# -*- coding: utf8 -*-
import logging

from django.conf import settings
from django.http import JsonResponse
from django.template.loader import render_to_string

from www.decorator import perm_required
from www.models import Users, TenantServiceInfo, PermRelService, PermRelTenant, service_identity, \
    tenant_identity, \
    TenantEnterprise
from www.services.sso import SSO_BASE_URL
from www.tenantservice.baseservice import CodeRepositoriesService
from www.utils.crypt import AuthCode
from www.utils.mail import send_invite_mail_withHtml

from www.models import Users, Tenants, TenantServiceInfo, PermRelService, PermRelTenant, service_identity, tenant_identity, \
    TenantEnterprise
from www.utils.giturlparse import parse as git_url_parse
from www.utils.mail import send_invite_mail_withHtml
from www.views import AuthedView

logger = logging.getLogger('default')

codeRepositoriesService = CodeRepositoriesService()

gitlab_identity_map = {
    'admin': 'master', 'developer': 'developer',
}


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
        pass

    def user_exists_in_gitlab(self, user, member_list):
        for member in member_list:
            if user.git_user_id == member['id']:
                return member

        return False

    def do_gitlab_perm_works(self, user, identity):
        if self.service.git_url is None:
            return

        project_id = self.service.git_project_id
        if project_id > 0:
            parsed_git_url = git_url_parse(self.service.git_url)
            if parsed_git_url.host != 'code.goodrain.com':
                return
            try:
                current_members = codeRepositoriesService.listProjectMembers(project_id)
                is_member = self.user_exists_in_gitlab(user, current_members)

                if identity in ('admin', 'developer'):
                    gitlab_identity = gitlab_identity_map.get(identity)
                    if is_member:
                        logger.info("perm.gitlab",
                                    "modify user {0} identity for project {1} with address {2}".format(user.nick_name,
                                                                                                       project_id,
                                                                                                       self.service.git_url))
                        codeRepositoriesService.editMemberIdentity(project_id, user.git_user_id, gitlab_identity)
                    else:
                        logger.info("perm.gitlab",
                                    "add user {0} into project {1} with address {2}".format(user.nick_name, project_id,
                                                                                            self.service.git_url))
                        codeRepositoriesService.addProjectMember(project_id, user.git_user_id, gitlab_identity)
                elif identity == 'remove':
                    if is_member:
                        logger.info("perm.gitlab",
                                    "remove user {0} perms from project {1} with address {2}".format(user.nick_name,
                                                                                                     project_id,
                                                                                                     self.service.git_url))
                        codeRepositoriesService.deleteProjectMember(project_id, user.git_user_id)
                else:
                    if is_member:
                        logger.info("perm.gitlab",
                                    "remove user {0} perms from project {1} with address {2}".format(user.nick_name,
                                                                                                     project_id,
                                                                                                     self.service.git_url))
                        codeRepositoriesService.deleteProjectMember(project_id, user.git_user_id)
            except Exception, e:
                logger.exception('perm.gitlab', e)

    @perm_required('perm_setting')
    def post(self, request, *args, **kwargs):
        nick_name = request.POST.get('user')
        identity = request.POST.get('identity')
        user = Users.objects.get(nick_name=nick_name)
        if self.user.pk == user.user_id:
            desc = u"不能调整自己的权限"
            result = {"ok": True, "user": nick_name, "desc": desc}
            return JsonResponse(result, status=200)
        self.do_gitlab_perm_works(user, identity)
        if identity == 'remove':
            PermRelService.objects.filter(user_id=user.user_id, service_id=self.service.pk).delete()
            desc = u"权限已收回"
        else:
            service_perm = PermRelService.objects.get(user_id=user.user_id, service_id=self.service.pk)
            service_perm.identity = identity
            service_perm.save()
            my_alias = get_identity_name('service', identity)
            desc = u"调整用户{0}的身份为{1}".format(nick_name, my_alias)

        result = {"ok": True, "user": nick_name, "desc": desc}
        return JsonResponse(result, status=200)


class TenantIdentity(AuthedView):

    def init_request(self, *args, **kwargs):
        pass

    def user_exists_in_gitlab(self, user, member_list):
        for member in member_list:
            if user.git_user_id == member['id']:
                return member

        return False

    def do_gitlab_perm_works(self, user, identity):
        gitlab_services = TenantServiceInfo.objects.only('git_project_id', 'git_url').filter(
            tenant_id=self.tenant.tenant_id, git_project_id__gt=0)

        added_pids = []
        for s in gitlab_services:
            project_id = s.git_project_id
            if s.git_url is None:
                break

            if project_id in added_pids:
                break

            parsed_git_url = git_url_parse(s.git_url)
            if parsed_git_url.host != 'code.goodrain.com':
                return

            try:
                current_members = codeRepositoriesService.listProjectMembers(project_id)
                is_member = self.user_exists_in_gitlab(user, current_members)

                if identity in ('admin', 'developer'):
                    gitlab_identity = gitlab_identity_map.get(identity)
                    if is_member:
                        logger.info("perm.gitlab",
                                    "modify user {0} identity for project {1} with address {2}".format(user.nick_name,
                                                                                                       project_id,
                                                                                                       s.git_url))
                        codeRepositoriesService.editMemberIdentity(project_id, user.git_user_id, gitlab_identity)
                    else:
                        logger.info("perm.gitlab",
                                    "add user {0} into project {1} with address {2}".format(user.nick_name, project_id,
                                                                                            s.git_url))
                        codeRepositoriesService.addProjectMember(project_id, user.git_user_id, gitlab_identity)
                elif identity == 'remove':
                    if is_member:
                        logger.info("perm.gitlab",
                                    "remove user {0} perms from project {1} with address {2}".format(user.nick_name,
                                                                                                     project_id,
                                                                                                     s.git_url))
                        codeRepositoriesService.deleteProjectMember(project_id, user.git_user_id)
                else:
                    if is_member:
                        logger.info("perm.gitlab",
                                    "remove user {0} perms from project {1} with address {2}".format(user.nick_name,
                                                                                                     project_id,
                                                                                                     s.git_url))
                        codeRepositoriesService.deleteProjectMember(project_id, user.git_user_id)
                added_pids.append(project_id)
            except Exception, e:
                logger.exception("perm.gitlab", e)
                continue

    @perm_required('tenant.perm_setting')
    def post(self, request, *args, **kwargs):
        nick_name = request.POST.get('user')
        identity = request.POST.get('identity')
        user = Users.objects.get(nick_name=nick_name)
        user_id = user.pk
        if self.user.pk == user_id:
            desc = u"不能调整自己的权限"
            result = {"ok": True, "user": nick_name, "desc": desc}
            return JsonResponse(result, status=200)
        self.do_gitlab_perm_works(user, identity)
        if identity == 'remove':
            PermRelTenant.objects.filter(user_id=user.user_id, tenant_id=self.tenant.pk).delete()
            desc = u"权限已收回"
        else:
            tenant_perm = PermRelTenant.objects.get(user_id=user_id, tenant_id=self.tenant.pk)
            tenant_perm.identity = identity
            tenant_perm.save()
            my_alias = get_identity_name('tenant', identity)
            desc = u"调整用户{0}的团队身份为{1}".format(nick_name, my_alias)
        result = {"ok": True, "user": nick_name, "desc": desc}
        return JsonResponse(result, status=200)


class InviteServiceUser(AuthedView):

    def init_request(self, *args, **kwargs):
        pass

    def invite_content(self, email, tenant_name, service_alias, identity, eid):
        if settings.MODULES.get('SSO_LOGIN'):
            domain = SSO_BASE_URL
            mail_body = AuthCode.encode(
                ','.join(['invite_service', email, tenant_name, service_alias, identity, eid]), 'goodrain'
            )
            link_url = '{0}/api/invite?key={1}'.format(domain, mail_body)
        else:
            domain = self.request.META.get('HTTP_HOST')
            mail_body = AuthCode.encode(','.join([email, tenant_name, service_alias, identity, eid]), 'goodrain')
            link_url = 'http://{0}/invite?key={1}'.format(domain, mail_body)

        content = render_to_string('mail_invite.html', {'link_url': link_url, 'inviter': tenant_name})
        return content

    @perm_required('perm_setting')
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        identity = request.POST.get('identity')

        result = {"ok": True, "email": email, "identity": identity, "desc": None}

        try:
            user = Users.objects.get(email=email)
            try:
                PermRelService.objects.get(user_id=user.pk, service_id=self.service.pk)
                result['desc'] = u"{0}已经有应用权限了".format(user.nick_name)
            except PermRelService.DoesNotExist:
                PermRelService.objects.create(user_id=user.pk, service_id=self.service.pk, identity=identity)
                try:
                    PermRelTenant.objects.get(user_id=user.pk, tenant_id=self.tenant.pk)
                except PermRelTenant.DoesNotExist:
                    PermRelTenant.objects.create(enterprise_id=self.tenant.enterprise_id, user_id=user.pk, tenant_id=self.tenant.pk, identity='access')
                result['desc'] = u"已向{0}授权".format(user.nick_name)
                result['show'] = True

                # add gitlab project member
                if self.service.git_url is not None:
                    parsed_git_url = git_url_parse(self.service.git_url)
                    if parsed_git_url.host == 'code.goodrain.com':

                        git_project_id = self.service.git_project_id
                        if git_project_id > 0 and user.git_user_id > 0:
                            if identity in ("developer", "admin"):
                                gitlab_identity = gitlab_identity_map.get(identity)
                                codeRepositoriesService.addProjectMember(git_project_id, user.git_user_id,
                                                                         gitlab_identity)
                                logger.info("perm.gitlab",
                                            "add user {0} into project {1} with address {2}".format(user.nick_name,
                                                                                                    git_project_id,
                                                                                                    self.service.git_url))

        except Users.DoesNotExist:
            try:
                send_invite_mail_withHtml(email, self.invite_content(
                    email, self.tenant.tenant_name, self.service.service_alias, identity, self.tenant.enterprise_id))
                result['desc'] = u'已向{0}发送邀请邮件'.format(email)
            except Exception, e:
                logger.exception("error", e)

        return JsonResponse(result, status=200)


class InviteTenantUser(AuthedView):

    def init_request(self, *args, **kwargs):
        pass

    def invite_content(self, email, tenant_name, identity, eid):
        if settings.MODULES.get('SSO_LOGIN'):
            domain = SSO_BASE_URL
            mail_body = AuthCode.encode(','.join(['invite_tenant', email, tenant_name, identity, eid]), 'goodrain')
            link_url = '{0}/api/invite?key={1}'.format(domain, mail_body)
        else:
            domain = self.request.META.get('HTTP_HOST')
            mail_body = AuthCode.encode(','.join([email, tenant_name, identity, eid]), 'goodrain')
            link_url = 'http://{0}/invite?key={1}'.format(domain, mail_body)
        content = render_to_string('mail_invite.html', {'link_url': link_url, 'inviter': tenant_name})
        return content

    def add_member_to_gitlab(self, user, identity):
        gitlab_services = TenantServiceInfo.objects.only('git_project_id', 'git_url').filter(
            tenant_id=self.tenant.tenant_id, git_project_id__gt=0)

        if identity in ('admin', 'developer'):
            gitlab_identity = gitlab_identity_map.get(identity)
            try:
                added_pids = []
                for s in gitlab_services:
                    if s.git_url is None:
                        break

                    project_id = s.git_project_id
                    if project_id in added_pids:
                        break
                    parsed_git_url = git_url_parse(s.git_url)
                    if parsed_git_url.host == 'code.goodrain.com':
                        logger.info("perm.gitlab",
                                    "add user {0} into project {1} with address {2}".format(user.nick_name, project_id,
                                                                                            s.git_url))
                        codeRepositoriesService.addProjectMember(project_id, user.git_user_id, gitlab_identity)
                        added_pids.append(project_id)
            except Exception, e:
                logger.exception("perm.gitlab", e)

    @perm_required('tenant.perm_setting')
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        identity = request.POST.get('identity')

        result = {"ok": True, "email": email, "identity": identity, "desc": None}

        try:
            user = Users.objects.get(email=email)
            try:
                PermRelTenant.objects.get(user_id=user.user_id, tenant_id=self.tenant.pk)
                result['desc'] = u"{0}已经是项目成员了".format(user.nick_name)
            except PermRelTenant.DoesNotExist:
                enterprise = TenantEnterprise.objects.get(enterprise_id=self.tenant.enterprise_id)
                PermRelTenant.objects.create(enterprise_id=enterprise.ID, user_id=user.user_id,
                                             tenant_id=self.tenant.pk, identity=identity)
                result['desc'] = u"已向{0}授权".format(user.nick_name)
                result['show'] = True
                self.add_member_to_gitlab(user, identity)
        except Users.DoesNotExist:
            # user = Users.objects.create(email=email, password='unset', is_active=False)
            # PermRelTenant.objects.create(user_id=user.user_id, tenant_id=self.tenant_pk, identity=identity)
            try:
                send_invite_mail_withHtml(email, self.invite_content(
                    email, self.tenant.tenant_name, identity, self.tenant.enterprise_id))
                result['desc'] = u'已向{0}发送邀请邮件'.format(email)
            except Exception, e:
                logger.exception("error", e)

        return JsonResponse(result, status=200)
