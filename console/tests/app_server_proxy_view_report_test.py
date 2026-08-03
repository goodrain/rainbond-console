# -*- coding: utf-8 -*-
from unittest import TestCase, mock

from console.views.app_server_proxy import AppServerProxyView


def make_request(path, method="GET", meta=None):
    request = mock.Mock()
    request.path = path
    request.method = method
    request.META = meta if meta is not None else {}
    return request


def make_response(status_code=200, content=b'{"marketID": "m1", "appKeyID": "a1"}', content_type="application/json"):
    response = mock.Mock()
    response.status_code = status_code
    response.content = content
    response.headers = {"Content-Type": content_type}
    return response


class AppServerProxyViewReportTests(TestCase):
    """控制台内的应用市场经由 /app-server 代理请求商店的应用详情, 但从不上报浏览量,
    所以商店的 showCount 只统计到网页商店那一侧, 控制台内的浏览是空的(P0-1).
    这里覆盖"哪些请求该上报、上报到哪个地址、以及上报失败不能影响详情返回".
    """
    def setUp(self):
        self.view = AppServerProxyView()

    def test_app_detail_request_reports_view_to_store(self):
        request = make_request("/app-server/marketui/apps/1723/detail",
                               meta={
                                   "REMOTE_ADDR": "10.0.0.9",
                                   "HTTP_X_FORWARDED_FOR": "1.2.3.4"
                               })

        with mock.patch("console.views.app_server_proxy.threading.Thread") as thread:
            self.view.report_app_view(request, make_response())

        thread.assert_called_once()
        url, headers = thread.call_args.kwargs["args"]
        self.assertEqual("https://hub.grapps.cn/app-server/markets/m1/apps/a1/view", url)
        self.assertEqual("1.2.3.4", headers["X-Forwarded-For"])
        self.assertEqual("10.0.0.9", headers["X-Real-IP"])
        self.assertTrue(thread.call_args.kwargs["daemon"])
        thread.return_value.start.assert_called_once()

    def test_legacy_app_detail_path_also_reports(self):
        request = make_request("/app-server/marketui/859a51f9/apps/a1/detail")

        with mock.patch("console.views.app_server_proxy.threading.Thread") as thread:
            self.view.report_app_view(request, make_response())

        thread.assert_called_once()

    def test_non_detail_request_does_not_report(self):
        request = make_request("/app-server/marketui/859a51f9/indexApps")

        with mock.patch("console.views.app_server_proxy.threading.Thread") as thread:
            self.view.report_app_view(request, make_response())

        thread.assert_not_called()

    def test_failed_detail_request_does_not_report(self):
        request = make_request("/app-server/marketui/apps/1723/detail")

        with mock.patch("console.views.app_server_proxy.threading.Thread") as thread:
            self.view.report_app_view(request, make_response(status_code=404))

        thread.assert_not_called()

    def test_non_get_request_does_not_report(self):
        request = make_request("/app-server/marketui/apps/1723/detail", method="POST")

        with mock.patch("console.views.app_server_proxy.threading.Thread") as thread:
            self.view.report_app_view(request, make_response())

        thread.assert_not_called()

    def test_response_without_app_identity_does_not_report(self):
        request = make_request("/app-server/marketui/apps/1723/detail")

        with mock.patch("console.views.app_server_proxy.threading.Thread") as thread:
            self.view.report_app_view(request, make_response(content=b'{"name": "Coze"}'))

        thread.assert_not_called()

    def test_non_json_response_does_not_report(self):
        request = make_request("/app-server/marketui/apps/1723/detail")

        with mock.patch("console.views.app_server_proxy.threading.Thread") as thread:
            self.view.report_app_view(request, make_response(content=b"<html>", content_type="text/html"))

        thread.assert_not_called()

    def test_broken_json_response_does_not_report(self):
        request = make_request("/app-server/marketui/apps/1723/detail")

        with mock.patch("console.views.app_server_proxy.threading.Thread") as thread:
            self.view.report_app_view(request, make_response(content=b"{not json"))

        thread.assert_not_called()

    def test_store_failure_is_swallowed(self):
        with mock.patch("console.views.app_server_proxy.requests.post", side_effect=Exception("boom")):
            self.view.post_app_view("https://hub.grapps.cn/app-server/markets/m1/apps/a1/view", {})
