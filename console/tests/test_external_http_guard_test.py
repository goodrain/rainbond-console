# -*- coding: utf-8 -*-
import pytest
import requests


def test_external_http_requests_are_blocked():
    with pytest.raises(AssertionError, match="external HTTP request"):
        requests.post("https://posthog.goodrain.com/batch/", timeout=1)
