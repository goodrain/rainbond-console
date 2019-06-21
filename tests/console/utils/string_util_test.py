# -*- coding:utf-8 -*-
from console.utils.string_util import check_contain_chinese


def test_check_contain_chinese():
    testcases = [
        {"in": "hahaha", "exp": False},
        {"in": "哈哈哈", "exp": True},
        {"in": "", "exp": False},
        {"in": "ha哈哈哈haha", "exp": True},
    ]
    for testcase in testcases:
        assert testcase["exp"] == check_contain_chinese(testcase["in"])
