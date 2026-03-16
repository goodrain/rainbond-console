#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.core.management import BaseCommand
from django.db import transaction
from console.models.main import PlatformFeatureFlag


class Command(BaseCommand):
    help = '初始化平台功能开关'

    @transaction.atomic()
    def handle(self, *args, **options):
        feature_flags = [
            {
                'feature_name': 'k8s_resource_management',
                'enabled': False,
                'description': 'Kubernetes 资源管理功能'
            },
        ]

        for flag_data in feature_flags:
            flag, created = PlatformFeatureFlag.objects.get_or_create(
                feature_name=flag_data['feature_name'],
                defaults={
                    'enabled': flag_data['enabled'],
                    'description': flag_data['description']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'创建功能开关: {flag.feature_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'功能开关已存在: {flag.feature_name}'))

        self.stdout.write(self.style.SUCCESS('功能开关初始化完成'))
