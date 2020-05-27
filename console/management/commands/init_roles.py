#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.core.management import BaseCommand
from django.db import transaction

from console.exception.main import ServiceHandleException
from console.services.perm_services import role_kind_services
from console.services.perm_services import user_kind_role_service
from console.repositories.team_repo import team_repo

from www.models.main import Tenants


class Command(BaseCommand):
    help = u'初始化所有团队的角色和团队成员的角色分配'

    def add_arguments(self, parser):
        parser.add_argument('--tenant_id',
                            default=None,
                            help=u"指定团队初始化权限")
        parser.add_argument('--enterprise_id',
                            default=None,
                            help=u"指定企业初始化权限")

    @transaction.atomic()
    def handle(self, *args, **options):
        tenant_id = options['tenant_id']
        enterprise_id = options['enterprise_id']
        if tenant_id and enterprise_id:
            teams = Tenants.objects.filter(tenant_id=tenant_id, enterprise_id=enterprise_id)
        elif tenant_id and not enterprise_id:
            teams = Tenants.objects.filter(tenant_id=tenant_id)
        elif not tenant_id and enterprise_id:
            teams = Tenants.objects.filter(enterprise_id=enterprise_id)
        else:
            teams = Tenants.objects.all()
        if not teams:
            print(u"未发现团队, 初始化结束")
            return
        for team in teams:
            role_kind_services.init_default_roles(kind="team", kind_id=team.tenant_id)
            users = team_repo.get_tenant_users_by_tenant_ID(team.ID)
            admin = role_kind_services.get_role_by_name(kind="team", kind_id=team.tenant_id, name=u"管理员")
            developer = role_kind_services.get_role_by_name(kind="team", kind_id=team.tenant_id, name=u"开发者")
            if not admin or not developer:
                raise ServiceHandleException(msg="init failed", msg_show=u"初始化失败")
            if users:
                for user in users:
                    if user.user_id == team.creater:
                        user_kind_role_service.update_user_roles(
                            kind="team", kind_id=team.tenant_id, user=user, role_ids=[admin.ID])
                    else:
                        user_kind_role_service.update_user_roles(
                            kind="team", kind_id=team.tenant_id, user=user, role_ids=[developer.ID])
        print("初始化权限分配成功")
