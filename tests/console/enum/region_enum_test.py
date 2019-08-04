# -*- coding: utf8 -*-
from console.enum.region_enum import RegionStatusEnum


def test_region_status_names():
    names = RegionStatusEnum.names()

    assert isinstance(names, list)
    assert len(names) == 4


def test_region_status_to_dict():
    d = RegionStatusEnum.to_dict()

    assert isinstance(d, dict)
    assert len(d) == 4
    assert d["NOTREADY"] == 0
    assert d["ONLINE"] == 1
    assert d["OFFLINE"] == 2
    assert d["MAINTAIN"] == 3
    assert "ONLINE" == RegionStatusEnum.ONLINE.name
