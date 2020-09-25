# -*- coding: utf8 -*-
from app import GovernanceModeEnum


def test_governance_mode_choices():
    choices = GovernanceModeEnum.choices()
    want = ["BUILD_IN_SERVICE_MESH", "KUBERNETES_NATIVE_SERVICE"]
    # compare
    assert not set(choices) & set(want)
