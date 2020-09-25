# -*- coding: utf-8 -*-
import datetime

from django.test import TestCase

from django.db.models import Q

from www.models.main import WeChatConfig
from www.models.main import WeChatUser
from www.models.main import WeChatUnBind
from www.models.main import WeChatState
from www.models.main import SuperAdminUser
from www.models.main import Users
from www.models.main import Tenants
from www.models.main import TenantRegionInfo
from www.models.main import TenantRegionResource
from www.models.main import ServiceInfo
from www.models.main import TenantServiceInfoDelete
from www.models.main import TenantServiceLog
from www.models.main import TenantServiceRelation
from www.models.main import TenantServiceEnv
from www.models.main import TenantServiceAuth
from www.models.main import TenantServiceExtendMethod
from www.models.main import ServiceDomain
from www.models.main import ServiceDomainCertificate
from www.models.main import PermRelService
from www.models.main import PermRelTenant
from www.models.main import TenantRecharge
from www.models.main import TenantServiceStatics
from www.models.main import TenantConsumeDetail
from www.models.main import TenantConsume
from www.models.main import TenantFeeBill
from www.models.main import TenantPaymentNotify
from www.models.main import PhoneCode
from www.models.main import TenantRegionPayModel
from www.models.main import TenantServiceL7Info
from www.models.main import TenantServiceEnvVar
from www.models.main import TenantServicesPort
from www.models.main import TenantServiceMountRelation
from www.models.main import TenantServiceVolume
from www.models.main import TenantServiceConfigurationFile
from www.models.main import ServiceGroup
from www.models.main import ServiceGroupRelation
from www.models.main import ImageServiceRelation
from www.models.main import ServiceRule
from www.models.main import ComposeServiceRelation
from www.models.main import ServiceRuleHistory
from www.models.main import ServiceAttachInfo
from www.models.main import ServiceCreateStep
from www.models.main import ServiceFeeBill
from www.models.main import ServiceConsume
from www.models.main import ServiceEvent
from www.models.main import GroupCreateTemp
from www.models.main import BackServiceInstallTemp
from www.models.main import ServiceProbe
from www.models.main import ConsoleConfig
from www.models.main import TenantEnterprise
from www.models.main import TenantEnterpriseToken
from www.models.main import TenantServiceGroup
from www.models.main import ServiceTcpDomain
from www.models.main import ThirdPartyServiceEndpoints
from www.models.main import ServiceWebhooks
from www.models.main import GatewayCustomConfiguration
from www.models.main import TenantServiceInfo

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class WWWTest(TestCase):
    def test_wechat_config(self):
        # 增加
        WeChatConfig.objects.create(
            config="fanyangyang",
            app_id="wx1029384842029122",
            app_secret="8cb61669b82e4563bb447b2196bbfc09",
            token="goodrain",
            encrypt_mode="",
            encoding_aes_key="",
            access_token="""JFUmEVInAWvtZLMy8-xVrzFdkwndieeyfyRNkWMLhJ5Omotwcn9YevaK7YA9J
AGKzUrJgbKUQwAIumDggE00NAKz6IrVSxPindKMVqRhFCU8AOLHDaHclr-79pviCtKETqZKAcAAAJUK""",
            access_token_expires_at=1509654527,
            refresh_token="",
            app_type="web",
        ).save()

        # 查询
        all = WeChatConfig.objects.all()
        assert len(all) == 1

        # 修改
        WeChatConfig.objects.filter(config="fanyangyang").update(access_token="new token", access_token_expires_at=2019102822)

        updated = WeChatConfig.objects.get(config="fanyangyang")
        assert updated.access_token == "new token"
        assert updated.access_token_expires_at == 2019102822

        # 删除
        WeChatConfig.objects.filter(config="fanyangyang").delete()
        assert len(WeChatConfig.objects.all()) == 0

    def test_wechat_user_info(self):
        # 增加
        WeChatUser.objects.create(
            open_id="open_id_wx_useridsldkGidndksdnRKdDkner",
            nick_name="eSIDeNTD",
            sex=1,
            city="Fengtai",
            province="Beijing",
            country="CN",
            headimgurl="""http://wx.qlogo.cn/mmopen/sIT7V1VaXqNwvn6f4Bpkf1nYLu4SQHmDpX9djH8CZbXicun1
cWVibu0Ks5iaVThwfM2R2EMaZBFYFzQZqia0owEYwFGNrIAXibHCd/0""",
            union_id="di0ekdkdnfdslkdfsd",
            config="user",
        ).save()

        # 查询
        all = WeChatUser.objects.all()
        assert len(all) == 1

        # 修改
        WeChatUser.objects.filter(open_id="open_id_wx_useridsldkGidndksdnRKdDkner").update(union_id="1234567890", sex=2)

        updated = WeChatUser.objects.get(open_id="open_id_wx_useridsldkGidndksdnRKdDkner")
        assert updated.union_id == "1234567890"
        assert updated.sex == 2

        # 删除
        WeChatUser.objects.filter(open_id="open_id_wx_useridsldkGidndksdnRKdDkner").delete()
        assert len(WeChatUser.objects.all()) == 0

    def test_wechat_unbind(self):
        # 增加
        WeChatUnBind.objects.create(
            user_id=3492,
            union_id="zoqozddkendndkdke",
            status=0,
        ).save()

        # 查询
        all = WeChatUnBind.objects.all()
        assert len(all) == 1

        # 修改
        WeChatUnBind.objects.filter(user_id=3492).update(status=1)

        updated = WeChatUnBind.objects.get(user_id=3492)
        assert updated.status == 1

        # 删除
        WeChatUnBind.objects.filter(user_id=3492).delete()
        assert len(WeChatUnBind.objects.all()) == 0

    def test_wechat_state(self):
        # 增加
        WeChatState.objects.create(
            state="unkown state",
            create_time=now,
            update_time=now,
        ).save()

        # 查询
        all = WeChatState.objects.all()
        assert len(all) == 1

        # 修改
        WeChatState.objects.filter(ID=1).update(state="hahah")

        updated = WeChatState.objects.get(ID=1)
        assert updated.state == "hahah"

        # 删除
        WeChatState.objects.filter(ID=1).delete()
        assert len(WeChatState.objects.all()) == 0

    def test_user_administrator(self):
        # 增加
        SuperAdminUser.objects.create(
            user_id=1,
            email="goodrain",
        ).save()

        # 查询
        all = SuperAdminUser.objects.all()
        assert len(all) == 1

        filter = Q(user_id=1)

        # 修改
        SuperAdminUser.objects.filter(filter).update(email="dev@example.com")

        updated = SuperAdminUser.objects.get(filter)
        assert updated.email == "dev@example.com"

        # 删除
        SuperAdminUser.objects.filter(filter).delete()
        assert len(SuperAdminUser.objects.all()) == 0

    def test_user_info(self):
        # 增加
        Users.objects.create(
            user_id=1,
            email="admin@example.com",
            nick_name="admin",
            password="newpassword",
            phone=None,
            is_active=False,
            origion="invitation",
            create_time=now,
            git_user_id=0,
            github_token='',
            client_ip='',
            rf='',
            status=0,
            union_id='',
            sso_user_id="12838482828",
            sso_user_token="",
            enterprise_id="12838djdk23ndkdf923jdfnek23kd93",
        ).save()

        # 查询
        assert len(Users.objects.all()) == 1

        # 修改
        filter = Q(user_id=1)
        Users.objects.filter(filter).update(nick_name="dev", is_active=True, origion="rainbond", status=True)

        updated = Users.objects.get(filter)
        assert updated.nick_name == "dev"
        assert updated.is_active is True
        assert updated.origion == "rainbond"
        assert updated.status == 1

        # 删除
        Users.objects.filter(filter).delete()
        assert len(Users.objects.all()) == 0

    def test_tenant_info(self):
        # 增加
        Tenants.objects.create(
            tenant_id="a3b5a5912838485df888977b1784d2fa",
            tenant_name="5yu1iem6",
            region="rainbond",
            is_active=False,
            pay_type="free",
            balance=0,
            create_time=now,
            creater=1,
            limit_memory=4096,
            update_time=now,
            pay_level="company",
            expired_time=now,
            tenant_alias="abc",
            enterprise_id="daa5ed8b1e9747518f1c531bf3c12aca",
        ).save()

        # 查询
        assert len(Tenants.objects.all()) == 1

        # 修改

        filter = Q(tenant_id="a3b5a5912838485df888977b1784d2fa")
        Tenants.objects.filter(filter).update(is_active=True, limit_memory=2048, tenant_alias="testalias")

        updated = Tenants.objects.get(filter)
        assert updated.is_active is True
        assert updated.limit_memory == 2048
        assert updated.tenant_alias == "testalias"

        # 删除
        Tenants.objects.filter(filter).delete()
        assert len(Tenants.objects.all()) == 0

    def test_tenant_region(self):
        # 增加
        TenantRegionInfo.objects.create(
            tenant_id="a3b5a5912838485df888977b1784d2fa",
            region_name="rainbond",
            is_active=False,
            is_init=False,
            service_status=0,
            create_time=now,
            update_time=now,
            region_tenant_name="23ehgni5",
            region_tenant_id="cbd4c2dc46454631b2446e3d248d5e05",
            region_scope="private",
            enterprise_id="bf952b88382844d7adbd260af7b6296d",
        ).save()

        # 查询
        assert len(TenantRegionInfo.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="a3b5a5912838485df888977b1784d2fa")
        TenantRegionInfo.objects.filter(filter).update(is_active=True, is_init=True, service_status=1)

        updated = TenantRegionInfo.objects.get(filter)
        assert updated.is_active is True
        assert updated.is_init is True
        assert updated.service_status == 1

        # 删除
        TenantRegionInfo.objects.filter(filter).delete()
        assert len(TenantRegionInfo.objects.all()) == 0

    def test_tenant_region_resource(self):
        # 增加
        TenantRegionResource.objects.create(
            enterprise_id="bf952b88382844d7adbd260af7b6296d",
            tenant_id="a3b5a5912838485df888977b1784d2fa",
            region_name="rainbond",
            memory_limit=2048,
            memory_expire_date=now,
            disk_limit=40,
            disk_expire_date=now,
            net_limit=10,
            net_stock=10,
            create_time=now,
            update_time=now,
        ).save()

        # 查询
        assert len(TenantRegionResource.objects.all()) == 1

        # 修改
        filter = Q(enterprise_id="bf952b88382844d7adbd260af7b6296d", tenant_id="a3b5a5912838485df888977b1784d2fa")
        TenantRegionResource.objects.filter(filter).update(region_name="testname", memory_limit=4096)

        updated = TenantRegionResource.objects.get(filter)
        assert updated.region_name == "testname"
        assert updated.memory_limit == 4096

        # 删除
        TenantRegionResource.objects.filter(filter).delete()
        assert len(TenantRegionResource.objects.all()) == 0

    def test_service(self):
        # 增加
        ServiceInfo.objects.create(
            service_key="3d0d32121e5b444daf6310d728a6ba8f",
            publisher="dex@example.com",
            service_name="39skdn82d",
            pic=None,
            info=None,
            desc="this is describe about old service struct",
            status="1",
            category="application",
            is_service=False,
            is_web_service=False,
            version="v1.0",
            update_version=1,
            image="goodrain.me/nginx:20191029102938",
            namespace="12nd823",
            slug="",
            extend_method='',
            cmd="start web",
            setting=None,
            env=None,
            dependecy="",
            min_node=1,
            min_cpu=2,
            min_memory=512,
            inner_port=5000,
            publish_time=now,
            volume_mount_path="/",
            service_type="web",
            is_init_accout=False,
            creater=1,
            publish_type='',
        ).save()

        # 查询
        assert len(ServiceInfo.objects.all()) == 1

        # 修改
        filter = Q(service_key="3d0d32121e5b444daf6310d728a6ba8f")
        ServiceInfo.objects.filter(filter).update(service_type="mysql", min_node=2)

        updated = ServiceInfo.objects.get(filter)
        assert updated.service_type == "mysql"
        assert updated.min_node == 2

        # 删除
        ServiceInfo.objects.filter(filter).delete()
        assert len(ServiceInfo.objects.all()) == 0

    def test_tenant_service_delete(self):
        # 增加
        TenantServiceInfoDelete.objects.create(
            service_id="ac96eed7c78dcda7106bbcd63c78816a",
            tenant_id="3b1f4056edb2411cac3f993fde23a85f",
            service_key="2a2f86291bdb486594cf9a83d56e905d",
            service_alias="gr78816a",
            service_cname="2048",
            service_region="rainbond",
            desc="docker run application",
            category="app_publish",
            service_port=0,
            is_web_service=False,
            version="latest",
            update_version=1,
            image="nginx:1.11",
            cmd="start web",
            setting="",
            extend_method="stateless",
            env="",
            min_node=1,
            min_cpu=2,
            min_memory=512,
            inner_port=5000,
            volume_mount_path="",
            host_path="",
            deploy_version="20190218165008",
            code_from="gitlab_demo",
            git_url="http://code.goodrain.com/demo/2048.git",
            create_time=now,
            git_project_id=0,
            is_code_upload=False,
            code_version="master",
            service_type="application",
            delete_time=now,
            creater=1,
            language="Python",
            protocol="",
            total_memory=4096,
            is_service=False,
            namespace="goodrain",
            volume_type="share",
            port_type="multi_outer",
            service_origin="assistant",
            expired_time=now,
            service_source="source_code",
            create_status="complete",
            update_time=now,
            tenant_service_group_id=1,
            open_webhooks=False,
            check_uuid="368e2663-6a47-4c8f-8887-584d8bf974a2",
            check_event_id="55049d45e93f4afabab58531bcf9373d",
            docker_cmd=None,
            secret=None,
            server_type="state",
            is_upgrate=0,
            build_upgrade=False,
            service_name="",
        ).save()

        # 查询
        assert len(TenantServiceInfoDelete.objects.all()) == 1

        # 修改
        filter = Q(service_id="ac96eed7c78dcda7106bbcd63c78816a")
        TenantServiceInfoDelete.objects.filter(filter).update(deploy_version="2019102911432310")

        updated = TenantServiceInfoDelete.objects.get(filter)
        assert updated.deploy_version == "2019102911432310"

        # 删除
        TenantServiceInfoDelete.objects.filter(filter).delete()
        assert len(TenantServiceInfoDelete.objects.all()) == 0

    def test_tenant_service_log(self):
        # 增加
        TenantServiceLog.objects.create(
            user_id=1,
            user_name="gr78816a",
            service_id="b73e01d3b83546cc8d33d60a1618a79f",
            tenant_id="ac96eed7c78dcda7106bbcd63c78816a",
            action="start",
            create_time=now,
        ).save()

        # 查询
        assert len(TenantServiceLog.objects.all()) == 1

        # 修改
        filter = Q(ID=1)
        TenantServiceLog.objects.filter(filter).update(action="stop")

        updated = TenantServiceLog.objects.get(filter)
        assert updated.action == "stop"

        # 删除
        TenantServiceLog.objects.filter(filter).delete()
        assert len(TenantServiceLog.objects.all()) == 0

    def test_tenant_service_relation(self):
        # 增加
        TenantServiceRelation.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="3ceb45680e2e8b83197c56a05d7cdbaf",
            dep_service_id="85905961a178441cb49f96c7943ae2bf",
            dep_service_type="application",
            dep_order=0,
        ).save()

        # 查询
        assert len(TenantServiceRelation.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id="3ceb45680e2e8b83197c56a05d7cdbaf")
        TenantServiceRelation.objects.filter(filter).update(dep_service_id="2aab7a1728ce42a1a4ba820ad405420a")

        updated = TenantServiceRelation.objects.get(filter)
        assert updated.dep_service_id == "2aab7a1728ce42a1a4ba820ad405420a"

        # 删除
        TenantServiceRelation.objects.filter(filter).delete()
        assert len(TenantServiceRelation.objects.all()) == 0

    def test_tenant_service_env(self):
        # 增加
        TenantServiceEnv.objects.create(
            service_id="6c6457ff1050dcf924690644b50c6691",
            language="Python",
            check_dependency='{"procfile": true, "dependencies": true, "language": "static", "runtimes": false}',
            user_dependency="{}",
            create_time=now,
        ).save()

        # 查询
        assert len(TenantServiceEnv.objects.all()) == 1

        # 修改
        filter = Q(service_id="6c6457ff1050dcf924690644b50c6691")
        TenantServiceEnv.objects.filter(filter).update(
            user_dependency='{"procfile": "", "dependencies": {}, "language": "dockerfile", "runtimes": ""}')

        updated = TenantServiceEnv.objects.get(filter)
        assert updated.user_dependency == '{"procfile": "", "dependencies": {}, "language": "dockerfile", "runtimes": ""}'

        # 删除
        TenantServiceEnv.objects.filter(filter).delete()
        assert len(TenantServiceEnv.objects.all()) == 0

    def test_tenant_service_auth(self):
        # 增加
        TenantServiceAuth.objects.create(
            service_id="6c6457ff1050dcf924690644b50c6691",
            user="test123",
            password="fd5fe5a5",
            create_time=now,
        ).save()

        # 查询
        assert len(TenantServiceAuth.objects.all()) == 1

        # 修改
        filter = Q(service_id="6c6457ff1050dcf924690644b50c6691")
        TenantServiceAuth.objects.filter(filter).update(user=None, password=None)

        updated = TenantServiceAuth.objects.get(filter)
        assert updated.user is None
        assert updated.password is None

        # 删除
        TenantServiceAuth.objects.filter(filter).delete()
        assert len(TenantServiceAuth.objects.all()) == 0

    def test_tenant_service_extend_method(self):
        # 增加
        TenantServiceExtendMethod.objects.create(
            service_key="6c6457ff1050dcf924690644b50c6691",
            version="latest",
            min_node=1,
            max_node=5,
            step_node=1,
            min_memory=512,
            max_memory=5120,
            step_memory=1024,
            is_restart=False,
        ).save()

        # 查询
        assert len(TenantServiceExtendMethod.objects.all()) == 1

        # 修改
        filter = Q(service_key="6c6457ff1050dcf924690644b50c6691", version="latest")
        TenantServiceExtendMethod.objects.filter(filter).update(step_node=2, step_memory=2048)

        updated = TenantServiceExtendMethod.objects.get(filter)
        assert updated.step_node == 2
        assert updated.step_memory == 2048

        # 删除
        TenantServiceExtendMethod.objects.filter(filter).delete()
        assert len(TenantServiceExtendMethod.objects.all()) == 0

    def test_service_domain(self):
        # 增加
        ServiceDomain.objects.create(
            http_rule_id="64924007e66321802c8dd20df1f57854",
            region_id="asdasdasdasdasdasdasdasdas",
            tenant_id="b9662d34f1ec49a4b81c2d415f678af3",
            service_id="866cf9d9ed37b98e50581ee76a72d597",
            service_name="gr72d597",
            domain_name="5000.gr72d597.so53fcet.0196bd.grapps.cn",
            create_time=now,
            container_port=5000,
            protocol="http",
            certificate_id=0,
            domain_type="www",
            service_alias="leanote",
            is_senior=False,
            domain_path="/",
            domain_cookie="",
            domain_heander="",
            type=0,
            the_weight=100,
            rule_extensions="",
            is_outer_service=False,
        ).save()

        # 查询
        assert len(ServiceDomain.objects.all()) == 1

        # 修改
        filter = Q(http_rule_id="64924007e66321802c8dd20df1f57854")
        ServiceDomain.objects.filter(filter).update(is_outer_service=True, domain_path="/test")

        updated = ServiceDomain.objects.get(filter)
        assert updated.is_outer_service is True
        assert updated.domain_path == "/test"

        # 删除
        ServiceDomain.objects.filter(filter).delete()
        assert len(ServiceDomain.objects.all()) == 0

    def test_service_domain_certificate(self):
        # 增加
        ServiceDomainCertificate.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            certificate_id="62f2b326b28c486fbb0c4de575aa2fc1",
            private_key="----- Begin Private key ---***XXX**** ---End Private key----",
            certificate="tatatadatadededededada",
            certificate_type="unknown certificate type",
            create_time=now,
            alias="*.fanyangyang.top",
        ).save()

        # 查询
        assert len(ServiceDomainCertificate.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="e0090b27209c446e83313cd4e03e6d68", certificate_id="62f2b326b28c486fbb0c4de575aa2fc1")
        ServiceDomainCertificate.objects.filter(filter).update(
            certificate="LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUdNakNDQlJxZ0F3SUJBZ0lRQ")

        updated = ServiceDomainCertificate.objects.get(filter)
        assert updated.certificate == "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUdNakNDQlJxZ0F3SUJBZ0lRQ"

        # 删除
        ServiceDomainCertificate.objects.filter(filter).delete()
        assert len(ServiceDomainCertificate.objects.all()) == 0

    def test_service_perms(self):
        # 增加
        PermRelService.objects.create(
            user_id=1,
            service_id=1,
            identity="administrator",
            role_id=1,
        ).save()

        # 查询
        assert len(PermRelService.objects.all()) == 1

        # 修改
        filter = Q(user_id=1, service_id=1)
        PermRelService.objects.filter(filter).update(identity="developer", role_id=2)

        updated = PermRelService.objects.get(filter)
        assert updated.identity == "developer"
        assert updated.role_id == 2

        # 删除
        PermRelService.objects.filter(filter).delete()
        assert len(PermRelService.objects.all()) == 0

    def test_tenant_perms(self):
        # 增加
        PermRelTenant.objects.create(
            user_id=8441,
            tenant_id=3,
            identity="viwer",
            enterprise_id=1,
            role_id=None,
        ).save()

        # 查询
        assert len(PermRelTenant.objects.all()) == 1

        # 修改
        filter = Q(user_id=8441, tenant_id=3)
        PermRelTenant.objects.filter(filter).update(identity="developer", role_id=0)

        updated = PermRelTenant.objects.get(filter)
        assert updated.identity == "developer"
        assert updated.role_id == 0

        # 删除
        PermRelTenant.objects.filter(filter).delete()
        assert len(PermRelTenant.objects.all()) == 0

    def test_tenant_recharge(self):
        # 增加
        TenantRecharge.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            user_id=1,
            user_name="jackson",
            order_no="9102938238123",
            recharge_type="wechat?",
            money="50",
            subject="what subject?",
            body="i don't known anything about this",
            show_url="https://unknownlink.org",
            status="failed",
            trade_no="10283kd23nfsdj23ns03",
            time=now,
        ).save()

        # 查询
        assert len(TenantRecharge.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="e0090b27209c446e83313cd4e03e6d68", order_no="9102938238123")
        TenantRecharge.objects.filter(filter).update(status="success")

        updated = TenantRecharge.objects.get(filter)
        assert updated.status == "success"

        # 删除
        TenantRecharge.objects.filter(filter).delete()
        assert len(TenantRecharge.objects.all()) == 0

    def test_tenant_service_statics(self):
        # 增加
        TenantServiceStatics.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            service_id="866cf9d9ed37b98e50581ee76a72d597",
            pod_id="866cf9d9ed37b98e50581ee76a72d597",
            node_num=1,
            node_memory=2048,
            container_cpu=2,
            container_memory=1024,
            container_memory_working=512,
            pod_cpu=4,
            pod_memory=4096,
            pod_memory_working=2048,
            container_disk=1024,
            storage_disk=2048,
            net_in=10,
            net_out=5,
            flow=5,
            time_stamp=201910291,
            status=1,
            region="rainbond",
            time=now,
        ).save()

        # 查询
        assert len(TenantServiceStatics.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="e0090b27209c446e83313cd4e03e6d68", service_id="866cf9d9ed37b98e50581ee76a72d597")
        TenantServiceStatics.objects.filter(filter).update(status=2, flow=10)

        updated = TenantServiceStatics.objects.get(filter)
        assert updated.status == 2
        assert updated.flow == 10

        # 删除
        TenantServiceStatics.objects.filter(filter).delete()
        assert len(TenantServiceStatics.objects.all()) == 0

    def test_tenant_consume_detail(self):
        # 增加
        TenantConsumeDetail.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            service_id="866cf9d9ed37b98e50581ee76a72d597",
            service_alias="gr12ks81",
            node_num=2,
            cpu=4,
            memory=8192,
            disk=40,
            net=10,
            money=0,
            total_memory=8192,
            fee_rule="unknown",
            pay_status="failed",
            region="rainbond",
            status=0,
            time=now).save()

        # 查询
        assert len(TenantConsumeDetail.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="e0090b27209c446e83313cd4e03e6d68", service_id="866cf9d9ed37b98e50581ee76a72d597")
        TenantConsumeDetail.objects.filter(filter).update(status=1, pay_status="success")

        updated = TenantConsumeDetail.objects.get(filter)
        assert updated.status == 1
        assert updated.pay_status == "success"

        # 删除
        TenantConsumeDetail.objects.filter(filter).delete()
        assert len(TenantConsumeDetail.objects.all()) == 0

    def test_tenant_consume(self):
        # 增加
        TenantConsume.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            total_memory=4096,
            cost_money=100,
            payed_money=50,
            pay_status="failed",
            time=now,
        ).save()

        # 查询
        assert len(TenantConsume.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="e0090b27209c446e83313cd4e03e6d68")
        TenantConsume.objects.filter(filter).update(pay_status="success")

        updated = TenantConsume.objects.get(filter)
        assert updated.pay_status == "success"

        # 删除
        TenantConsume.objects.filter(filter).delete()
        assert len(TenantConsume.objects.all()) == 0

    def test_tenant_fee_bill(self):
        # 增加
        TenantFeeBill.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            bill_title="peple's republic of china",
            bill_type="check",
            bill_address="beijing china",
            bill_phone="18512034903",
            money=10,
            status="unapproved",
            time=now,
        ).save()

        # 查询
        assert len(TenantFeeBill.objects.all()) == 1

        # 修改
        filter = Q()
        TenantFeeBill.objects.filter(filter).update(status='approved')

        updated = TenantFeeBill.objects.get(filter)
        assert updated.status == 'approved'

        # 删除
        TenantFeeBill.objects.filter(filter).delete()
        assert len(TenantFeeBill.objects.all()) == 0

    def test_tenant_payment_notify(self):
        # 增加
        TenantPaymentNotify.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            notify_type="not enough",
            notify_content="your wallet is not enough for your continue use, please charge",
            send_person="jackson",
            time=now,
            status="valid",
        ).save()

        # 查询
        assert len(TenantPaymentNotify.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="e0090b27209c446e83313cd4e03e6d68")
        TenantPaymentNotify.objects.filter(filter).update(status="unvalid")

        updated = TenantPaymentNotify.objects.get(filter)
        assert updated.status == "unvalid"

        # 删除
        TenantPaymentNotify.objects.filter(filter).delete()
        assert len(TenantPaymentNotify.objects.all()) == 0

    def test_phone_code(self):
        # 增加
        PhoneCode.objects.create(
            phone="18612384921",
            type="regist",
            code="2039",
            message_id="201920192828",
            status=0,
            create_time=now,
        ).save()

        # 查询
        assert len(PhoneCode.objects.all()) == 1

        # 修改
        filter = Q(message_id="201920192828")
        PhoneCode.objects.filter(filter).update(status=1)

        updated = PhoneCode.objects.get(filter)
        assert updated.status == 1

        # 删除
        PhoneCode.objects.filter(filter).delete()
        assert len(PhoneCode.objects.all()) == 0

    def test_tenant_region_pay_model(self):
        # 增加
        TenantRegionPayModel.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            region_name="rainbond",
            pay_model="check",
            buy_period=10,
            buy_memory=100,
            buy_disk=20,
            buy_net=5,
            buy_start_time=now,
            buy_end_time=now,
            buy_money=20,
            create_time=now).save()

        # 查询
        assert len(TenantRegionPayModel.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="e0090b27209c446e83313cd4e03e6d68")
        TenantRegionPayModel.objects.filter(filter).update(buy_net=10)

        updated = TenantRegionPayModel.objects.get(filter)
        assert updated.buy_net == 10

        # 删除
        TenantRegionPayModel.objects.filter(filter).delete()
        assert len(TenantRegionPayModel.objects.all()) == 0

    def test_tenant_l7_info(self):
        # 增加
        TenantServiceL7Info.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            service_id="866cf9d9ed37b98e50581ee76a72d597",
            dep_service_id="",
            l7_json="{'key':'value'}",
        ).save()

        # 查询
        assert len(TenantServiceL7Info.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="e0090b27209c446e83313cd4e03e6d68", service_id="866cf9d9ed37b98e50581ee76a72d597")
        TenantServiceL7Info.objects.filter(filter).update(dep_service_id="8cb61669b82e4563bb447b2196bbfc09")

        updated = TenantServiceL7Info.objects.get(filter)
        assert updated.dep_service_id == "8cb61669b82e4563bb447b2196bbfc09"

        # 删除
        TenantServiceL7Info.objects.filter(filter).delete()
        assert len(TenantServiceL7Info.objects.all()) == 0

    def test_tenant_service_env_var(self):
        # 增加
        TenantServiceEnvVar.objects.create(
            tenant_id="e0090b27209c446e83313cd4e03e6d68",
            service_id="866cf9d9ed37b98e50581ee76a72d597",
            container_port=5000,
            name="BUILD_PROCFILE",
            attr_name="BUILD_PROCFILE",
            attr_value="web: java $JAVA_OPTS -jar target/java-maven-demo-0.0.1.jar",
            is_change=False,
            scope="builder",
            create_time=now,
        ).save()

        # 查询
        assert len(TenantServiceEnvVar.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="e0090b27209c446e83313cd4e03e6d68", service_id="866cf9d9ed37b98e50581ee76a72d597")
        TenantServiceEnvVar.objects.filter(filter).update(attr_value="27017", attr_name="MONGODB_PORT")

        updated = TenantServiceEnvVar.objects.get(filter)
        assert updated.attr_value == "27017"
        assert updated.attr_name == "MONGODB_PORT"

        # 删除
        TenantServiceEnvVar.objects.filter(filter).delete()
        assert len(TenantServiceEnvVar.objects.all()) == 0

    def test_tenant_services_port(self):
        # 增加
        TenantServicesPort.objects.create(
            tenant_id="b9662d34f1ec49a4b81c2d415f678af3",
            service_id="866cf9d9ed37b98e50581ee76a72d597",
            container_port=5000,
            mapping_port=5000,
            lb_mapping_port=10080,
            protocol="http",
            port_alias="GR72D5975000",
            is_inner_service=False,
            is_outer_service=True,
        ).save()

        # 查询
        assert len(TenantServicesPort.objects.all()) == 1

        # 修改
        filter = Q(
            tenant_id="b9662d34f1ec49a4b81c2d415f678af3", service_id="866cf9d9ed37b98e50581ee76a72d597", container_port=5000)
        TenantServicesPort.objects.filter(filter).update(is_inner_service=True, is_outer_service=False)

        updated = TenantServicesPort.objects.get(filter)
        assert updated.is_inner_service is True
        assert updated.is_outer_service is False

        # 删除
        TenantServicesPort.objects.filter(filter).delete()
        assert len(TenantServicesPort.objects.all()) == 0

    def test_tenant_service_mnt_relation(self):
        # 增加
        TenantServiceMountRelation.objects.create(
            tenant_id="4797d3ac8f8149e4904ee4f679723e49",
            service_id="4117899c6756be4f9bace8310192201a",
            dep_service_id="9216556f8c6242358a0ce760eaff6808",
            mnt_name="c3420f8",
            mnt_dir="/abc",
        ).save()

        # 查询
        assert len(TenantServiceMountRelation.objects.all()) == 1

        # 修改
        filter = Q(
            tenant_id="4797d3ac8f8149e4904ee4f679723e49",
            service_id="4117899c6756be4f9bace8310192201a",
            dep_service_id="9216556f8c6242358a0ce760eaff6808")
        TenantServiceMountRelation.objects.filter(filter).update(mnt_dir="/mnt/grda43201")

        updated = TenantServiceMountRelation.objects.get(filter)
        assert updated.mnt_dir == "/mnt/grda43201"

        # 删除
        TenantServiceMountRelation.objects.filter(filter).delete()
        assert len(TenantServiceMountRelation.objects.all()) == 0

    def test_tenant_service_volume(self):
        # 增加
        TenantServiceVolume.objects.create(
            service_id="85905961a178441cb49f96c7943ae2bf",
            category="application",
            host_path="/grdata/tenant/b73e01d3b83546cc8d33d60a1618a79f/service/add364a8f98c26f18bc8b7f8c954bf39/data",
            volume_type="share-file",
            volume_path="/var/lib/mysql",
            volume_name="GR7FE548_1",
        ).save()

        # 查询
        assert len(TenantServiceVolume.objects.all()) == 1

        # 修改
        filter = Q(service_id="85905961a178441cb49f96c7943ae2bf", volume_path="/var/lib/mysql")
        TenantServiceVolume.objects.filter(filter).update(volume_name="db")

        updated = TenantServiceVolume.objects.get(filter)
        assert updated.volume_name == "db"

        # 删除
        TenantServiceVolume.objects.filter(filter).delete()
        assert len(TenantServiceVolume.objects.all()) == 0

    def test_tenant_service_config(self):
        # 增加
        TenantServiceConfigurationFile.objects.create(
            service_id="ab9789311ed98aa1f444f6f94e9def80",
            volume_id=186,
            file_content="mysql_host=${MYSQL_HOST} \n mysql_port=${MYSQL_PORT}").save()

        # 查询
        assert len(TenantServiceConfigurationFile.objects.all()) == 1

        # 修改
        filter = Q(service_id="ab9789311ed98aa1f444f6f94e9def80", volume_id=186)
        TenantServiceConfigurationFile.objects.filter(filter).update(
            file_content="version: '3' \n services: \n nginx: \n images: 'nginx:1.11'")

        updated = TenantServiceConfigurationFile.objects.get(filter)
        assert updated.file_content == "version: '3' \n services: \n nginx: \n images: 'nginx:1.11'"

        # 删除
        TenantServiceConfigurationFile.objects.filter(filter).delete()
        assert len(TenantServiceConfigurationFile.objects.all()) == 0

    def test_service_group(self):
        # 增加
        ServiceGroup.objects.create(
            tenant_id="3b1f4056edb2411cac3f993fde23a85f",
            group_name="test dev ",
            region_name="region",
            is_default=False,
        ).save()

        # 查询
        assert len(ServiceGroup.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="3b1f4056edb2411cac3f993fde23a85f", group_name="test dev ")
        ServiceGroup.objects.filter(filter).update(region_name="rainbond", is_default=True)

        updated = ServiceGroup.objects.get(filter)
        assert updated.region_name == "rainbond"
        assert updated.is_default is True

        # 删除
        ServiceGroup.objects.filter(filter).delete()
        assert len(ServiceGroup.objects.all()) == 0

    def test_service_group_relation(self):
        # 增加
        ServiceGroupRelation.objects.create(
            service_id="2aab7a1728ce42a1a4ba820ad405420a",
            group_id=2,
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            region_name="rainbond").save()

        # 查询
        assert len(ServiceGroupRelation.objects.all()) == 1

        # 修改
        filter = Q(service_id="2aab7a1728ce42a1a4ba820ad405420a", group_id=2)
        ServiceGroupRelation.objects.filter(filter).update(region_name="test region")

        updated = ServiceGroupRelation.objects.get(filter)
        assert updated.region_name == "test region"

        # 删除
        ServiceGroupRelation.objects.filter(filter).delete()
        assert len(ServiceGroupRelation.objects.all()) == 0

    def test_tenant_service_image_relation(self):
        # 增加
        ImageServiceRelation.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id='2aab7a1728ce42a1a4ba820ad405420a',
            image_url='goodrain.me/nginx',
            service_cname='nginx').save()

        # 查询
        assert len(ImageServiceRelation.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id='2aab7a1728ce42a1a4ba820ad405420a')
        ImageServiceRelation.objects.filter(filter).update(image_url="goodrain.me/envoy", service_cname="service mesh envoy")

        updated = ImageServiceRelation.objects.get(filter)
        assert updated.image_url == "goodrain.me/envoy"
        assert updated.service_cname == "service mesh envoy"

        # 删除
        ImageServiceRelation.objects.filter(filter).delete()
        assert len(ImageServiceRelation.objects.all()) == 0

    def test_tenant_compose_file(self):
        # 增加
        ComposeServiceRelation.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            compose_file_id="4f6ad5fbb2f844d7b1ba12df520c15a7",
            compose_file="version: '3' services: nginx: image: nginx",
        ).save()

        #  查询
        assert len(ComposeServiceRelation.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", compose_file_id="4f6ad5fbb2f844d7b1ba12df520c15a7")
        ComposeServiceRelation.objects.filter(filter).update(compose_file="version: '3' \n services: \n nginx: \n image: nginx")

        updated = ComposeServiceRelation.objects.get(filter)
        assert updated.compose_file == "version: '3' \n services: \n nginx: \n image: nginx"

        # 删除
        ComposeServiceRelation.objects.filter(filter).delete()
        assert len(ComposeServiceRelation.objects.all()) == 0

    def test_tenant_service_rule(self):
        # 增加
        ServiceRule.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            tenant_name="gr12nd92",
            service_id="2aab7a1728ce42a1a4ba820ad405420a",
            service_alias="nginx",
            service_region="rainbond",
            item="what",
            maxvalue=100,
            minvalue=10,
            status=False,
            count=0,
            node_number=1,
            port=5000,
            port_type="multi_outer",
        ).save()

        # 查询
        assert len(ServiceRule.objects.all()) == 1

        # 修改
        filter = Q(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f", tenant_name="gr12nd92", service_id="2aab7a1728ce42a1a4ba820ad405420a")
        ServiceRule.objects.filter(filter).update(port_type="one_outer", port="80", status=True)

        updated = ServiceRule.objects.get(filter)
        assert updated.port_type == "one_outer"
        assert updated.port == "80"
        assert updated.status is True

        # 删除
        ServiceRule.objects.filter(filter).delete()
        assert len(ServiceRule.objects.all()) == 0

    def test_tenant_service_rule_history(self):
        # 增加
        ServiceRuleHistory.objects.create(
            rule_id="2aab7a1728ce42a1a4ba820ad405420a",
            trigger_time=now,
            action="upvolume",
            message="upvolume failed",
        ).save()

        # 查询
        assert len(ServiceRuleHistory.objects.all()) == 1

        # 修改
        filter = Q(rule_id="2aab7a1728ce42a1a4ba820ad405420a")
        ServiceRuleHistory.objects.filter(filter).update(action="up-disk", message="up-disk success")

        updated = ServiceRuleHistory.objects.get(filter)
        assert updated.action == "up-disk"
        assert updated.message == "up-disk success"

        # 删除
        ServiceRuleHistory.objects.filter(filter).delete()
        assert len(ServiceRuleHistory.objects.all()) == 0

    def test_service_attach_info(self):
        # 增加
        ServiceAttachInfo.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="2aab7a1728ce42a1a4ba820ad405420a",
            memory_pay_method="month",
            disk_pay_method="day",
            min_memory=2048,
            min_node=2,
            disk=40,
            pre_paid_period=20,
            pre_paid_money=400,
            buy_start_time=now,
            buy_end_time=now,
            create_time=now,
            region="region",
        ).save()

        # 查询
        assert len(ServiceAttachInfo.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id="2aab7a1728ce42a1a4ba820ad405420a")
        ServiceAttachInfo.objects.filter(filter).update(region="test dev")

        updated = ServiceAttachInfo.objects.get(filter)
        assert updated.region == 'test dev'

        # 删除
        ServiceAttachInfo.objects.filter(filter).delete()
        assert len(ServiceAttachInfo.objects.all()) == 0

    def test_service_create_step(self):
        # 增加
        ServiceCreateStep.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id="2aab7a1728ce42a1a4ba820ad405420a", app_step=5).save()

        # 查询
        assert len(ServiceCreateStep.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id="2aab7a1728ce42a1a4ba820ad405420a")
        ServiceCreateStep.objects.filter(filter).update(app_step=4)

        updated = ServiceCreateStep.objects.get(filter)
        assert updated.app_step == 4

        # 删除
        ServiceCreateStep.objects.filter(filter).delete()
        assert len(ServiceCreateStep.objects.all()) == 0

    def test_third_app_info(self):
        # 增加
        ThirdAppInfo.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="2aab7a1728ce42a1a4ba820ad405420a",
            bucket_name="bucket_name",
            app_type="mysql",
            create_time=now,
            name="mysql3",
            bill_type="demand",
            open=False,
            delete=False,
            create_user=1,
        ).save()

        # 查询
        assert len(ThirdAppInfo.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id="2aab7a1728ce42a1a4ba820ad405420a")
        ThirdAppInfo.objects.filter(filter).update(open=True, name="thirdpart-mysql")

        updated = ThirdAppInfo.objects.get(filter)
        assert updated.open is True
        assert updated.name == "thirdpart-mysql"

        # 删除
        ThirdAppInfo.objects.filter(filter).delete()
        assert len(ThirdAppInfo.objects.all()) == 0

    def test_cdn_traffic_hour_record(self):
        # 增加
        CDNTrafficHourRecord.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="2aab7a1728ce42a1a4ba820ad405420a",
            bucket_name="bucket_name",
            start_time=now,
            end_time=now,
            traffic_number=1024,
            balance=10,
            create_time=now,
            order_id="1dk2nd9123nd910sm3832d01k8d34dn1",
        ).save()

        # 查询
        assert len(CDNTrafficHourRecord.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id="2aab7a1728ce42a1a4ba820ad405420a")
        CDNTrafficHourRecord.objects.filter(filter).update(traffic_number=2048)

        updated = CDNTrafficHourRecord.objects.get(filter)
        assert updated.traffic_number == 2048

        # 删除
        CDNTrafficHourRecord.objects.filter(filter).delete()
        assert len(CDNTrafficHourRecord.objects.all()) == 0

    def test_third_app_operator(self):
        # 增加
        ThirdAppOperator.objects.create(
            service_id="2aab7a1728ce42a1a4ba820ad405420a",
            bucket_name="bucket_name",
            operator_name="post",
            real_name="whoareyou",
            password="123123123",
        ).save()

        # 查询
        assert len(ThirdAppOperator.objects.all()) == 1

        # 修改
        filter = Q(service_id="2aab7a1728ce42a1a4ba820ad405420a")
        ThirdAppOperator.objects.filter(filter).update(real_name="jackson", password="321321312")

        updated = ThirdAppOperator.objects.get(filter)
        assert updated.real_name == "jackson"
        assert updated.password == "321321312"

        # 删除
        ThirdAppOperator.objects.filter(filter).delete()
        assert len(ThirdAppOperator.objects.all()) == 0

    def test_third_app_order(self):
        # 增加
        ThirdAppOrder.objects.create(
            order_id="20191029383812",
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="2aab7a1728ce42a1a4ba820ad405420a",
            bucket_name="bucket_name",
            start_time=now,
            end_time=now,
            create_time=now,
            traffic_size=1024,
            oos_size=10,
            request_size=20,
            bill_type="cash",
            total_cost=100,
            total_traffic_cost=200,
        ).save()

        # 查询
        assert len(ThirdAppOrder.objects.all()) == 1

        # 修改
        filter = Q(order_id="20191029383812")
        ThirdAppOrder.objects.filter(filter).update(bill_type="packet")

        updated = ThirdAppOrder.objects.get(filter)
        assert updated.bill_type == "packet"

        # 删除
        ThirdAppOrder.objects.filter(filter).delete()
        assert len(ThirdAppOrder.objects.all()) == 0

    def test_service_fee_bill(self):
        # 增加
        ServiceFeeBill.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="2aab7a1728ce42a1a4ba820ad405420a",
            prepaid_money=100,
            pay_status="failed",
            cost_type="cash",
            node_memory=2048,
            node_num=1,
            disk=40,
            buy_period=40,
            create_time=now,
            pay_time=now,
        ).save()

        # 查询
        assert len(ServiceFeeBill.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id="2aab7a1728ce42a1a4ba820ad405420a")
        ServiceFeeBill.objects.filter(filter).update(buy_period=48)

        updated = ServiceFeeBill.objects.get(filter)
        assert updated.buy_period == 48

        # 删除
        ServiceFeeBill.objects.filter(filter).delete()
        assert len(ServiceFeeBill.objects.all()) == 0

    def test_service_consume(self):
        # 增加
        ServiceConsume.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="2aab7a1728ce42a1a4ba820ad405420a",
            memory=2048,
            node_num=1,
            disk=40,
            net=5,
            memory_money=100,
            disk_money=200,
            net_money=300,
            pay_money=500,
            pay_status="failed",
            region="rainbond",
            status=0,
            time=now,
            real_memory_money=500,
            real_disk_money=400,
        ).save()

        # 查询
        assert len(ServiceConsume.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id="2aab7a1728ce42a1a4ba820ad405420a")
        ServiceConsume.objects.filter(filter).update(status=1)

        updated = ServiceConsume.objects.get(filter)
        assert updated.status == 1

        # 删除
        ServiceConsume.objects.filter(filter).delete()
        assert len(ServiceConsume.objects.all()) == 0

    def test_service_event(self):
        # 增加
        ServiceEvent.objects.create(
            event_id="036cbcac600746f4aceea26d8c2f03c9",
            tenant_id="3b1f4056edb2411cac3f993fde23a85f",
            service_id="b0baf29788500c429a242185605f8cf6",
            user_name="mailbox",
            start_time=now,
            end_time=now,
            type='deploy',
            status="success",
            final_status="complete",
            message="2048",
            deploy_version="20190218165008",
            old_deploy_version="",
            code_version="72a82ad",
            old_code_version="",
            region="rainbond",
        ).save()

        # 查询
        assert len(ServiceEvent.objects.all()) == 1

        # 修改
        filter = Q(event_id="036cbcac600746f4aceea26d8c2f03c9")
        ServiceEvent.objects.filter(filter).update(status="timeout")

        updated = ServiceEvent.objects.get(filter)
        assert updated.status == "timeout"

        # 删除
        ServiceEvent.objects.filter(filter).delete()
        assert len(ServiceEvent.objects.all()) == 0

    def test_group_create_temp(self):
        # 增加
        GroupCreateTemp.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_id="b0baf29788500c429a242185605f8cf6",
            service_key="b0baf29788500c429a242185605f8cf6",
            share_group_id=1,
            service_group_id=1,
            service_cname="nginx",
        ).save()

        # 查询
        assert len(GroupCreateTemp.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", service_id="b0baf29788500c429a242185605f8cf6")
        GroupCreateTemp.objects.filter(filter).update(service_cname="2048")

        updated = GroupCreateTemp.objects.get(filter)
        assert updated.service_cname == "2048"

        # 删除
        GroupCreateTemp.objects.filter(filter).delete()
        assert len(GroupCreateTemp.objects.all()) == 0

    def test_back_service_install_temp(self):
        # 增加
        BackServiceInstallTemp.objects.create(
            group_share_id="123qwe34d9fn23",
            share_pk=1,
            group_pk=2,
            success=False,
        ).save()

        # 查询
        assert len(BackServiceInstallTemp.objects.all()) == 1

        # 修改
        filter = Q(group_share_id="123qwe34d9fn23", share_pk=1, group_pk=2)
        BackServiceInstallTemp.objects.filter(filter).update(success=True)

        updated = BackServiceInstallTemp.objects.get(filter)
        assert updated.success is True

        # 删除
        BackServiceInstallTemp.objects.filter(filter).delete()
        assert len(BackServiceInstallTemp.objects.all()) == 0

    def test_service_probe(self):
        # 增加
        ServiceProbe.objects.create(
            service_id="98744641a3577d58529b4602337d4b05",
            probe_id="149392f85c30442b9e2009f8d4fade3a",
            mode="readiness",
            scheme="tcp",
            path="",
            port=80,
            cmd="",
            http_header="",
            initial_delay_second=2,
            period_second=3,
            timeout_second=30,
            failure_threshold=3,
            success_threshold=1,
            is_used=False,
        ).save()

        # 查询
        assert len(ServiceProbe.objects.all()) == 1

        # 修改
        filter = Q(service_id="98744641a3577d58529b4602337d4b05", probe_id="149392f85c30442b9e2009f8d4fade3a")
        ServiceProbe.objects.filter(filter).update(is_used=True, failure_threshold=1)

        updated = ServiceProbe.objects.get(filter)
        assert updated.is_used is True
        assert updated.failure_threshold == 1

        # 删除
        ServiceProbe.objects.filter(filter).delete()
        assert len(ServiceProbe.objects.all()) == 0

    def test_console_config(self):
        # 增加
        ConsoleConfig.objects.create(
            key="config-logo",
            value="/images/logo.img",
            description="web logo",
            update_time=now,
        ).save()

        # 查询
        assert len(ConsoleConfig.objects.all()) == 1

        # 修改
        filter = Q(key="config-logo")
        ConsoleConfig.objects.filter(filter).update(value="/data/images/logo.png")

        updated = ConsoleConfig.objects.get(filter)
        assert updated.value == "/data/images/logo.png"

        # 删除
        ConsoleConfig.objects.filter(filter).delete()
        assert len(ConsoleConfig.objects.all()) == 0

    def test_service_payment_notify(self):
        # 增加
        TenantEnterprise.objects.create(
            enterprise_id="b44871d051ed41e9ab9defea40d4e21d",
            enterprise_name="testname",
            enterprise_alias="enteralias",
            create_time=now,
            enterprise_token="57b24b68d50bf37e850c4fac9c552c0e",
            is_active=0,
        ).save()

        # 查询
        assert len(TenantEnterprise.objects.all()) == 1

        # 修改
        filter = Q(enterprise_id="b44871d051ed41e9ab9defea40d4e21d")
        TenantEnterprise.objects.filter(filter).update(
            enterprise_alias="fanyangyang", enterprise_token="219da0fbc4681fd16f32c7e5431c96ea", is_active=1)

        updated = TenantEnterprise.objects.get(filter)
        assert updated.enterprise_alias == "fanyangyang"
        assert updated.enterprise_token == "219da0fbc4681fd16f32c7e5431c96ea"
        assert updated.is_active == 1

        # 删除
        TenantEnterprise.objects.filter(filter).delete()
        assert len(TenantEnterprise.objects.all()) == 0

    def test_tenant_enterprise_token(self):
        # 增加
        TenantEnterpriseToken.objects.create(
            enterprise_id=102,
            access_target='goodrain.me',
            access_url="https://goodrain.me:443",
            access_id="2ed88eb6b2b64fa79b9699af459eb3a6",
            access_token="a9293764854f4d65b56cbd1761936d98",
            crt=None,
            key=None,
            create_time=now,
            update_time=now,
        ).save()

        # 查询
        assert len(TenantEnterpriseToken.objects.all()) == 1

        # 修改
        filter = Q(enterprise_id=102)
        TenantEnterpriseToken.objects.filter(filter).update(access_token="2b4ddb679054cf117748803881b6121c")

        updated = TenantEnterpriseToken.objects.get(filter)
        assert updated.access_token == "2b4ddb679054cf117748803881b6121c"

        # 删除
        TenantEnterpriseToken.objects.filter(filter).delete()
        assert len(TenantEnterpriseToken.objects.all()) == 0

    def test_tenant_service_group(self):
        # 增加
        TenantServiceGroup.objects.create(
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            group_name="gr_7fe7",
            group_alias="nginx",
            group_key="memcached",
            group_version="1.4.24",
            region_name="rainbond",
            service_group_id=33,
        ).save()

        # 查询
        assert len(TenantServiceGroup.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="b73e01d3b83546cc8d33d60a1618a79f", group_name="gr_7fe7")
        TenantServiceGroup.objects.filter(filter).update(group_version="2.0")

        updated = TenantServiceGroup.objects.get(filter)
        assert updated.group_version == "2.0"

        # 删除
        TenantServiceGroup.objects.filter(filter).delete()
        assert len(TenantServiceGroup.objects.all()) == 0

    def test_service_tcp_domain(self):
        # 增加
        ServiceTcpDomain.objects.create(
            tcp_rule_id="98f8f6b5ff5967e747857a05083b9123",
            region_id="asdasdasdasdasdasdasdasdas",
            tenant_id="237e21d1c7654e9bb58e3139b964ce86",
            service_id="ec20cb954c4b4e64b3b295cc17c07b5e",
            service_name="gr37ea94",
            end_point="127.0.0.1:3290",
            create_time=now,
            protocol="http",
            container_port=5000,
            service_alias="2048",
            type=0,
            rule_extensions=None,
            is_outer_service=False,
        ).save()

        # 查询
        assert len(ServiceTcpDomain.objects.all()) == 1

        # 修改
        filter = Q(tcp_rule_id="98f8f6b5ff5967e747857a05083b9123")
        ServiceTcpDomain.objects.filter(filter).update(is_outer_service=True, protocol='stream', end_point="127.0.0.1:3309")

        updated = ServiceTcpDomain.objects.get(filter)
        assert updated.is_outer_service is True
        assert updated.protocol == 'stream'
        assert updated.end_point == "127.0.0.1:3309"

        # 删除
        ServiceTcpDomain.objects.filter(filter).delete()
        assert len(ServiceTcpDomain.objects.all()) == 0

    def test_third_party_service_endpoints(self):
        # 增加
        ThirdPartyServiceEndpoints.objects.create(
            tenant_id="4f6ad5fbb2f844d7b1ba12df520c15a7",
            service_id="de2bca6d5089d2274aba882c08038429",
            service_cname="hubservice",
            endpoints_info='["10.10.10.10:5000"]',
            endpoints_type="static",
        ).save()

        # 查询
        assert len(ThirdPartyServiceEndpoints.objects.all()) == 1

        # 修改
        filter = Q(tenant_id="4f6ad5fbb2f844d7b1ba12df520c15a7", service_id="de2bca6d5089d2274aba882c08038429")
        ThirdPartyServiceEndpoints.objects.filter(filter).update(endpoints_info='["192.168.2.182:5000"]')

        updated = ThirdPartyServiceEndpoints.objects.get(filter)
        assert updated.endpoints_info == '["192.168.2.182:5000"]'

        # 删除
        ThirdPartyServiceEndpoints.objects.filter(filter).delete()
        assert len(ThirdPartyServiceEndpoints.objects.all()) == 0

    def test_service_webhooks(self):
        # 增加
        ServiceWebhooks.objects.create(
            service_id="b6098f52dabe91244f3d9d908073506c",
            state=False,
            webhooks_type='code_Webhooks',
            deploy_keyword="deploy",
            trigger="",
        ).save()

        # 查询
        assert len(ServiceWebhooks.objects.all()) == 1

        # 修改
        filter = Q(service_id="b6098f52dabe91244f3d9d908073506c")
        ServiceWebhooks.objects.filter(filter).update(deploy_keyword="update")

        updated = ServiceWebhooks.objects.get(filter)
        assert updated.deploy_keyword == "update"

        # 删除
        ServiceWebhooks.objects.filter(filter).delete()
        assert len(ServiceWebhooks.objects.all()) == 0

    def test_gateway_custom_configuration(self):
        # 增加
        GatewayCustomConfiguration.objects.create(
            rule_id="7243e80f1cf4edb242777cfc96f4f3d3",
            value="""{"set_headers": [], "proxy_read_timeout": 60, "proxy_body_size": 1024,
"proxy_send_timeout": 60, "proxy_connect_timeout": 75}""",
        ).save()

        # 查询
        assert len(GatewayCustomConfiguration.objects.all()) == 1

        # 修改
        filter = Q(rule_id="7243e80f1cf4edb242777cfc96f4f3d3")
        GatewayCustomConfiguration.objects.filter(filter).update(
            value="""{"set_headers": [{"value": "bar", "key": "foo"}], "proxy_read_timeout": 60,
"proxy_body_size": 0, "proxy_send_timeout": 60, "proxy_connect_timeout": 75}""")

        updated = GatewayCustomConfiguration.objects.get(filter)
        assert updated.value == """{"set_headers": [{"value": "bar", "key": "foo"}], "proxy_read_timeout": 60,
"proxy_body_size": 0, "proxy_send_timeout": 60, "proxy_connect_timeout": 75}"""

        # 删除
        GatewayCustomConfiguration.objects.filter(filter).delete()
        assert len(GatewayCustomConfiguration.objects.all()) == 0

    def test_tenant_service(self):
        # 增加
        TenantServiceInfo.objects.create(
            service_id="b0baf29788500c429a242185605f8cf6",
            tenant_id="b73e01d3b83546cc8d33d60a1618a79f",
            service_key="3936a406ccdf4b55ad747be3ce1cb21f",
            service_alias="gr5f8cf6",
            service_cname="unknown chinese name",
            service_region="rainbond",
            desc="application info ",
            category="application",
            service_port=0,
            is_web_service=False,
            version="v1.0",
            update_version=1,
            image="goodrain.me/nginx:latest",
            cmd="start web",
            setting="",
            extend_method='stateless',
            env="",
            min_node=1,
            min_cpu=2,
            min_memory=2048,
            inner_port=5000,
            volume_mount_path="",
            host_path="",
            deploy_version="20190330184526",
            code_from="gitlab_manual",
            git_url="https://github.com/unknown/go.git",
            create_time=now,
            git_project_id=1,
            is_code_upload=False,
            code_version="master",
            service_type="application",
            creater=1,
            language="dockerfile",
            protocol="",
            total_memory=4096,
            is_service=False,
            namespace="goodrain",
            volume_type="shared",
            port_type="multi_outer",
            service_origin="assistant",
            expired_time=None,
            tenant_service_group_id=1,
            open_webhooks=False,
            # service_source = "source_code",
            create_status="complete",
            update_time=now,
            check_uuid="3e69980d-3b34-44f0-939e-97a0d42af256",
            check_event_id="1cc6297cb053440f8e7934d122e54658",
            docker_cmd=None,
            secret=None,
            server_type="git",
            is_upgrate=False,
            build_upgrade=True,
            service_name="",
        ).save()

        # 查询
        assert len(TenantServiceInfo.objects.all()) == 1

        # 修改
        filter = Q(service_id="b0baf29788500c429a242185605f8cf6")
        TenantServiceInfo.objects.filter(filter).update(service_name="unknown application name", total_memory=2048)

        updated = TenantServiceInfo.objects.get(filter)
        assert updated.service_name == "unknown application name"
        assert updated.total_memory == 2048

        # 删除
        TenantServiceInfo.objects.filter(filter).delete()
        assert len(TenantServiceInfo.objects.all()) == 0
