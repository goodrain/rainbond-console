# coding: utf-8
"""请求参数解析测试"""
from unittest import TestCase

import os
import sys
from types import ModuleType

try:
    import mock
except ImportError:
    from unittest import mock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "openapi-client")))
sys.modules.setdefault("MySQLdb", ModuleType("MySQLdb"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "goodrain_web.settings")

import django
from django.http import QueryDict
from rest_framework.request import Request

django.setup()

from console.exception.main import AbortRequest
from console.utils.reqparse import parse_args
from console.utils.reqparse import parse_argument
from console.utils.reqparse import bool_argument
from console.utils.reqparse import parse_date
from console.utils.reqparse import parse_item


class ParseArgumentTestCase(TestCase):
    # capability_id: console.request-args.query-parse
    """请求参数解析测试"""
    request = None

    def setUp(self):
        self.request = mock.create_autospec(Request)
        self.request.GET = QueryDict('a=1&b=hello&c=django&c=test&d=true')

    # capability_id: console.request-args.type-error
    def test_value_type_error(self):
        """测试 value_type TypeError"""
        with self.assertRaises(TypeError):
            parse_argument(self.request, 'a', value_type=dict)

    # capability_id: console.request-args.default-type-error
    def test_parse_argument_default_error(self):
        """测试默认参数类型错误"""
        with self.assertRaises(TypeError):
            parse_argument(self.request, 'a', default='hello', value_type=int)

    # capability_id: console.request-args.bool-parse
    def test_parse_argument_return_bool(self):
        """测试 bool 参数获取"""
        value = parse_argument(self.request, 'd', value_type=bool)
        self.assertEqual(value, True)

    # capability_id: console.request-args.bool-default-true
    def test_parse_argument_return_default_bool(self):
        """测试 bool 默认参数获取"""
        value = parse_argument(self.request, 'i', default=True, value_type=bool)
        self.assertEqual(value, True)

    # capability_id: console.request-args.bool-default-false
    def test_parse_argument_return_default_false_bool(self):
        value = parse_argument(self.request, 'missing_bool', default=False, value_type=bool)
        self.assertEqual(value, False)

    # capability_id: console.request-args.bool-invalid
    def test_parse_argument_return_bool_error(self):
        """测试 bool 参数获取错误"""
        try:
            parse_argument(self.request, 'a', value_type=bool)
        except AbortRequest as e:
            self.assertEqual(isinstance(e, AbortRequest), True)

    # capability_id: console.request-args.int-parse
    def test_parse_argument_return_int(self):
        """测试 int 参数获取"""
        value = parse_argument(self.request, 'a', value_type=int)
        self.assertEqual(value, 1)

    # capability_id: console.request-args.string-parse
    def test_parse_argument_return_str(self):
        """测试 str 参数获取"""
        value = parse_argument(self.request, 'b', value_type=str)
        self.assertEqual(value, 'hello')

    # capability_id: console.request-args.list-parse
    def test_parse_argument_return_list(self):
        """测试 list 参数获取"""
        value = parse_argument(self.request, 'c', value_type=list)
        self.assertEqual(isinstance(value, list), True)
        self.assertEqual(value, ['django', 'test'])

    # capability_id: console.request-args.int-missing
    def test_not__return_int(self):
        """测试获取不到 int 参数"""
        value = parse_argument(self.request, 'not_int', value_type=int)
        self.assertEqual(value, None)

    # capability_id: console.request-args.list-missing
    def test_not_get_argument_return_list(self):
        """测试获取不到 list 参数"""
        value = parse_argument(self.request, 'not_list', value_type=list)
        self.assertEqual(value, None)

    # capability_id: console.request-args.list-default-fallback
    def test_parse_argument_return_list_default(self):
        value = parse_argument(self.request, 'not_list', default=['fallback'], value_type=list)
        self.assertEqual(value, ['fallback'])

    # capability_id: console.request-args.int-required
    def test_parse_argument_return_int_must(self):
        """测试获取必填参数"""
        value = parse_argument(self.request, 'a', value_type=int, required=True, error="缺少必填参数")
        self.assertEqual(value, 1)

    # capability_id: console.request-args.list-required
    def test_parse_argument_return_list_must(self):
        """测试获取 list 必填参数"""
        value = parse_argument(self.request, 'c', value_type=list, required=True, error="缺少必填参数")
        self.assertEqual(isinstance(value, list), True)
        self.assertEqual(value, ['django', 'test'])

    # capability_id: console.request-args.list-required-missing
    def test_not_parse_argument_return_list_must(self):
        """测试获取不到 list 必填参数"""
        try:
            parse_argument(self.request, 'not_list', value_type=list, required=True, error="缺少必填参数")
        except AbortRequest as e:
            self.assertEqual(isinstance(e, AbortRequest), True)

    # capability_id: console.request-args.int-required-missing
    def test_not_parse_argument_return_int_must(self):
        """测试获取不到必填参数"""
        try:
            parse_argument(self.request, 'not_int', value_type=int, required=True, error="缺少必填参数")
        except AbortRequest as e:
            self.assertEqual(isinstance(e, AbortRequest), True)

    # capability_id: console.request-args.parse-batch
    def test_parse_args(self):
        """测试解析多个参数"""
        args_conf = (
            {
                'key': 'a',
                'value_type': int
            },
            {
                'key': 'b',
                'value_type': str
            },
            {
                'key': 'c',
                'value_type': list
            },
            {
                'key': 'not_list',
                'value_type': list
            },
        )
        args = parse_args(self.request, args_conf)
        self.assertEqual(args, {
            'a': 1,
            'b': 'hello',
            'c': ['django', 'test'],
        })

    # capability_id: console.request-args.parse-args-keep-falsy
    def test_parse_args_keep_falsy_values(self):
        self.request.GET = QueryDict('count=0&name=')
        args_conf = (
            {
                'key': 'count',
                'value_type': int
            },
            {
                'key': 'name',
                'value_type': str
            },
            {
                'key': 'missing',
                'value_type': int
            },
        )
        args = parse_args(self.request, args_conf)
        self.assertEqual(args, {
            'count': 0,
            'name': '',
        })


class ParseDateTestCase(TestCase):
    # capability_id: console.request-args.data-parse
    """解析 data"""
    request = None

    def setUp(self):
        self.request = mock.create_autospec(Request)
        self.request.data = {'a': 1, 'b': 'hello'}

    # capability_id: console.request-data.item-parse
    def test_parse_item(self):
        """测试 解析一个参数"""
        value = parse_item(self.request, 'a')
        self.assertEqual(value, 1)

    # capability_id: console.request-data.item-required
    def test_parse_item_must(self):
        """测试 解析必填参数"""
        value = parse_item(self.request, 'a', required=True)
        self.assertEqual(value, 1)

    # capability_id: console.request-data.item-required-missing
    def test_not_parse_item_must(self):
        """测试解析不到必填参数"""
        try:
            parse_item(self.request, 'c', required=True)
        except AbortRequest as e:
            self.assertEqual(isinstance(e, AbortRequest), True)

    # capability_id: console.request-data.required-default-error
    def test_parse_item_required_uses_default_error_message(self):
        with self.assertRaises(AbortRequest) as ctx:
            parse_item(self.request, 'missing_field', required=True)
        self.assertIn("the filed 'missing_field' is required", str(ctx.exception))

    # capability_id: console.request-data.parse-batch
    def test_parse_data(self):
        """测试解析data"""
        data_conf = (
            {
                'key': 'a',
                'required': True
            },
            {
                'key': 'b',
                'required': True
            },
            {
                'key': 'c',
                'default': [1, 2]
            },
        )
        data = parse_date(self.request, data_conf)
        self.assertEqual(data, {
            'a': 1,
            'b': 'hello',
            'c': [1, 2],
        })

    # capability_id: console.request-data.dict-parse
    def test_parse_dict_data(self):
        data = {"foo": "bar"}
        value = parse_item(data, key="foo", required=True)
        self.assertEqual(value, "bar")

    # capability_id: console.request-data.parse-date-keep-falsy
    def test_parse_date_keep_falsy_values(self):
        self.request.data = {'count': 0, 'enabled': False, 'name': ''}
        data_conf = (
            {
                'key': 'count',
            },
            {
                'key': 'enabled',
            },
            {
                'key': 'name',
            },
            {
                'key': 'missing',
            },
        )
        data = parse_date(self.request, data_conf)
        self.assertEqual(data, {
            'count': 0,
            'enabled': False,
            'name': '',
        })


class BoolArgumentTestCase(TestCase):
    # capability_id: console.request-args.bool-coercion
    def test_bool_argument_accepts_string_and_bool_inputs(self):
        self.assertTrue(bool_argument("true"))
        self.assertFalse(bool_argument("false"))
        self.assertTrue(bool_argument(True))
        self.assertFalse(bool_argument(False))

    def test_bool_argument_rejects_invalid_value(self):
        with self.assertRaises(AbortRequest):
            bool_argument("yes")
