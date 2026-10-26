import importlib
import sys
import types
from datetime import datetime, timedelta, timezone
from unittest import TestCase, mock


class FakeCredentialConfig(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeCredentialClient(object):
    def __init__(self, config):
        self.config = config


class FakeOpenAPIConfig(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeAliyunClient(object):
    def __init__(self, config):
        self.config = config


class FakeSTSService(object):
    def __init__(self, responses):
        self.responses = list(responses)
        self.access_key = None
        self.access_secret = None
        self.calls = []

    def set_ak(self, value):
        self.access_key = value

    def set_sk(self, value):
        self.access_secret = value

    def assume_role(self, params):
        self.calls.append({
            "access_key": self.access_key,
            "access_secret": self.access_secret,
            "params": params,
        })
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def sts_response(access_key, access_secret, token, expiration):
    return {
        "Result": {
            "Credentials": {
                "AccessKeyId": access_key,
                "SecretAccessKey": access_secret,
                "SessionToken": token,
                "ExpiredTime": expiration.isoformat(),
            }
        }
    }


class SMSCredentialsTests(TestCase):
    def test_aliyun_legacy_config_uses_direct_access_key(self):
        from console.services.sms_credentials import create_aliyun_client

        client = create_aliyun_client(
            {
                "access_key": "source-ak",
                "access_secret": "source-sk",
            },
            client_class=FakeAliyunClient,
            openapi_config_class=FakeOpenAPIConfig,
            credential_client_class=FakeCredentialClient,
            credential_config_class=FakeCredentialConfig,
        )

        self.assertEqual("source-ak", client.config.kwargs["access_key_id"])
        self.assertEqual("source-sk", client.config.kwargs["access_key_secret"])
        self.assertNotIn("credential", client.config.kwargs)

    def test_aliyun_role_config_uses_ram_role_credential(self):
        from console.services.sms_credentials import create_aliyun_client

        client = create_aliyun_client(
            {
                "auth_type": "role",
                "access_key": "source-ak",
                "access_secret": "source-sk",
                "role_arn": "acs:ram::1234567890123456:role/sms-role",
            },
            client_class=FakeAliyunClient,
            openapi_config_class=FakeOpenAPIConfig,
            credential_client_class=FakeCredentialClient,
            credential_config_class=FakeCredentialConfig,
        )

        credential = client.config.kwargs["credential"]
        self.assertEqual("ram_role_arn", credential.config.kwargs["type"])
        self.assertEqual("source-ak", credential.config.kwargs["access_key_id"])
        self.assertEqual("source-sk", credential.config.kwargs["access_key_secret"])
        self.assertEqual(
            "acs:ram::1234567890123456:role/sms-role",
            credential.config.kwargs["role_arn"],
        )
        self.assertEqual("rainbond-console-sms", credential.config.kwargs["role_session_name"])
        self.assertNotIn("access_key_id", client.config.kwargs)

    def test_volcano_direct_credentials_have_no_session_token(self):
        from console.services.sms_credentials import VolcanoCredentialProvider

        provider = VolcanoCredentialProvider()
        credentials = provider.get_credentials({
            "auth_type": "access_key",
            "access_key": "direct-ak",
            "access_secret": "direct-sk",
        })

        self.assertEqual("direct-ak", credentials.access_key)
        self.assertEqual("direct-sk", credentials.access_secret)
        self.assertEqual("", credentials.session_token)

    def test_volcano_role_credentials_are_cached_until_refresh_window(self):
        from console.services.sms_credentials import VolcanoCredentialProvider

        now = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)
        clock = [now]
        sts = FakeSTSService([
            sts_response("temp-ak-1", "temp-sk-1", "token-1", now + timedelta(hours=1)),
        ])
        provider = VolcanoCredentialProvider(sts_service_factory=lambda: sts, now=lambda: clock[0])
        config = {
            "auth_type": "role",
            "access_key": "source-ak",
            "access_secret": "source-sk",
            "role_trn": "trn:iam::1234567890:role/sms-role",
        }

        first = provider.get_credentials(config)
        clock[0] = now + timedelta(minutes=30)
        second = provider.get_credentials(config)

        self.assertEqual("temp-ak-1", first.access_key)
        self.assertEqual("token-1", second.session_token)
        self.assertEqual(1, len(sts.calls))
        self.assertEqual("3600", sts.calls[0]["params"]["DurationSeconds"])
        self.assertEqual("rainbond-console-sms", sts.calls[0]["params"]["RoleSessionName"])

    def test_volcano_role_credentials_refresh_before_expiration(self):
        from console.services.sms_credentials import VolcanoCredentialProvider

        now = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)
        clock = [now]
        sts = FakeSTSService([
            sts_response("temp-ak-1", "temp-sk-1", "token-1", now + timedelta(hours=1)),
            sts_response("temp-ak-2", "temp-sk-2", "token-2", now + timedelta(hours=2)),
        ])
        provider = VolcanoCredentialProvider(sts_service_factory=lambda: sts, now=lambda: clock[0])
        config = {
            "auth_type": "role",
            "access_key": "source-ak",
            "access_secret": "source-sk",
            "role_trn": "trn:iam::1234567890:role/sms-role",
        }

        provider.get_credentials(config)
        clock[0] = now + timedelta(minutes=56)
        refreshed = provider.get_credentials(config)

        self.assertEqual("temp-ak-2", refreshed.access_key)
        self.assertEqual("token-2", refreshed.session_token)
        self.assertEqual(2, len(sts.calls))

    def test_volcano_role_cache_invalidates_when_source_secret_changes(self):
        from console.services.sms_credentials import VolcanoCredentialProvider

        now = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)
        sts = FakeSTSService([
            sts_response("temp-ak-1", "temp-sk-1", "token-1", now + timedelta(hours=1)),
            sts_response("temp-ak-2", "temp-sk-2", "token-2", now + timedelta(hours=1)),
        ])
        provider = VolcanoCredentialProvider(sts_service_factory=lambda: sts, now=lambda: now)
        config = {
            "auth_type": "role",
            "access_key": "source-ak",
            "access_secret": "source-sk-1",
            "role_trn": "trn:iam::1234567890:role/sms-role",
        }

        provider.get_credentials(config)
        config["access_secret"] = "source-sk-2"
        refreshed = provider.get_credentials(config)

        self.assertEqual("temp-ak-2", refreshed.access_key)
        self.assertEqual(2, len(sts.calls))

    def test_volcano_assume_role_failure_does_not_return_source_credentials(self):
        from console.services.sms_credentials import VolcanoCredentialProvider

        sts = FakeSTSService([RuntimeError("assume role denied")])
        provider = VolcanoCredentialProvider(sts_service_factory=lambda: sts)

        with self.assertRaises(RuntimeError):
            provider.get_credentials({
                "auth_type": "role",
                "access_key": "source-ak",
                "access_secret": "source-sk",
                "role_trn": "trn:iam::1234567890:role/sms-role",
            })


class FakeVolcanoSMSService(object):
    def __init__(self):
        self.access_key = None
        self.access_secret = None
        self.session_token = "stale-token"
        self.body = None

    def set_ak(self, value):
        self.access_key = value

    def set_sk(self, value):
        self.access_secret = value

    def set_session_token(self, value):
        self.session_token = value

    def send_sms(self, body):
        self.body = body
        return {"ResponseMetadata": {}}


class FakeCredentialProvider(object):
    def __init__(self, credentials):
        self.credentials = credentials

    def get_credentials(self, config):
        return self.credentials


class FakeAliyunSendClient(object):
    def __init__(self):
        self.request = None

    def send_sms(self, request):
        self.request = request
        return types.SimpleNamespace(body=types.SimpleNamespace(code="OK"))


class SMSProviderTests(TestCase):
    def tearDown(self):
        sys.modules.pop("console.services.sms_service", None)

    @staticmethod
    def import_sms_service():
        class FakeServiceHandleException(Exception):
            def __init__(self, msg=None, msg_show=None, status_code=None):
                super(FakeServiceHandleException, self).__init__(msg)
                self.msg = msg
                self.msg_show = msg_show
                self.status_code = status_code

        modules = {
            "console.models.main": types.SimpleNamespace(SMSVerificationCode=object),
            "console.repositories.enterprise_repo": types.SimpleNamespace(enterprise_repo=object()),
            "console.repositories.sms_repo": types.SimpleNamespace(sms_repo=object()),
            "console.exception.main": types.SimpleNamespace(ServiceHandleException=FakeServiceHandleException),
            "console.services.config_service": types.SimpleNamespace(EnterpriseConfigService=object),
        }
        with mock.patch.dict(sys.modules, modules):
            return importlib.import_module("console.services.sms_service")

    def test_direct_mode_clears_stale_session_token(self):
        module = self.import_sms_service()

        service = FakeVolcanoSMSService()
        provider = module.VolcanoSMSProvider(sms_service_factory=lambda: service)
        provider.send_sms("18800000000", "123456", {
            "auth_type": "access_key",
            "access_key": "direct-ak",
            "access_secret": "direct-sk",
            "sms_account": "sub-account",
            "sign_name": "approved-sign",
            "template_code": "template-id",
        })

        self.assertEqual("direct-ak", service.access_key)
        self.assertEqual("direct-sk", service.access_secret)
        self.assertEqual("", service.session_token)

    def test_role_mode_injects_temporary_credentials(self):
        from console.services.sms_credentials import SMSCredentials

        module = self.import_sms_service()
        service = FakeVolcanoSMSService()
        credentials = SMSCredentials("temp-ak", "temp-sk", "temp-token")
        provider = module.VolcanoSMSProvider(
            credential_provider=FakeCredentialProvider(credentials),
            sms_service_factory=lambda: service,
        )

        provider.send_sms("18800000000", "123456", {
            "auth_type": "role",
            "access_key": "source-ak",
            "access_secret": "source-sk",
            "role_trn": "trn:iam::1234567890:role/sms-role",
            "sms_account": "sub-account",
            "sign_name": "approved-sign",
            "template_code": "template-id",
        })

        self.assertEqual("temp-ak", service.access_key)
        self.assertEqual("temp-sk", service.access_secret)
        self.assertEqual("temp-token", service.session_token)

    def test_aliyun_send_request_keeps_sign_template_and_code(self):
        module = self.import_sms_service()
        client = FakeAliyunSendClient()
        provider = module.AliyunSMSProvider(client_factory=lambda config: client)

        provider.send_sms("18800000000", "123456", {
            "auth_type": "access_key",
            "access_key": "ak",
            "access_secret": "sk",
            "sign_name": "approved-sign",
            "template_code": "SMS_123",
        })

        self.assertEqual("18800000000", client.request.phone_numbers)
        self.assertEqual("approved-sign", client.request.sign_name)
        self.assertEqual("SMS_123", client.request.template_code)
        self.assertEqual('{"code":"123456"}', client.request.template_param)

    def test_sms_service_does_not_expose_provider_error_details(self):
        module = self.import_sms_service()

        class FailingProvider(object):
            def send_sms(self, phone, code, config):
                raise RuntimeError("provider diagnostic detail")

        module.sms_repo = types.SimpleNamespace(
            get_recent_code=lambda phone: None,
            count_today_codes=lambda phone: 0,
            create_verification=lambda *args: None,
        )
        module.enterprise_repo = types.SimpleNamespace(
            get_enterprise_first=lambda: types.SimpleNamespace(enterprise_id="eid"),
        )
        stored_config = types.SimpleNamespace(
            enable=True,
            value=str({
                "provider": "aliyun",
                "access_key": "ak",
                "access_secret": "sk",
                "sign_name": "sign",
                "template_code": "SMS_123",
            }),
        )
        module.EnterpriseConfigService = lambda *args, **kwargs: types.SimpleNamespace(
            get_config_by_key=lambda key: stored_config,
        )
        service = module.SMSService()
        service.providers["aliyun"] = FailingProvider()

        with mock.patch.object(module.logger, "exception"), \
                self.assertRaises(module.ServiceHandleException) as raised:
            service.send_verification_code("18800000000", "login")

        self.assertEqual("send sms failed", raised.exception.msg)
        self.assertNotIn("provider diagnostic detail", raised.exception.msg_show)
