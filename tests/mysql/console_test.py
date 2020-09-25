# -*- coding: utf-8 -*-
import datetime

from django.test import TestCase

from console.models.main import ConsoleSysConfig
from console.models.main import RainbondCenterApp
from console.models.main import RainbondCenterAppInherit
from console.models.main import RainbondCenterPlugin
from console.models.main import ServiceShareRecord
from console.models.main import ServiceShareRecordEvent
from console.models.main import PluginShareRecordEvent
from console.models.main import ComposeGroup
from console.models.main import ComposeServiceRelation
from console.models.main import ServiceSourceInfo
from console.models.main import TeamGitlabInfo
from console.models.main import ServiceRecycleBin
from console.models.main import ServiceRelationRecycleBin
from console.models.main import EnterpriseUserPerm
from console.models.main import TenantUserRole
from console.models.main import TenantUserPermission
from console.models.main import TenantUserRolePermission
from console.models.main import PermGroup
from console.models.main import ServiceRelPerms
from console.models.main import AppExportRecord
from console.models.main import UserMessage
from console.models.main import AppImportRecord
from console.models.main import GroupAppBackupRecord
from console.models.main import GroupAppMigrateRecord
from console.models.main import GroupAppBackupImportRecord
from console.models.main import Applicants
from console.models.main import DeployRelation
from console.models.main import ServiceBuildSource
from console.models.main import TenantServiceBackup
from console.models.main import AppUpgradeRecord
from console.models.main import ServiceUpgradeRecord
from console.models.main import RegionConfig
from console.models.main import CloundBangImages
from console.models.main import Announcement

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class ConsoleTest(TestCase):
    def test_console_sys_config(self):
        # 增加
        ConsoleSysConfig.objects.create(
            key="88fb7498308932711cb0beac238ee420",
            type="json",
            value="""[{"status": true, "key": "app_create"}, {"status": true, "key": "source_code_service_create"},
{"status": false, "key": "service_connect_db"}, {"status": true, "key": "share_app"},
{"status": true, "key": "custom_gw_rule"},
{"status": true, "key": "install_plugin"}, {"status": true, "key": "image_service_create"}]""",
            desc="some config of unknow message",
            enable=True,
            create_time=now,
        ).save()

        # 查询
        all = ConsoleSysConfig.objects.all()
        assert len(all) == 1

        # 修改
        ConsoleSysConfig.objects.filter(key=all[0].key).update(desc=None, enable=False)

        updated = ConsoleSysConfig.objects.get(key=all[0].key)
        assert updated.desc is None
        assert updated.enable is False

        # 删除
        ConsoleSysConfig.objects.filter(key=all[0].key).delete()
        assert len(ConsoleSysConfig.objects.all()) == 0

    def test_rainbond_center_app(self):
        # 增加
        RainbondCenterApp.objects.create(
            group_key='055c60f993324ef583e22f853d280259',
            group_name='import',
            share_user=1,
            record_id=0,
            share_team='amgi9wsp',
            tenant_service_group_id=0,
            pic=None,
            source='import',
            version='v1.0',
            scope='enterprise',
            describe='This is a default description.',
            app_template="""
{"template_version": "v2", "group_version": "v1.0",
"apps": [{"deploy_version": "20190818215605", "service_name": "", "image": "image.goodrain.com/grafana-proxy:0.1"
"service_volume_map_list": [{"category": "app_publish", "file_content": "", "volume_path": "/var/lib/grafana",
"volume_type": "share-file", "volume_name": "data"}, {"category": "app_publish", "file_content": "",
"volume_path": "/var/log/grafana", "volume_type": "share-file", "volume_name": "log"}],
"extend_method": "stateless", "mnt_relation_list": [], "service_key": "72a725ddb86c45fb9c25cdd73ab6794a",
"category": "app_publish", "service_region": "rainbond", "share_type": "image",
"extend_method_map": {"min_node": 1, "step_memory": 128, "max_memory": 65536, "step_node": 1,
"is_restart": 0, "max_node": 20, "min_memory": 128}, "version": "0.1", "service_source": "docker_image",
"memory": 512, "service_type": "application", "service_env_map_list": [],
"service_related_plugin_config": [], "service_alias": "gr6ec5ac",
"service_cname": "\u76d1\u63a7\u53ef\u89c6\u5316\u4ee3\u7406",
"port_map_list": [{"port_alias": "GR6EC5AC8080", "protocol": "http",
"tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "container_port": 8080, "is_outer_service": true,
"is_inner_service": false}],
"share_image": "goodrain.me/amgi9wsp/476ea3c915bf29e4bd529626b86ec5ac:20190818215605",
"dep_service_map_list": [{"dep_service_key": "7403c8abb359477c8cea15aee321500c+13844b20fac6b41b5daccbfae71a43fd"}]
"probes": [], "language": "", "need_share": true, "tenant_id": "f614a5eddea546c2bbaeb67d381599ee",
"cmd": "", "creater": 1, "service_share_uuid": "72a725ddb86c45fb9c25cdd73ab6794a+476ea3c915bf29e4bd529626b86ec5ac"
"service_image": {"hub_user": "", "namespace": "amgi9wsp", "hub_url": "goodrain.me", "hub_password": ""},
"service_connect_info_map_list": [], "service_id": "476ea3c915bf29e4bd529626b86ec5ac"},
{"deploy_version": "20190818215346", "service_name": "", "image": "grafana/grafana:latest",
"service_volume_map_list": [], "extend_method": "stateless", "mnt_relation_list": [],
"service_key": "7403c8abb359477c8cea15aee321500c", "category": "app_publish",
"service_region": "rainbond", "share_type": "image",
"extend_method_map": {"min_node": 1, "step_memory": 128, "max_memory": 65536, "step_node": 1,
"is_restart": 0, "max_node": 20, "min_memory": 128}, "version": "latest", "service_source": "docker_image",
"memory": 512, "service_type": "application", "service_env_map_list": [{"attr_name": "GF_PATHS_CONFIG",
"attr_value": "/etc/grafana/grafana.ini", "is_change": true, "name": "GF_PATHS_CONFIG"},
{"attr_name": "GF_PATHS_DATA", "attr_value": "/var/lib/grafana", "is_change": true,
"name": "GF_PATHS_DATA"}, {"attr_name": "GF_PATHS_HOME", "attr_value": "/usr/share/grafana",
"is_change": true, "name": "GF_PATHS_HOME"}, {"attr_name": "GF_PATHS_LOGS",
"attr_value": "/var/log/grafana", "is_change": true, "name": "GF_PATHS_LOGS"},
{"attr_name": "GF_PATHS_PLUGINS", "attr_value": "/var/lib/grafana/plugins", "is_change": true,
"name": "GF_PATHS_PLUGINS"}, {"attr_name": "GF_PATHS_PROVISIONING",
"attr_value": "/etc/grafana/provisioning", "is_change": true, "name": "GF_PATHS_PROVISIONING"}],
"service_related_plugin_config": [], "service_alias": "gr1a43fd",
"service_cname": "\u76d1\u63a7\u53ef\u89c6\u5316", "port_map_list": [{"port_alias": "GR1A43FD3000",
"protocol": "tcp", "tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "container_port": 3000,
"is_outer_service": false, "is_inner_service": true}],
"share_image": "goodrain.me/amgi9wsp/13844b20fac6b41b5daccbfae71a43fd:20190818215346",
"dep_service_map_list": [], "probes": [{"http_header": "", "initial_delay_second": 2, "cmd": "",
"probe_id": "59d2a6b551d64b96844055d93fd7b899", "period_second": 3, "port": 3000,
"failure_threshold": 3, "is_used": true, "path": "", "service_id": "13844b20fac6b41b5daccbfae71a43fd",
"scheme": "tcp", "success_threshold": 1, "ID": 8, "timeout_second": 30, "mode": "readiness"}],
"language": "", "need_share": true, "tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "cmd": "",
"creater": 1, "service_share_uuid": "7403c8abb359477c8cea15aee321500c+13844b20fac6b41b5daccbfae71a43fd",
"service_image": {"hub_user": "", "namespace": "amgi9wsp", "hub_url": "goodrain.me", "hub_password": ""},
"service_connect_info_map_list": [], "service_id": "13844b20fac6b41b5daccbfae71a43fd"},
{"deploy_version": "20190819012900", "service_name": "", "image": "goodrain.me/rbd-res:20180818",
"service_volume_map_list": [], "extend_method": "stateless", "mnt_relation_list": [],
"service_key": "ee2b03efc3a64786b7122a25a123e8ff", "category": "app_publish", "service_region": "rainbond",
"share_type": "image", "extend_method_map": {"min_node": 1, "step_memory": 128, "max_memory": 65536,
"step_node": 1, "is_restart": 0, "max_node": 20, "min_memory": 512}, "version": "20180818",
"service_source": "docker_image", "memory": 512, "service_type": "application",
"service_env_map_list": [{"attr_name": "GRAFANA_DOMAIN",
"attr_value": "http://8080.gr6ec5ac.acx9dtbf.07c553.grapps.cn", "is_change": true, "name": ""},
{"attr_name": "GRAFANA_TOKEN",
"attr_value": "eyJrIjoiaE04MnBsSkxPYnQ0Nlp3RldodVFxR1hsaFVSbzR2bkYiLCJuIjoiZm9vYmFyIiwiaWQiOjF9",
"is_change": true, "name": ""}], "service_related_plugin_config": [],
"service_alias": "gre957c9", "service_cname": "\u7ba1\u7406\u540e\u53f0",
"port_map_list": [{"port_alias": "GRE957C94999", "protocol": "http",
"tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "container_port": 4999, "is_outer_service": true,
"is_inner_service": false}], "share_image": "goodrain.me/amgi9wsp/4f4669fa04930ad10108a82019e957c9:20190819012900",
"dep_service_map_list": [], "probes": [{"http_header": "", "initial_delay_second": 2, "cmd": "",
"probe_id": "2013b98a19f043fdac9da801d7ac0e32", "period_second": 3, "port": 4999, "failure_threshold": 3,
"is_used": true, "path": "", "service_id": "4f4669fa04930ad10108a82019e957c9", "scheme": "tcp",
"success_threshold": 1, "ID": 6, "timeout_second": 30, "mode": "readiness"}], "language": "",
"need_share": true, "tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "cmd": "", "creater": 1,
"service_share_uuid": "ee2b03efc3a64786b7122a25a123e8ff+4f4669fa04930ad10108a82019e957c9",
"service_image": {"hub_user": "", "namespace": "amgi9wsp", "hub_url": "goodrain.me", "hub_password": ""},
"service_connect_info_map_list": [], "service_id": "4f4669fa04930ad10108a82019e957c9"}],
"group_name": "\u7ba1\u7406\u540e\u53f0", "group_key": "055c60f993324ef583e22f853d280259",
"suffix": ""}
            """,
            is_complete=1,
            is_ingerit=True,
            template_version='v2',
            create_time=now,
            update_time=None,
            enterprise_id='88fb7498308932711cb0beac238ee420',
            install_number=1,
            is_official=0,
            details=None,
            upgrade_time='',
        ).save()

        # 查询
        all = RainbondCenterApp.objects.all()
        assert len(all) == 1

        # 修改
        RainbondCenterApp.objects.filter(group_key=all[0].group_key).update(install_number=2,
                                                                            details='application import detail, balabalabala')

        updated = RainbondCenterApp.objects.get(group_key=all[0].group_key)
        assert updated.install_number == 2
        assert updated.details == 'application import detail, balabalabala'

        # 删除
        RainbondCenterApp.objects.filter(group_key=all[0].group_key).delete()
        assert len(RainbondCenterApp.objects.all()) == 0

    def test_rainbond_center_app_inherit(self):
        # 增加
        RainbondCenterAppInherit.objects.create(
            group_key="055c60f993324ef583e22f853d280259",
            version="v1.0",
            derived_group_key="e3213b4844df40df9cb17e6dcfd4a086",
        ).save()

        # 查询
        all = RainbondCenterAppInherit.objects.all()
        assert len(all) == 1

        # 修改
        RainbondCenterAppInherit.objects.filter(group_key=all[0].group_key).update(
            version="v2.0", derived_group_key="91f0daa5ff88471d9f7d518b2cdf038b")

        updated = RainbondCenterAppInherit.objects.get(group_key=all[0].group_key)
        assert updated.version == 'v2.0'
        assert updated.derived_group_key == '91f0daa5ff88471d9f7d518b2cdf038b'

        # 删除
        RainbondCenterAppInherit.objects.filter(group_key=all[0].group_key).delete()
        assert len(RainbondCenterAppInherit.objects.all()) == 0

    def test_rainbond_center_plugin(self):
        # 增加
        RainbondCenterPlugin.objects.create(
            plugin_key="055c60f993324ef583e22f853d280259",
            plugin_name="import",
            plugin_id="1",
            category="plugini",
            record_id=1,
            version="v1.0",
            build_version="20191028154452123",
            pic=None,
            scope="enterprise",
            source="import",
            share_user=1,
            share_team="amgi9wsp",
            desc="plugin export from rainbond",
            plugin_template="""
{"template_version": "v2", "group_version": "v1.0", "apps": [{"deploy_version": "20190818215605",
"service_name": "", "image": "image.goodrain.com/grafana-proxy:0.1",
"service_volume_map_list": [{"category": "app_publish", "file_content": "",
"volume_path": "/var/lib/grafana", "volume_type": "share-file", "volume_name": "data"},
{"category": "app_publish", "file_content": "", "volume_path": "/var/log/grafana",
"volume_type": "share-file", "volume_name": "log"}], "extend_method": "stateless",
"mnt_relation_list": [], "service_key": "72a725ddb86c45fb9c25cdd73ab6794a", "category": "app_publish",
"service_region": "rainbond", "share_type": "image", "extend_method_map": {"min_node": 1,
"step_memory": 128, "max_memory": 65536, "step_node": 1, "is_restart": 0, "max_node": 20, "min_memory": 128},
"version": "0.1", "service_source": "docker_image", "memory": 512, "service_type": "application",
"service_env_map_list": [], "service_related_plugin_config": [], "service_alias": "gr6ec5ac",
"service_cname": "\u76d1\u63a7\u53ef\u89c6\u5316\u4ee3\u7406", "port_map_list": [{"port_alias": "GR6EC5AC8080",
"protocol": "http", "tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "container_port": 8080,
"is_outer_service": true, "is_inner_service": false}],
"share_image": "goodrain.me/amgi9wsp/476ea3c915bf29e4bd529626b86ec5ac:20190818215605",
"dep_service_map_list": [{"dep_service_key": "7403c8abb359477c8cea15aee321500c+13844b20fac6b41b5daccbfae71a43fd"}],
"probes": [], "language": "", "need_share": true, "tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "cmd": "",
"creater": 1, "service_share_uuid": "72a725ddb86c45fb9c25cdd73ab6794a+476ea3c915bf29e4bd529626b86ec5ac",
"service_image": {"hub_user": "", "namespace": "amgi9wsp", "hub_url": "goodrain.me", "hub_password": ""},
"service_connect_info_map_list": [], "service_id": "476ea3c915bf29e4bd529626b86ec5ac"},
{"deploy_version": "20190818215346", "service_name": "", "image": "grafana/grafana:latest",
"service_volume_map_list": [], "extend_method": "stateless", "mnt_relation_list": [],
"service_key": "7403c8abb359477c8cea15aee321500c", "category": "app_publish", "service_region": "rainbond",
"share_type": "image", "extend_method_map": {"min_node": 1, "step_memory": 128, "max_memory": 65536,
"step_node": 1, "is_restart": 0, "max_node": 20, "min_memory": 128}, "version": "latest",
"service_source": "docker_image", "memory": 512, "service_type": "application",
"service_env_map_list": [{"attr_name": "GF_PATHS_CONFIG", "attr_value": "/etc/grafana/grafana.ini",
"is_change": true, "name": "GF_PATHS_CONFIG"},
{"attr_name": "GF_PATHS_DATA", "attr_value": "/var/lib/grafana", "is_change": true,
"name": "GF_PATHS_DATA"}, {"attr_name": "GF_PATHS_HOME", "attr_value": "/usr/share/grafana",
"is_change": true, "name": "GF_PATHS_HOME"}, {"attr_name": "GF_PATHS_LOGS", "attr_value": "/var/log/grafana",
"is_change": true, "name": "GF_PATHS_LOGS"}, {"attr_name": "GF_PATHS_PLUGINS",
"attr_value": "/var/lib/grafana/plugins", "is_change": true, "name": "GF_PATHS_PLUGINS"},
{"attr_name": "GF_PATHS_PROVISIONING", "attr_value": "/etc/grafana/provisioning",
"is_change": true, "name": "GF_PATHS_PROVISIONING"}], "service_related_plugin_config": [],
"service_alias": "gr1a43fd", "service_cname": "\u76d1\u63a7\u53ef\u89c6\u5316",
"port_map_list": [{"port_alias": "GR1A43FD3000", "protocol": "tcp",
"tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "container_port": 3000, "is_outer_service": false,
"is_inner_service": true}],
"share_image": "goodrain.me/amgi9wsp/13844b20fac6b41b5daccbfae71a43fd:20190818215346",
"dep_service_map_list": [], "probes": [{"http_header": "", "initial_delay_second": 2, "cmd": "",
"probe_id": "59d2a6b551d64b96844055d93fd7b899", "period_second": 3, "port": 3000, "failure_threshold": 3,
"is_used": true, "path": "", "service_id": "13844b20fac6b41b5daccbfae71a43fd", "scheme": "tcp",
"success_threshold": 1, "ID": 8, "timeout_second": 30, "mode": "readiness"}], "language": "",
"need_share": true, "tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "cmd": "", "creater": 1,
"service_share_uuid": "7403c8abb359477c8cea15aee321500c+13844b20fac6b41b5daccbfae71a43fd",
"service_image": {"hub_user": "", "namespace": "amgi9wsp", "hub_url": "goodrain.me", "hub_password": ""},
"service_connect_info_map_list": [], "service_id": "13844b20fac6b41b5daccbfae71a43fd"},
{"deploy_version": "20190819012900", "service_name": "", "image": "goodrain.me/rbd-res:20180818",
"service_volume_map_list": [], "extend_method": "stateless", "mnt_relation_list": [],
"service_key": "ee2b03efc3a64786b7122a25a123e8ff", "category": "app_publish",
"service_region": "rainbond", "share_type": "image", "extend_method_map":
{"min_node": 1, "step_memory": 128, "max_memory": 65536, "step_node": 1, "is_restart": 0,
"max_node": 20, "min_memory": 512}, "version": "20180818", "service_source": "docker_image",
"memory": 512, "service_type": "application", "service_env_map_list": [{"attr_name": "GRAFANA_DOMAIN",
"attr_value": "http://8080.gr6ec5ac.acx9dtbf.07c553.grapps.cn", "is_change": true, "name": ""},
{"attr_name": "GRAFANA_TOKEN",
"attr_value": "eyJrIjoiaE04MnBsSkxPYnQ0Nlp3RldodVFxR1hsaFVSbzR2bkYiLCJuIjoiZm9vYmFyIiwiaWQiOjF9",
"is_change": true, "name": ""}], "service_related_plugin_config": [], "service_alias": "gre957c9",
"service_cname": "\u7ba1\u7406\u540e\u53f0", "port_map_list": [{"port_alias": "GRE957C94999",
"protocol": "http", "tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "container_port": 4999,
"is_outer_service": true, "is_inner_service": false}],
"share_image": "goodrain.me/amgi9wsp/4f4669fa04930ad10108a82019e957c9:20190819012900",
"dep_service_map_list": [], "probes": [{"http_header": "", "initial_delay_second": 2,
"cmd": "", "probe_id": "2013b98a19f043fdac9da801d7ac0e32", "period_second": 3, "port": 4999,
"failure_threshold": 3, "is_used": true, "path": "", "service_id": "4f4669fa04930ad10108a82019e957c9",
"scheme": "tcp", "success_threshold": 1, "ID": 6, "timeout_second": 30, "mode": "readiness"}], "language": "",
"need_share": true, "tenant_id": "f614a5eddea546c2bbaeb67d381599ee", "cmd": "", "creater": 1,
"service_share_uuid": "ee2b03efc3a64786b7122a25a123e8ff+4f4669fa04930ad10108a82019e957c9",
"service_image": {"hub_user": "", "namespace": "amgi9wsp", "hub_url": "goodrain.me", "hub_password": ""},
"service_connect_info_map_list": [], "service_id": "4f4669fa04930ad10108a82019e957c9"}],
"group_name": "\u7ba1\u7406\u540e\u53f0", "group_key": "055c60f993324ef583e22f853d280259", "suffix": ""
            """,
            is_complete=1,
            create_time=now,
            update_time=None,
            enterprise_id="055c60f993324ef583e22f853d280259",
            details="this is plugin's details, not detail",
        ).save()

        # 查询
        all = RainbondCenterPlugin.objects.all()
        assert len(all) == 1

        # 修改
        RainbondCenterPlugin.objects.filter(plugin_key=all[0].plugin_key).update(plugin_name="network plugin", details=None)

        updated = RainbondCenterPlugin.objects.get(plugin_key=all[0].plugin_key)
        assert updated.plugin_name == "network plugin"
        assert updated.details is None

        # 删除

        RainbondCenterPlugin.objects.filter(plugin_key=all[0].plugin_key).delete()
        assert len(RainbondCenterPlugin.objects.all()) == 0

    def test_service_share_record(self):
        # 增加
        ServiceShareRecord.objects.create(
            group_share_id="242c6fcce6fd414784d32aabf16ef1e5",
            group_id="9",
            team_name="amgi9wsp",
            event_id="",
            share_version='',
            is_success=1,
            step=1,
            create_time=now,
            update_time=now,
        ).save()

        # 查询
        all = ServiceShareRecord.objects.all()
        assert len(all) == 1

        # 修改
        ServiceShareRecord.objects.filter(group_share_id=all[0].group_share_id).update(is_success=False, step=2)

        updated = ServiceShareRecord.objects.get(group_share_id=all[0].group_share_id)
        assert updated.is_success is False
        assert updated.step == 2

        # 删除
        ServiceShareRecord.objects.filter(group_share_id=all[0].group_share_id).delete()
        assert len(ServiceShareRecord.objects.all()) == 0

    def test_service_share_recordd_event(self):
        # 增加
        ServiceShareRecordEvent.objects.create(
            record_id=1,
            region_share_id=1,
            team_name="amgi9wsp",
            service_key="a21405abcca44dc6837beb4a8ea76d46",
            service_id="886b9ce6fb0b89f272104239277988c9",
            service_alias="gr7988c9",
            service_name="2048",
            team_id="f73a4fd089a54571b564090068920049",
            event_id="41c44d02911e437ea48a68e40287ff9f",
            event_status="success",
            create_time=now,
            update_time=now,
        ).save()

        # 查询
        all = ServiceShareRecordEvent.objects.all()
        assert len(all) == 1

        # 修改
        ServiceShareRecordEvent.objects.filter(record_id=all[0].record_id).update(event_status="failed", service_name="nginx")

        updated = ServiceShareRecordEvent.objects.get(record_id=all[0].record_id)
        assert updated.event_status == "failed"
        assert updated.service_name == 'nginx'

        # 删除
        ServiceShareRecordEvent.objects.filter(record_id=all[0].record_id).delete()
        assert len(ServiceShareRecordEvent.objects.all()) == 0

    def test_plugin_share_record_event(self):
        # 增加
        PluginShareRecordEvent.objects.create(
            record_id=1,
            region_share_id='db7f3189-8786-48ee-ad66-1b53e23ccdda',
            team_id="f73a4fd089a54571b564090068920049",
            team_name="amgi9wsp",
            plugin_id="fe38ded3f8fb4d78962c691ec31b51c3",
            plugin_name="chinese plugin name",
            event_id="c58a4c9ffb784c9f863f5045e3c11f33",
            event_status="success",
            create_time=now,
            update_time=now,
        ).save()

        # 查询
        all = PluginShareRecordEvent.objects.all()
        assert len(all) == 1

        # 修改
        PluginShareRecordEvent.objects.filter(record_id=all[0].record_id).update(event_status="not_start",
                                                                                 plugin_name="test plugin name")

        updated = PluginShareRecordEvent.objects.get(record_id=all[0].record_id)
        assert updated.event_status == "not_start"
        assert updated.plugin_name == "test plugin name"

        # 删除
        PluginShareRecordEvent.objects.filter(record_id=all[0].record_id).delete()
        assert len(PluginShareRecordEvent.objects.all()) == 0

    def test_compose_group(self):
        # 增加
        ComposeGroup.objects.create(
            group_id=2,
            team_id="f73a4fd089a54571b564090068920049",
            region="rainbond",
            compose_content="""
        version: '3'
services:
  mysql:
    image: "harbortest.com/mysql/mysql:5.6"
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: root
        """,
            compose_id="8cb61669b82e4563bb447b2196bbfc09",
            create_status="complete",
            check_uuid="697d9790-71d1-4aa3-b0ce-7eef4eb86efa",
            check_event_id="a60adefcee6e408fac11c18a2525513e",
            hub_user="admin",
            hub_pass="Harbor12345",
            create_time=now,
        ).save()

        # 查询
        all = ComposeGroup.objects.all()
        assert len(all) == 1

        # 修改
        ComposeGroup.objects.filter(group_id=all[0].group_id).update(hub_user="fanyangyang", create_status="failed")

        updated = ComposeGroup.objects.get(group_id=all[0].group_id)
        assert updated.hub_user == "fanyangyang"
        assert updated.create_status == "failed"

        # 删除
        ComposeGroup.objects.filter(group_id=all[0].group_id).delete()
        assert len(ComposeGroup.objects.all()) == 0

    def test_compose_service_relation(self):
        # 增加
        ComposeServiceRelation.objects.create(team_id="fe38ded3f8fb4d78962c691ec31b51c3",
                                              service_id="fe38ded3f8fb4d78962c691ec31b51c3",
                                              compose_id="8cb61669b82e4563bb447b2196bbfc09",
                                              create_time=now).save()

        # 查询
        all = ComposeServiceRelation.objects.all()
        assert len(all) == 1

        # 修改
        ComposeServiceRelation.objects.filter(team_id=all[0].team_id).update(service_id="8cb61669b82e4563bb447b2196bbfc09")

        updated = ComposeServiceRelation.objects.get(team_id=all[0].team_id)
        assert updated.service_id == "8cb61669b82e4563bb447b2196bbfc09"

        # 删除
        ComposeServiceRelation.objects.filter(team_id=all[0].team_id).delete()
        assert len(ComposeServiceRelation.objects.all()) == 0

    def test_service_source_info(self):
        # 增加
        ServiceSourceInfo.objects.create(
            team_id="f73a4fd089a54571b564090068920049",
            service_id="48e7f03cd68b4330a92b2161029f497e",
            user_name=None,
            password=None,
            group_key="e3213b4844df40df9cb17e6dcfd4a086",
            version="v1.0",
            service_share_uuid="5fddefb0087c4a0d9b70feb5d3cf0850+c2f877c9157104c647f752e0ab0a44c7",
            extend_info="""{"source_service_share_uuid": "5fddefb0087c4a0d9b70feb5d3cf0850+c2f877c9157104c647f752e0ab0a44c7",
"hub_user": "", "source_deploy_version": "20191022180504", "namespace": "amgi9wsp", "hub_password": "",
"hub_url": "goodrain.me"}""",
            create_time=now,
        ).save()

        # 查询
        all = ServiceSourceInfo.objects.all()
        assert len(all) == 1

        # 修改
        ServiceSourceInfo.objects.filter(team_id=all[0].team_id).update(
            version=None, service_share_uuid="963554fecfd9456ca963a4f3922678ca+6ecb959b6366a320b20148054b58d70d")

        updated = ServiceSourceInfo.objects.get(team_id=all[0].team_id)
        assert updated.version is None
        assert updated.service_share_uuid == '963554fecfd9456ca963a4f3922678ca+6ecb959b6366a320b20148054b58d70d'

        # 删除
        ServiceSourceInfo.objects.filter(team_id=all[0].team_id).delete()
        assert len(ServiceSourceInfo.objects.all()) == 0

    def test_team_gitlab_info(self):
        # 新增
        TeamGitlabInfo.objects.create(team_id="f73a4fd089a54571b564090068920049",
                                      repo_name="rainbond",
                                      respo_url="https://github.com/goodrain/rainbond.git",
                                      git_project_id=1,
                                      code_version="v5.1.8",
                                      create_time=now).save()

        # 查询
        all = TeamGitlabInfo.objects.all()
        assert len(all) == 1

        # 修改
        TeamGitlabInfo.objects.filter(team_id=all[0].team_id).update(respo_url="https://github.com/fanyangyang/rainbond.git",
                                                                     git_project_id=2,
                                                                     code_version="v5.2")

        updated = TeamGitlabInfo.objects.get(team_id=all[0].team_id)
        assert updated.respo_url == "https://github.com/fanyangyang/rainbond.git"
        assert updated.git_project_id == 2
        assert updated.code_version == "v5.2"

        # 删除
        TeamGitlabInfo.objects.filter(team_id=all[0].team_id).delete()
        assert len(TeamGitlabInfo.objects.all()) == 0

    def test_tenant_service_recycle_bin(self):
        # 增加
        ServiceRecycleBin.objects.create(
            service_id="b0baf29788500c429a242185605f8cf6",
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_key="3936a406ccdf4b55ad747be3ce1cb21f",
            service_alias="gr5f8cf6",
            service_cname="not know service chinese name",
            service_region="rainbond",
            desc="application info",
            category="application",
            service_port=0,
            is_web_service=True,
            version="latest",
            update_version=1,
            image="goodrain.me/runner:latest",
            cmd="start web",
            setting=None,
            extend_method="stateless",
            env=None,
            min_node=1,
            min_cpu=2,
            min_memory=4096,
            inner_port=5000,
            volume_mount_path=None,
            host_path=None,
            deploy_version="20190330184526",
            code_from="gitlab_manual",
            git_url="http://git.goodrain.com/goodrain/goodrain-sso.git",
            create_time=now,
            git_project_id=0,
            is_code_upload=False,
            code_version="master",
            service_type="application",
            creater=1,
            language="Python",
            protocol='',
            total_memory=0,
            is_service=0,
            namespace="goodrain",
            volume_type="shared",
            port_type="multi_outer",
            service_origin="assistant",
            expired_time=None,
            tenant_service_group_id=0,
            service_source="source_code",
            create_status="complete",
            update_time=now,
            check_uuid="ca31d5ef-4f6d-4976-9c99-ad18f4d864f2",
            check_event_id="9ef06b7b85724de2bd75078dab397843",
            docker_cmd=None,
        ).save()

        # 查询
        all = ServiceRecycleBin.objects.all()
        assert len(all) == 1

        # 修改
        ServiceRecycleBin.objects.filter(service_id="b0baf29788500c429a242185605f8cf6",
                                         tenant_id="b73e01d3b83546cc8d33d60a1618a79f").update(
                                             language="go", is_service=1, deploy_version="20191028173818000")

        updated = ServiceRecycleBin.objects.get(service_id="b0baf29788500c429a242185605f8cf6",
                                                tenant_id="b73e01d3b83546cc8d33d60a1618a79f")
        assert updated.language == "go"
        assert updated.is_service == 1
        assert updated.deploy_version == "20191028173818000"

        # 删除
        ServiceRecycleBin.objects.filter(service_id="b0baf29788500c429a242185605f8cf6",
                                         tenant_id="b73e01d3b83546cc8d33d60a1618a79f").delete()
        assert len(ServiceRecycleBin.objects.all()) == 0

    def test_tenant_service_relation_recycle_bin(self):
        # 增加
        ServiceRelationRecycleBin.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="b0baf29788500c429a242185605f8cf6",
            dep_service_id="3936a406ccdf4b55ad747be3ce1cb21f",
            dep_service_type="mysql",
            dep_order=1,
        ).save()

        # 查询
        all = ServiceRelationRecycleBin.objects.all()
        assert len(all) == 1

        # 修改
        ServiceRelationRecycleBin.objects.filter(service_id="b0baf29788500c429a242185605f8cf6",
                                                 tenant_id="b73e01d3b83546cc8d33d60a1618a79f").update(dep_service_type="web",
                                                                                                      dep_order=2)

        updated = ServiceRelationRecycleBin.objects.get(service_id="b0baf29788500c429a242185605f8cf6",
                                                        tenant_id="b73e01d3b83546cc8d33d60a1618a79f")
        assert updated.dep_service_type == "web"
        assert updated.dep_order == 2

        # 删除
        ServiceRelationRecycleBin.objects.filter(service_id="b0baf29788500c429a242185605f8cf6",
                                                 tenant_id="b73e01d3b83546cc8d33d60a1618a79f").delete()
        assert len(ServiceRelationRecycleBin.objects.all()) == 0

    def test_enterprise_user_perm(self):
        # 增加
        EnterpriseUserPerm.objects.create(
            user_id=1,
            enterprise_id="b4ff5ce5301ee83f1fba16c9f37fc101",
            identity="admin",
            token="359424eb84573ab4e432b0add68ddbee",
        ).save()

        # 查询
        all = EnterpriseUserPerm.objects.all()
        assert len(all) == 1

        # 修改
        EnterpriseUserPerm.objects.filter(user_id=1).update(token="7ea3f9e18369c8ebdb0773926779ffd7", identity="developer")

        updated = EnterpriseUserPerm.objects.get(user_id=1)
        assert updated.token == "7ea3f9e18369c8ebdb0773926779ffd7"
        assert updated.identity == "developer"

        # 删除
        EnterpriseUserPerm.objects.filter(user_id=1).delete()
        assert len(EnterpriseUserPerm.objects.all()) == 0

    def test_tenant_user_role(self):
        # 增加
        TenantUserRole.objects.create(role_name="test", tenant_id=154, is_default=False).save()

        # 查询
        all = TenantUserRole.objects.all()
        assert len(all) == 1

        # 修改
        TenantUserRole.objects.filter(tenant_id=154).update(is_default=True, role_name="developer")

        updated = TenantUserRole.objects.get(tenant_id=154)
        assert updated.is_default is True
        assert updated.role_name == "developer"

        # 删除
        TenantUserRole.objects.filter(tenant_id=154).delete()
        assert len(TenantUserRole.objects.all()) == 0

    def test_tenant_user_permission(self):
        # 增加
        TenantUserPermission.objects.create(
            codename="create_three_service",
            per_info="create threepart service",
            is_select=True,
            group=1,
            per_explanation=None,
        ).save()

        # 查询
        all = TenantUserPermission.objects.all()
        assert len(all) == 1

        # 修改
        TenantUserPermission.objects.filter(group=1).update(per_explanation="this is describe about tenant_user_permisssion",
                                                            per_info="delete threepart service",
                                                            codename="delete_three_service")

        updated = TenantUserPermission.objects.get()
        assert updated.per_explanation == "this is describe about tenant_user_permisssion"
        assert updated.per_info == "delete threepart service"
        assert updated.codename == "delete_three_service"

        # 删除
        TenantUserPermission.objects.filter(group=1).delete()
        assert len(TenantUserPermission.objects.all()) == 0

    def test_tenant_user_role_permission(self):
        # 增加
        TenantUserRolePermission.objects.create(role_id=0, per_id=1).save()

        # 查询
        all = TenantUserRolePermission.objects.all()
        assert len(all) == 1

        # 修改
        TenantUserRolePermission.objects.filter(role_id=0).update(per_id=2)

        updated = TenantUserRolePermission.objects.get(role_id=0)
        assert updated.per_id == 2

        # 删除
        TenantUserRolePermission.objects.filter(role_id=0).delete()
        assert len(TenantUserRolePermission.objects.all()) == 0

    def test_tenant_permission_group(self):
        # 增加
        PermGroup.objects.create(group_name="group name").save()

        # 查询
        all = PermGroup.objects.all()
        assert len(all) == 1

        # 修改
        PermGroup.objects.filter(group_name="group name").update(group_name="new name")

        updated = PermGroup.objects.get(ID=1)
        assert updated.group_name == "new name"

        # 删除
        PermGroup.objects.filter(group_name="new name").delete()
        assert len(PermGroup.objects.all()) == 0

    def test_service_user_perms(self):
        # 增加
        ServiceRelPerms.objects.create(
            user_id=6616,
            service_id=2568,
            perm_id=36,
        ).save()

        # 查询
        all = ServiceRelPerms.objects.all()
        assert len(all) == 1

        # 修改
        ServiceRelPerms.objects.filter(user_id=6616, service_id=2568).update(perm_id=4)

        updated = ServiceRelPerms.objects.get(user_id=6616, service_id=2568)
        assert updated.perm_id == 4

        # 删除
        ServiceRelPerms.objects.filter(user_id=6616, service_id=2568).delete()
        assert len(ServiceRelPerms.objects.all()) == 0

    def tet_app_export_record(self):
        # 增加
        AppExportRecord.objects.create(
            group_key="f900b84ac20b4a56af649193e0004dcd",
            version="5.7.23",
            format="rainbond-app",
            event_id="e8e200e68822495aa220b12737378b30",
            status="success",
            file_path="/v2/app/download/rainbond-app/MYSQL-Percona-20191028182048000.zip",
            create_time=now,
            update_time=None,
            enterprise_id="b4ff5ce5301ee83f1fba16c9f37fc101",
        ).save()

        # 查询
        all = AppExportRecord.objects.all()
        assert len(all) == 1

        # 修改
        AppExportRecord.objects.filter(group_key="f900b84ac20b4a56af649193e0004dcd").update(status='exporting',
                                                                                            version='v0.19.20391203',
                                                                                            format="docker-compse")

        updated = AppExportRecord.objects.get(group_key="f900b84ac20b4a56af649193e0004dcd")
        assert updated.status == 'exporting'
        assert updated.version == 'v0.19.20391203'
        assert updated.format == "docker-compse"

        # 删除
        AppExportRecord.objects.filter(group_key="f900b84ac20b4a56af649193e0004dcd").delete()
        assert len(AppExportRecord.objects.all()) == 0

    def test_user_message(self):
        # 增加
        UserMessage.objects.create(
            message_id="51c5dc9b784943cbbabae055b9630e36",
            receiver_id="4160",
            content="balabala xiaomoxian",
            is_read=False,
            create_time=now,
            update_time=now,
            msg_type="news",
            announcement_id=None,
            title="i can't read it, can you?",
            level="low",
        ).save()

        # 查询
        all = UserMessage.objects.all()
        assert len(all) == 1

        # 修改
        UserMessage.objects.filter(message_id="51c5dc9b784943cbbabae055b9630e36").update(is_read=True, level="mid")

        updated = UserMessage.objects.get(message_id="51c5dc9b784943cbbabae055b9630e36")
        assert updated.is_read is True
        assert updated.level == "mid"

        # 删除
        UserMessage.objects.filter(message_id="51c5dc9b784943cbbabae055b9630e36").delete()
        assert len(UserMessage.objects.all()) == 0

    def test_app_import_record(self):
        # 增加
        AppImportRecord.objects.create(
            event_id="4a7a5189d00d4b708eaf8e4898621336",
            status="failed",
            scope="enterprise",
            format="rainbond-app",
            source_dir="/grdata/app/import/4a7a5189d00d4b708eaf8e4898621336",
            create_time=now,
            update_time=now,
            team_name="36c0xf8p",
            region="rainbond",
            user_name="eric wang",
        ).save()

        # 查询
        all = AppImportRecord.objects.all()
        assert len(all) == 1

        # 修改
        AppImportRecord.objects.filter(event_id="4a7a5189d00d4b708eaf8e4898621336").update(status="success", scope="group")

        updated = AppImportRecord.objects.get(event_id="4a7a5189d00d4b708eaf8e4898621336")
        assert updated.status == "success"
        assert updated.scope == "group"

        # 删除
        AppImportRecord.objects.filter(event_id="4a7a5189d00d4b708eaf8e4898621336").delete()
        assert len(AppImportRecord.objects.all()) == 0

    def test_groupapp_backup(self):
        # 增加
        GroupAppBackupRecord.objects.create(
            group_id=5,
            event_id="547515b3d12f43db9bb661d4f51c7c9e",
            group_uuid="1d10b8bc507c4b17ae23df2b434f22ef",
            version="20181228172011",
            backup_id="ea4c50d3cd0a4a15aa6bbad0a160d6f1",
            team_id="4f6ad5fbb2f844d7b1ba12df520c15a7",
            user="mrexamo",
            region="rainbond",
            status="success",
            note="group app backup note",
            mode="full-online",
            source_dir="/app_publish/a5qw69mz/backup/a4baa0891e914b17a3b8976505cc6bf9_20181228172011/metadata_data.zip",
            backup_size=1869326262,
            create_time=now,
            total_memory=6784,
            backup_server_info="""
{"image_info": {"hub_url": "hub.goodrain.com", "hub_user": "goodrain-admin", "is_trust": true,
"namespace": "goodrain", "hub_password": "goodrain123465"}, "slug_info": {"namespace": "/app_publish/a5qw69mz",
"ftp_password": "goodrain123465", "ftp_host": "139.196.88.57", "ftp_port": "10022", "ftp_username": "goodrain"}}
            """,
            source_type="local",
        ).save()

        # 查询
        all = GroupAppBackupRecord.objects.all()
        assert len(all) == 1

        # 修改
        GroupAppBackupRecord.objects.filter(event_id="547515b3d12f43db9bb661d4f51c7c9e").update(total_memory=1024 * 8,
                                                                                                backup_size=4096 * 1024,
                                                                                                mode="patch",
                                                                                                status="failed")
        updated = GroupAppBackupRecord.objects.get(event_id="547515b3d12f43db9bb661d4f51c7c9e")
        assert updated.total_memory == 1024 * 8
        assert updated.backup_size == 4096 * 1024
        assert updated.mode == "patch"
        assert updated.status == "failed"

        # 删除
        GroupAppBackupRecord.objects.filter(event_id="547515b3d12f43db9bb661d4f51c7c9e").delete()
        assert len(GroupAppBackupRecord.objects.all()) == 0

    def test_groupapp_migrate(self):
        # 增加
        GroupAppMigrateRecord.objects.create(
            group_id=6,
            event_id="accfa9736f904d62940d4e033128c9ed",
            group_uuid="19ae84cad71943e5b58f0ddc501415c6",
            version="20190220214510",
            backup_id="d5859360d9d94e488f299fc9fbece7eb",
            migrate_team="23ehgni5",
            user="gradmin",
            migrate_region="rainbond",
            status="starting",
            migrate_type="recover",
            restore_id="26e3161d02e04657b0a3d2bbe4fd364e",
            create_time=now,
            original_group_id=6,
            original_group_uuid="19ae84cad71943e5b58f0ddc501415c6",
        ).save()

        # 查询
        all = GroupAppMigrateRecord.objects.all()
        assert len(all) == 1

        # 修改
        GroupAppMigrateRecord.objects.filter(event_id="accfa9736f904d62940d4e033128c9ed").update(status="failed",
                                                                                                 version="20191028185721000")

        updated = GroupAppMigrateRecord.objects.get(event_id="accfa9736f904d62940d4e033128c9ed")
        assert updated.status == "failed"
        assert updated.version == "20191028185721000"

        # 删除
        GroupAppMigrateRecord.objects.filter(event_id="accfa9736f904d62940d4e033128c9ed").delete()
        assert len(GroupAppMigrateRecord.objects.all()) == 0

    def test_groupapp_backup_import(self):
        # 增加
        GroupAppBackupImportRecord.objects.create(
            event_id="accfa9736f904d62940d4e033128c9ed",
            status="failed",
            file_temp_dir="/app_publish/a5qw69mz/backup/a4baa0891e914b17a3b8976505cc6bf9_20181228172011/metadata_data.zip",
            create_time=now,
            update_time=now,
            team_name="23ehgni5",
            region="rainbond",
        ).save()

        # 查询
        all = GroupAppBackupImportRecord.objects.all()
        assert len(all) == 1

        # 修改
        GroupAppBackupImportRecord.objects.filter(event_id="accfa9736f904d62940d4e033128c9ed").update(team_name="team_name",
                                                                                                      region="test region",
                                                                                                      status="success")

        updated = GroupAppBackupImportRecord.objects.get(event_id="accfa9736f904d62940d4e033128c9ed")
        assert updated.team_name == "team_name"
        assert updated.region == "test region"
        assert updated.status == "success"

        # 删除
        GroupAppBackupImportRecord.objects.filter(event_id="accfa9736f904d62940d4e033128c9ed").delete()
        assert len(GroupAppBackupImportRecord.objects.all()) == 0

    def test_applicants(self):
        # 增加
        Applicants.objects.create(
            user_id=8429,
            user_name="longyuanbing",
            team_id="3b1f4056edb2411cac3f993fde23a85f",
            team_name="ew4xpfs8",
            apply_time=now,
            is_pass=0,
            team_alias="dev",
        ).save()

        # 查询
        all = Applicants.objects.all()
        assert len(all) == 1

        # 修改
        Applicants.objects.filter(user_id=8429).update(is_pass=1)

        updated = Applicants.objects.get(user_id=8429)
        assert updated.is_pass == 1

        # 删除
        Applicants.objects.filter(user_id=8429).delete()
        assert len(Applicants.objects.all()) == 0

    def test_deploy_relation(self):
        # 增加
        DeployRelation.objects.create(service_id="ac96eed7c78dcda7106bbcd63c78816a",
                                      key_type='',
                                      secret_key="KGRwMApTJ3NlY3JldF9rZXknCnAxClMnb2p5cEc3TlknCnAyCnMu").save()

        # 查询
        all = DeployRelation.objects.all()
        assert len(all) == 1

        # 修改
        DeployRelation.objects.filter(service_id="ac96eed7c78dcda7106bbcd63c78816a").update(key_type="unknown")

        updated = DeployRelation.objects.get(service_id="ac96eed7c78dcda7106bbcd63c78816a")
        assert updated.key_type == "unknown"

        # 删除
        DeployRelation.objects.filter(service_id="ac96eed7c78dcda7106bbcd63c78816a").delete()
        assert len(DeployRelation.objects.all()) == 0

    def test_service_build_source(self):
        # 增加
        ServiceBuildSource.objects.create(service_id="ac96eed7c78dcda7106bbcd63c78816a",
                                          group_key="19ae84cad71943e5b58f0ddc501415c6",
                                          version="2019201545").save()

        # 查询
        all = ServiceBuildSource.objects.all()
        assert len(all) == 1

        # 修改
        ServiceBuildSource.objects.filter(service_id="ac96eed7c78dcda7106bbcd63c78816a").update(version="201928191853")

        updated = ServiceBuildSource.objects.get(service_id="ac96eed7c78dcda7106bbcd63c78816a")
        assert updated.version == "201928191853"

        # 删除
        ServiceBuildSource.objects.filter(service_id="ac96eed7c78dcda7106bbcd63c78816a").delete()
        assert len(ServiceBuildSource.objects.all()) == 0

    def test_tenant_service_backup(self):
        # 增加
        TenantServiceBackup.objects.create(
            region_name="rainbond",
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="b7992f6a242b48dab0783b0a8b49374b",
            backup_id="dd172f863fb743c681c59b20c32082e3",
            backup_data="""
{"service_config_file": [], "service_extend_method": {"min_node": 1, "step_memory": 128,
"max_memory": 65536, "step_node": 1, "is_restart": false, "max_node": 1,
"service_key": "ea30f85acb714fc080251b0417cf6544", "app_version": "percona-5.7",
"min_memory": 512, "ID": 28}, "service_compile_env": null, "service_ports": [],
"service_base": {"min_node": 1, "protocol": "", "version": "percona-5.7", "service_region": "rainbond",
"is_upgrate": false, "service_name": "",
"image": "hub.goodrain.com/goodrain/mysql:20181019160510_20181019160510_5.7.23", "create_status": "complete",
"docker_cmd": null, "build_upgrade": true, "create_time": "2019-05-26 10:54:08", "extend_method": "state",
"total_memory": 512, "service_key": "ea30f85acb714fc080251b0417cf6544", "git_project_id": 0,
"category": "app_publish", "deploy_version": "20181019160510", "tenant_service_group_id": 619,
"namespace": "goodrain", "secret": null, "setting": "", "service_origin": "assistant", "expired_time": null,
"env": ",", "update_version": 1, "service_type": "application", "min_memory": 512, "service_source": "market",
"check_event_id": "", "update_time": "2019-05-26 10:54:08", "is_code_upload": false, "code_from": "",
"service_alias": "gr49374b", "service_cname": "MySQL5.7", "server_type": "git", "is_web_service": false,
"is_service": false, "host_path": "", "open_webhooks": false, "volume_mount_path": "", "port_type": "multi_outer",
"ID": 2539, "desc": "market app ", "language": "", "min_cpu": 80, "tenant_id": "b73e01d3b83546cc8d33d60a1618a79f",
"code_version": null, "cmd": "", "volume_type": "shared", "inner_port": 0, "creater": 6534, "service_port": 0,
"service_id": "b7992f6a242b48dab0783b0a8b49374b", "check_uuid": "", "git_url": null}, "service_perms": [],
"service_volumes": [], "service_probes": [], "image_service_relation": null, "service_mnts": [],
"service_labels": [], "service_relation": [], "service_events": [{"status": "success", "code_version": "",
"deploy_version": "20181019160510", "event_id": "0cc71985db6040ed90732885d2ffd13b",
"tenant_id": "b73e01d3b83546cc8d33d60a1618a79f", "start_time": "2019-05-26 10:59:55",
"region": "rainbond", "old_deploy_version": "", "end_time": null, "type": "truncate", "old_code_version": "",
"service_id": "b7992f6a242b48dab0783b0a8b49374b", "message": "MySQL5.7", "final_status": "complete",
"user_name": "\u609f\u7a7a", "ID": 12893}], "service_plugin_relation": [], "service_source": null,
"service_env_vars": [], "service_plugin_config": [], "service_auths": [], "service_domains": [],
"service_tcpdomains": []}
             """,
            create_time=now,
            update_time=now,
        ).save()

        # 查询
        all = TenantServiceBackup.objects.all()
        assert len(all) == 1

        # 修改
        TenantServiceBackup.objects.filter(tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
                                           service_id="b7992f6a242b48dab0783b0a8b49374b",
                                           backup_id="dd172f863fb743c681c59b20c32082e3").update(backup_data="""
{"service_config_file": [], "service_extend_method": {"min_node": 1, "step_memory": 128,
"max_memory": 65536, "step_node": 1, "is_restart": false, "max_node": 1,
"service_key": "ea30f85acb714fc080251b0417cf6544", "app_version": "percona-5.7", "min_memory": 512, "ID": 28},
"service_compile_env": null, "service_ports": [], "service_base": {"min_node": 1, "protocol": "",
"version": "percona-5.7", "service_region": "rainbond", "is_upgrate": false, "service_name": "",
"image": "hub.goodrain.com/goodrain/mysql:20181019160510_20181019160510_5.7.23", "create_status": "complete",
"docker_cmd": null, "build_upgrade": true, "create_time": "2019-05-26 10:54:08", "extend_method": "state",
"total_memory": 512, "service_key": "ea30f85acb714fc080251b0417cf6544", "git_project_id": 0, "category": "app_publish",
"deploy_version": "20181019160510", "tenant_service_group_id": 619, "namespace": "goodrain", "secret": null,
"setting": "", "service_origin": "assistant", "expired_time": null, "env": ",", "update_version": 1,
"service_type": "application", "min_memory": 512, "service_source": "market", "check_event_id": "",
"update_time": "2019-05-26 10:54:08", "is_code_upload": false, "code_from": "", "service_alias": "gr49374b",
"service_cname": "MySQL5.7", "server_type": "git", "is_web_service": false, "is_service": false, "host_path": "",
"open_webhooks": false, "volume_mount_path": "", "port_type": "multi_outer", "ID": 2539, "desc": "market app ",
"language": "", "min_cpu": 80, "tenant_id": "b73e01d3b83546cc8d33d60a1618a79f", "code_version": null, "cmd": "",
"volume_type": "shared", "inner_port": 0, "creater": 6534, "service_port": 0,
"service_id": "b7992f6a242b48dab0783b0a8b49374b", "check_uuid": "", "git_url": null},
"service_perms": [], "service_volumes": [], "service_probes": [], "image_service_relation": null,
"service_mnts": [], "service_labels": [], "service_relation": [], "service_events": [{"status": "success",
"code_version": "", "deploy_version": "20181019160510", "event_id": "0cc71985db6040ed90732885d2ffd13b",
"tenant_id": "b73e01d3b83546cc8d33d60a1618a79f", "start_time": "2019-05-26 10:59:55", "region": "rainbond",
"old_deploy_version": "", "end_time": null, "type": "truncate", "old_code_version": "",
"service_id": "b7992f6a242b48dab0783b0a8b49374b", "message": "MySQL5.7", "final_status": "complete",
"user_name": "\u609f\u7a7a", "ID": 12893}]}
        """)

        updated = TenantServiceBackup.objects.get(tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
                                                  service_id="b7992f6a242b48dab0783b0a8b49374b",
                                                  backup_id="dd172f863fb743c681c59b20c32082e3")
        assert updated.backup_data == """
{"service_config_file": [], "service_extend_method": {"min_node": 1, "step_memory": 128,
"max_memory": 65536, "step_node": 1, "is_restart": false, "max_node": 1,
"service_key": "ea30f85acb714fc080251b0417cf6544", "app_version": "percona-5.7", "min_memory": 512, "ID": 28},
"service_compile_env": null, "service_ports": [], "service_base": {"min_node": 1, "protocol": "",
"version": "percona-5.7", "service_region": "rainbond", "is_upgrate": false, "service_name": "",
"image": "hub.goodrain.com/goodrain/mysql:20181019160510_20181019160510_5.7.23", "create_status": "complete",
"docker_cmd": null, "build_upgrade": true, "create_time": "2019-05-26 10:54:08", "extend_method": "state",
"total_memory": 512, "service_key": "ea30f85acb714fc080251b0417cf6544", "git_project_id": 0, "category": "app_publish",
"deploy_version": "20181019160510", "tenant_service_group_id": 619, "namespace": "goodrain", "secret": null,
"setting": "", "service_origin": "assistant", "expired_time": null, "env": ",", "update_version": 1,
"service_type": "application", "min_memory": 512, "service_source": "market", "check_event_id": "",
"update_time": "2019-05-26 10:54:08", "is_code_upload": false, "code_from": "", "service_alias": "gr49374b",
"service_cname": "MySQL5.7", "server_type": "git", "is_web_service": false, "is_service": false, "host_path": "",
"open_webhooks": false, "volume_mount_path": "", "port_type": "multi_outer", "ID": 2539, "desc": "market app ",
"language": "", "min_cpu": 80, "tenant_id": "b73e01d3b83546cc8d33d60a1618a79f", "code_version": null, "cmd": "",
"volume_type": "shared", "inner_port": 0, "creater": 6534, "service_port": 0,
"service_id": "b7992f6a242b48dab0783b0a8b49374b", "check_uuid": "", "git_url": null},
"service_perms": [], "service_volumes": [], "service_probes": [], "image_service_relation": null,
"service_mnts": [], "service_labels": [], "service_relation": [], "service_events": [{"status": "success",
"code_version": "", "deploy_version": "20181019160510", "event_id": "0cc71985db6040ed90732885d2ffd13b",
"tenant_id": "b73e01d3b83546cc8d33d60a1618a79f", "start_time": "2019-05-26 10:59:55", "region": "rainbond",
"old_deploy_version": "", "end_time": null, "type": "truncate", "old_code_version": "",
"service_id": "b7992f6a242b48dab0783b0a8b49374b", "message": "MySQL5.7", "final_status": "complete",
"user_name": "\u609f\u7a7a", "ID": 12893}]}
        """

        # 删除
        TenantServiceBackup.objects.filter(tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
                                           service_id="b7992f6a242b48dab0783b0a8b49374b",
                                           backup_id="dd172f863fb743c681c59b20c32082e3").delete()
        assert len(TenantServiceBackup.objects.all()) == 0

    def test_app_upgrade_record(self):
        # 增加
        AppUpgradeRecord.objects.create(
            tenant_id="e4dd12842fdd4395815dd486cacf360d",
            group_id=240,
            group_key="f6d1ac6efee14b8d9a49d450030e551d",
            group_name="java-demo",
            version="",
            old_version="",
            status=1,
            update_time=now,
            create_time=now,
        ).save()

        # 查询
        all = AppUpgradeRecord.objects.all()
        assert len(all) == 1

        # 修改
        AppUpgradeRecord.objects.filter(tenant_id="e4dd12842fdd4395815dd486cacf360d",
                                        group_id=240,
                                        group_key="f6d1ac6efee14b8d9a49d450030e551d").update(version="v5.1.8-release", status=3)

        updated = AppUpgradeRecord.objects.get(tenant_id="e4dd12842fdd4395815dd486cacf360d",
                                               group_id=240,
                                               group_key="f6d1ac6efee14b8d9a49d450030e551d")
        assert updated.version == "v5.1.8-release"
        assert updated.status == 3

        # 删除
        AppUpgradeRecord.objects.filter(tenant_id="e4dd12842fdd4395815dd486cacf360d",
                                        group_id=240,
                                        group_key="f6d1ac6efee14b8d9a49d450030e551d").delete()
        assert len(AppUpgradeRecord.objects.all()) == 0

    def test_service_upgrade_record(self):
        # 增加
        ServiceUpgradeRecord.objects.create(
            app_upgrade_record_id=1,
            service_id="b7992f6a242b48dab0783b0a8b49374b",
            service_cname="chinese name",
            upgrade_type="unknown",
            event_id="accfa9736f904d62940d4e033128c9ed",
            update='',
            status=1,
            update_time=now,
            create_time=now,
        ).save()

        # 查询
        all = ServiceUpgradeRecord.objects.all()
        assert len(all) == 1

        # 修改
        ServiceUpgradeRecord.objects.filter(app_upgrade_record_id=1).update(status=2)

        updated = ServiceUpgradeRecord.objects.get(app_upgrade_record_id=1)
        assert updated.status == 2

        # 删除
        ServiceUpgradeRecord.objects.filter(app_upgrade_record_id=1).delete()
        assert len(ServiceUpgradeRecord.objects.all()) == 0

    def test_region_info(self):
        # 增加
        RegionConfig.objects.create(
            region_id="asdasdasdasdasdasdasdasdas",
            region_name="rainbond",
            region_alias="rainbond",
            url="http://10.10.10.10:8888",
            wsurl="wss://wss-alish.goodrain.com:6060",
            httpdomain="0196bd.grapps.cn",
            tcpdomain="139.196.72.60",
            token="Token 5ca196801173be06c7e6ce41d5f7b3b8071e680a",
            status="1",
            create_time=now,
            desc="unknown describe info ",
            scope="private",
            ssl_ca_cert="dummy",
            cert_file="dummy",
            key_file="dummy",
        ).save()

        # 查询
        all = RegionConfig.objects.all()
        assert len(all) == 1

        # 修改
        RegionConfig.objects.filter(region_id="asdasdasdasdasdasdasdasdas").update(status="2", scope="publish")

        updated = RegionConfig.objects.get(region_id="asdasdasdasdasdasdasdasdas")
        assert updated.status == "2"
        assert updated.scope == "publish"

        # 删除
        RegionConfig.objects.filter(region_id="asdasdasdasdasdasdasdasdas").delete()
        assert len(RegionConfig.objects.all()) == 0

    def test_clound_bang_images(self):
        # 增加
        CloundBangImages.objects.create(
            identify="clound_bang_logo",
            logo="/data/media/logo/c954dc154dde49dfa6d4cf047ee778ea.png",
            create_time=now,
        ).save()

        # 查询
        all = CloundBangImages.objects.all()
        assert len(all) == 1

        # 修改
        CloundBangImages.objects.filter(identify="clound_bang_logo").update(
            logo="/data/media/logo/c954dc154dde49dfa6d4cf047ee778.png")

        updated = CloundBangImages.objects.get(identify="clound_bang_logo")
        assert updated.logo == "/data/media/logo/c954dc154dde49dfa6d4cf047ee778.png"

        # 删除
        CloundBangImages.objects.filter(identify="clound_bang_logo").delete()
        assert len(CloundBangImages.objects.all()) == 0

    def test_announcement(self):
        # 增加
        Announcement.objects.create(
            announcement_id="7ccf2ab053624ff3bf26778a24469fc1",
            content="chinese content",
            a_tag=None,
            a_tag_url=None,
            type=None,
            active=False,
            create_time=now,
            title="unkown title",
            level="mid",
        ).save()

        # 查询
        all = Announcement.objects.all()
        assert len(all) == 1

        # 修改
        Announcement.objects.filter(announcement_id="7ccf2ab053624ff3bf26778a24469fc1").update(level='low',
                                                                                               title="announcement")

        updated = Announcement.objects.get(announcement_id="7ccf2ab053624ff3bf26778a24469fc1")
        assert updated.level == 'low'
        assert updated.title == "announcement"

        # 删除
        Announcement.objects.filter(announcement_id="7ccf2ab053624ff3bf26778a24469fc1").delete()
        assert len(Announcement.objects.all()) == 0
