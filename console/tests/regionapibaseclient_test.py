# -*- coding: utf-8 -*-
import collections
import json
import os
import sys
from types import ModuleType
from unittest import TestCase

for attr in ("Mapping", "MutableMapping", "Sequence", "Iterable", "Iterator"):
    if not hasattr(collections, attr):
        setattr(collections, attr, getattr(collections.abc, attr))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django  # noqa: E402

django.setup()

from console.exception.main import ServiceHandleException  # noqa: E402
from www.apiclient.regionapibaseclient import RegionApiBaseHttpClient  # noqa: E402


class RegionApiBaseHttpClientTestCase(TestCase):
    # capability_id: console.region-api.helm-resource-conflict-msg
    def test_check_status_translates_helm_ownership_conflict_to_actionable_msg_show(self):
        client = RegionApiBaseHttpClient()
        raw_message = (
            'rendered manifests contain a resource that already exists. Unable to continue with install: '
            'Service "nginx" in namespace "zzz" exists and cannot be imported into the current release: '
            'invalid ownership metadata; label validation error: missing key "app.kubernetes.io/managed-by": '
            'must be set to "Helm"; annotation validation error: missing key "meta.helm.sh/release-name": '
            'must be set to "nginx"; annotation validation error: missing key "meta.helm.sh/release-namespace": '
            'must be set to "zzz"'
        )

        with self.assertRaises(ServiceHandleException) as context:
            client._check_status(
                url="/v2/tenants/demo/helm/releases",
                method="POST",
                status=500,
                content=json.dumps({
                    "code": 500,
                    "msg": raw_message
                }),
            )

        error = context.exception
        self.assertEqual(error.msg, raw_message)
        self.assertEqual(error.status_code, 500)
        self.assertEqual(
            error.msg_show,
            '命名空间 zzz 中已存在资源 Service/nginx，且缺少 Helm 接管元数据，Release nginx 无法继续安装。'
            '请先删除该资源，或补齐 Helm 元数据后重试：'
            'app.kubernetes.io/managed-by=Helm，'
            'meta.helm.sh/release-name=nginx，'
            'meta.helm.sh/release-namespace=zzz。')

    # capability_id: console.region-api.proxy-error-pass-through
    def test_check_status_keeps_original_message_for_non_helm_conflicts(self):
        client = RegionApiBaseHttpClient()
        raw_message = "locate chart: repository not found"

        with self.assertRaises(ServiceHandleException) as context:
            client._check_status(
                url="/v2/tenants/demo/helm/releases",
                method="POST",
                status=400,
                content=json.dumps({
                    "code": 400,
                    "msg": raw_message
                }),
            )

        error = context.exception
        self.assertEqual(error.msg, raw_message)
        self.assertEqual(error.msg_show, raw_message)

    # capability_id: console.region-api.batch-create-error-bean
    def test_check_status_preserves_batch_create_result_bean_for_coded_errors(self):
        client = RegionApiBaseHttpClient()

        with self.assertRaises(ServiceHandleException) as context:
            client._check_status(
                url="/v2/tenants/demo/ns-resources",
                method="POST",
                status=400,
                content=json.dumps({
                    "code": 400,
                    "msg": "共创建 2 个资源，全部失败",
                    "data": {
                        "bean": {
                            "summary": {
                                "total": 2,
                                "success_count": 0,
                                "failure_count": 2,
                                "partial_success": False
                            },
                            "results": [
                                {
                                    "index": 1,
                                    "kind": "Service",
                                    "name": "demo",
                                    "success": False,
                                    "message": "services \"demo\" already exists"
                                }
                            ]
                        }
                    }
                }),
            )

        error = context.exception
        self.assertEqual(error.msg, "共创建 2 个资源，全部失败")
        self.assertEqual(error.response.data["data"]["bean"]["summary"]["failure_count"], 2)
        self.assertEqual(error.response.data["data"]["bean"]["results"][0]["kind"], "Service")

    # capability_id: console.region-api.domain-conflict-msg
    def test_check_status_keeps_domain_conflict_as_conflict_error(self):
        client = RegionApiBaseHttpClient()
        raw_message = (
            "domain conflict: domain 'yangshanshu.core.lchuike.com' conflicts with existing domain "
            "'yangshanshu.core.lchuike.com' in namespace 'tenant-a' (resource: existing-cert)"
        )

        with self.assertRaises(ServiceHandleException) as context:
            client._check_status(
                url="/api-gateway/v1/demo/routes/http/cert-manager",
                method="POST",
                status=409,
                content=json.dumps({
                    "msg": raw_message
                }),
            )

        error = context.exception
        self.assertEqual(error.msg, raw_message)
        self.assertEqual(error.status_code, 409)
        self.assertEqual(error.error_code, 409)
        self.assertEqual(
            error.msg_show,
            "域名 yangshanshu.core.lchuike.com 与命名空间 tenant-a 下资源 existing-cert 的现有证书配置冲突，请先清理冲突配置后重试。")
