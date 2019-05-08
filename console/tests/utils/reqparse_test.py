# coding: utf-8
"""请求参数解析测试"""
from unittest import TestCase

import mock
from django.http import QueryDict
from rest_framework.request import Request

from console.exception.main import AbortRequest
from console.utils.reqparse import parse_args
from console.utils.reqparse import parse_argument
from console.utils.reqparse import parse_date
from console.utils.reqparse import parse_item


class ParseArgumentTestCase(TestCase):
    """请求参数解析测试"""
    request = None

    def setUp(self):
        self.request = mock.create_autospec(Request)
        self.request.GET = QueryDict('a=1&b=hello&c=django&c=test&d=true')

    def test_value_type_error(self):
        """测试 value_type TypeError"""
        with self.assertRaises(TypeError):
            parse_argument(self.request, 'a', value_type=dict)

    def test_parse_argument_default_error(self):
        """测试默认参数类型错误"""
        with self.assertRaises(TypeError):
            parse_argument(self.request, 'a', default='hello', value_type=int)

    def test_parse_argument_return_bool(self):
        """测试 bool 参数获取"""
        value = parse_argument(self.request, 'd', value_type=bool)
        self.assertEqual(value, True)

    def test_parse_argument_return_default_bool(self):
        """测试 bool 默认参数获取"""
        value = parse_argument(self.request, 'i', default=True, value_type=bool)
        self.assertEqual(value, True)

    def test_parse_argument_return_bool_error(self):
        """测试 bool 参数获取错误"""
        try:
            parse_argument(self.request, 'a', value_type=bool)
        except AbortRequest as e:
            self.assertEqual(isinstance(e, AbortRequest), True)

    def test_parse_argument_return_int(self):
        """测试 int 参数获取"""
        value = parse_argument(self.request, 'a', value_type=int)
        self.assertEqual(value, 1)

    def test_parse_argument_return_str(self):
        """测试 str 参数获取"""
        value = parse_argument(self.request, 'b', value_type=str)
        self.assertEqual(value, 'hello')

    def test_parse_argument_return_list(self):
        """测试 list 参数获取"""
        value = parse_argument(self.request, 'c', value_type=list)
        self.assertEqual(isinstance(value, list), True)
        self.assertEqual(value, ['django', 'test'])

    def test_not__return_int(self):
        """测试获取不到 int 参数"""
        value = parse_argument(self.request, 'not_int', value_type=int)
        self.assertEqual(value, None)

    def test_not_get_argument_return_list(self):
        """测试获取不到 list 参数"""
        value = parse_argument(self.request, 'not_list', value_type=list)
        self.assertEqual(value, None)

    def test_parse_argument_return_int_must(self):
        """测试获取必填参数"""
        value = parse_argument(
            self.request,
            'a',
            value_type=int,
            required=True,
            error="缺少必填参数"
        )
        self.assertEqual(value, 1)

    def test_parse_argument_return_list_must(self):
        """测试获取 list 必填参数"""
        value = parse_argument(
            self.request,
            'c',
            value_type=list,
            required=True,
            error="缺少必填参数"
        )
        self.assertEqual(isinstance(value, list), True)
        self.assertEqual(value, ['django', 'test'])

    def test_not_parse_argument_return_list_must(self):
        """测试获取不到 list 必填参数"""
        try:
            parse_argument(
                self.request,
                'not_list',
                value_type=list,
                required=True,
                error="缺少必填参数"
            )
        except AbortRequest as e:
            self.assertEqual(isinstance(e, AbortRequest), True)

    def test_not_parse_argument_return_int_must(self):
        """测试获取不到必填参数"""
        try:
            parse_argument(
                self.request,
                'not_int',
                value_type=int,
                required=True,
                error="缺少必填参数"
            )
        except AbortRequest as e:
            self.assertEqual(isinstance(e, AbortRequest), True)

    def test_parse_args(self):
        """测试解析多个参数"""
        args_conf = (
            {'key': 'a', 'value_type': int},
            {'key': 'b', 'value_type': str},
            {'key': 'c', 'value_type': list},
            {'key': 'not_list', 'value_type': list},
        )
        args = parse_args(self.request, args_conf)
        self.assertEqual(
            args,
            {
                'a': 1,
                'b': 'hello',
                'c': ['django', 'test'],
            }
        )


class ParseDateTestCase(TestCase):
    """解析 data"""
    request = None

    def setUp(self):
        self.request = mock.create_autospec(Request)
        self.request.data = {'a': 1, 'b': 'hello'}

    def test_parse_item(self):
        """测试 解析一个参数"""
        value = parse_item(self.request, 'a')
        self.assertEqual(value, 1)

    def test_parse_item_must(self):
        """测试 解析必填参数"""
        value = parse_item(self.request, 'a', required=True)
        self.assertEqual(value, 1)

    def test_not_parse_item_must(self):
        """测试解析不到必填参数"""
        try:
            parse_item(self.request, 'c', required=True)
        except AbortRequest as e:
            self.assertEqual(isinstance(e, AbortRequest), True)

    def test_parse_data(self):
        """测试解析data"""
        data_conf = (
            {'key': 'a', 'required': True},
            {'key': 'b', 'required': True},
            {'key': 'c', 'default': [1, 2]},
        )
        data = parse_date(self.request, data_conf)
        self.assertEqual(
            data,
            {
                'a': 1,
                'b': 'hello',
                'c': [1, 2],
            }
        )
