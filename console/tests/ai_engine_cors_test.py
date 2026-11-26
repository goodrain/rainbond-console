# capability_id: console.ai-engine.public-scope-protocol
from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from corsheaders.middleware import CorsMiddleware


class AIEngineCORSContractTests(SimpleTestCase):
    @override_settings(CORS_ALLOW_ALL_ORIGINS=True)
    def test_explicit_model_api_selector_is_allowed_for_public_browser_preflight(self):
        request = RequestFactory().options(
            "/openapi/v1/ai-engine/team/regions/region/v1/responses",
            HTTP_ORIGIN="https://caller.invalid",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type,x-ai-model-api",
        )
        response = CorsMiddleware(lambda _: HttpResponse())(request)
        allowed = {name.strip().lower() for name in response["Access-Control-Allow-Headers"].split(",")}
        self.assertIn("x-ai-model-api", allowed)
        self.assertIn("authorization", allowed)
        self.assertIn("content-type", allowed)
        self.assertNotIn("x-ai-platform-token", allowed)
        self.assertIn("POST", settings.CORS_ALLOW_METHODS)
