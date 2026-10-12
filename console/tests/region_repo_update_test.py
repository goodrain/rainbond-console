# -*- coding: utf-8 -*-
from unittest import TestCase, mock

from console.repositories.region_repo import RegionRepo


class RegionRepoUpdateTestCase(TestCase):
    # capability_id: console.region.partial-update-preserves-required-fields
    def test_partial_update_preserves_omitted_required_connection_fields(self):
        region = mock.Mock(
            region_alias="Old Region",
            url="https://region-api.example.com",
            wsurl="wss://region-api.example.com/ws",
            httpdomain="example.com",
            tcpdomain="tcp.example.com",
            scope="private",
            ssl_ca_cert="ca",
            cert_file="cert",
            key_file="key",
            desc="old",
        )
        repo = RegionRepo()

        with mock.patch.object(repo, "get_region_by_id", return_value=region):
            updated = repo.update_enterprise_region(
                "enterprise-id",
                "region-id",
                {"region_alias": "New Region", "desc": "new"},
            )

        self.assertIs(updated, region)
        self.assertEqual(region.region_alias, "New Region")
        self.assertEqual(region.desc, "new")
        self.assertEqual(region.url, "https://region-api.example.com")
        self.assertEqual(region.wsurl, "wss://region-api.example.com/ws")
        self.assertEqual(region.httpdomain, "example.com")
        self.assertEqual(region.tcpdomain, "tcp.example.com")
        region.save.assert_called_once_with()
