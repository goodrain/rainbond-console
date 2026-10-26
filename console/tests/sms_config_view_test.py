from unittest import TestCase


class SMSConfigValidationTests(TestCase):
    def test_parser_rejects_executable_expressions(self):
        from console.services.sms_config import SMSConfigValidationError, parse_sms_config

        with self.assertRaises(SMSConfigValidationError):
            parse_sms_config("__import__('os').system('false')")

    def test_legacy_aliyun_config_defaults_to_access_key(self):
        from console.services.sms_config import normalize_sms_config

        config = normalize_sms_config({
            "provider": "aliyun",
            "access_key": "ak",
            "access_secret": "sk",
            "sign_name": "sign",
            "template_code": "SMS_123",
        })

        self.assertEqual("access_key", config["auth_type"])
        self.assertEqual("", config["role_arn"])

    def test_aliyun_role_requires_valid_role_arn(self):
        from console.services.sms_config import SMSConfigValidationError, normalize_sms_config

        with self.assertRaises(SMSConfigValidationError):
            normalize_sms_config({
                "provider": "aliyun",
                "auth_type": "role",
                "access_key": "ak",
                "access_secret": "sk",
                "role_arn": "invalid-role",
                "sign_name": "sign",
                "template_code": "SMS_123",
            })

    def test_aliyun_role_accepts_role_arn(self):
        from console.services.sms_config import normalize_sms_config

        config = normalize_sms_config({
            "provider": "aliyun",
            "auth_type": "role",
            "access_key": "ak",
            "access_secret": "sk",
            "role_arn": "acs:ram::1234567890123456:role/sms-role",
            "sign_name": "sign",
            "template_code": "SMS_123",
        })

        self.assertEqual("role", config["auth_type"])

    def test_volcano_direct_requires_sms_account(self):
        from console.services.sms_config import SMSConfigValidationError, normalize_sms_config

        with self.assertRaises(SMSConfigValidationError):
            normalize_sms_config({
                "provider": "volcano",
                "auth_type": "access_key",
                "access_key": "ak",
                "access_secret": "sk",
                "sign_name": "sign",
                "template_code": "template-id",
            })

    def test_volcano_direct_accepts_sms_account(self):
        from console.services.sms_config import normalize_sms_config

        config = normalize_sms_config({
            "provider": "volcano",
            "auth_type": "access_key",
            "access_key": "ak",
            "access_secret": "sk",
            "sms_account": "sub-account",
            "sign_name": "sign",
            "template_code": "template-id",
        })

        self.assertEqual("access_key", config["auth_type"])

    def test_volcano_role_requires_valid_role_trn(self):
        from console.services.sms_config import SMSConfigValidationError, normalize_sms_config

        with self.assertRaises(SMSConfigValidationError):
            normalize_sms_config({
                "provider": "volcano",
                "auth_type": "role",
                "access_key": "ak",
                "access_secret": "sk",
                "role_trn": "invalid-role",
                "sms_account": "sub-account",
                "sign_name": "sign",
                "template_code": "template-id",
            })

    def test_volcano_role_accepts_role_trn(self):
        from console.services.sms_config import normalize_sms_config

        config = normalize_sms_config({
            "provider": "volcano",
            "auth_type": "role",
            "access_key": "ak",
            "access_secret": "sk",
            "role_trn": "trn:iam::1234567890:role/sms-role",
            "sms_account": "sub-account",
            "sign_name": "sign",
            "template_code": "template-id",
        })

        self.assertEqual("role", config["auth_type"])

    def test_rejects_unsupported_provider(self):
        from console.services.sms_config import SMSConfigValidationError, normalize_sms_config

        with self.assertRaises(SMSConfigValidationError):
            normalize_sms_config({
                "provider": "unknown",
                "access_key": "ak",
                "access_secret": "sk",
                "sign_name": "sign",
                "template_code": "template-id",
            })

    def test_rejects_unsupported_auth_type(self):
        from console.services.sms_config import SMSConfigValidationError, normalize_sms_config

        with self.assertRaises(SMSConfigValidationError):
            normalize_sms_config({
                "provider": "aliyun",
                "auth_type": "session_token",
                "access_key": "ak",
                "access_secret": "sk",
                "sign_name": "sign",
                "template_code": "SMS_123",
            })

    def test_rejects_blank_required_value(self):
        from console.services.sms_config import SMSConfigValidationError, normalize_sms_config

        with self.assertRaises(SMSConfigValidationError):
            normalize_sms_config({
                "provider": "aliyun",
                "access_key": " ",
                "access_secret": "sk",
                "sign_name": "sign",
                "template_code": "SMS_123",
            })
