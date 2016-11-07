# -*- coding: utf8 -*-

from django.template.response import TemplateResponse

from www.views import AuthedView, LeftSideBarMixin
from www.decorator import perm_required
from www.models import Users, PermRelTenant

import logging
logger = logging.getLogger('default')


class TeamInfo(LeftSideBarMixin, AuthedView):

    def get_context(self):
        context = super(TeamInfo, self).get_context()
        context.update({
            'perm_users': self.get_user_perms(),
            'tenantName': self.tenantName,
        })
        context["teamStatus"] = "active"
        return context

    def get_media(self):
        media = super(TeamInfo, self).get_media() + self.vendor(
            'www/css/goodrainstyle.css', 'www/js/jquery.cookie.js', 'www/js/service.js',
            'www/js/gr/basic.js', 'www/css/gr/basic.css', 'www/js/perms.js', 'www/js/common-scripts.js', 'www/js/jquery.dcjqaccordion.2.7.js', 'www/js/jquery.scrollTo.min.js'
        )
        return media

    def get_response(self):
        return TemplateResponse(self.request, 'www/team.html', self.get_context())

    def get_user_perms(self):
        perm_users = []
        perm_template = {
            'name': None,
            'adminCheck': False,
            'developerCheck': False, 'developerDisable': False,
            'viewerCheck': False, 'viewerDisable': False
        }

        identities = PermRelTenant.objects.filter(tenant_id=self.tenant.pk)

        user_id_list = [x.user_id for x in identities]
        user_list = Users.objects.filter(pk__in=user_id_list)
        user_map = {x.user_id: x for x in user_list}

        for i in identities:
            user_perm = perm_template.copy()
            user_info = user_map.get(i.user_id)
            if user_info is None:
                continue
            user_perm['name'] = user_info.nick_name
            if i.user_id == self.user.user_id:
                user_perm['selfuser'] = True

            if i.identity == 'admin':
                user_perm.update({
                    'adminCheck': True,
                    'developerCheck': True,
                    'developerDisable': True,
                    'viewerCheck': True,
                    'viewerDisable': True
                })
            elif i.identity == 'developer':
                user_perm.update({
                    'developerCheck': True,
                    'viewerCheck': True,
                    'viewerDisable': True
                })
            elif i.identity == 'viewer':
                user_perm.update({
                    'viewerCheck': True
                })

            perm_users.append(user_perm)

        return perm_users

    @perm_required('tenant_access')
    def get(self, request, *args, **kwargs):
        return self.get_response()
