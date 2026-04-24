import ipaddress

from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from base.middlewares import TrustedProxyMiddleware


class TrustedProxyMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = lambda request: HttpResponse()
        self.middleware = TrustedProxyMiddleware(self.get_response)
        self.default_headers = {
            "HTTP_X_FORWARDED_FOR": "1.2.3.4",
            "HTTP_X_FORWARDED_HOST": "example.com",
            "HTTP_X_FORWARDED_PROTO": "https",
        }

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("10.0.0.0/8")])
    def test_trusted_proxy_keeps_headers(self):
        request = self.factory.get("/", **self.default_headers)
        request.META["REMOTE_ADDR"] = "10.0.0.1"

        self.middleware(request)

        self.assertEqual(request.META.get("HTTP_X_FORWARDED_FOR"), "1.2.3.4")
        self.assertEqual(request.META.get("HTTP_X_FORWARDED_HOST"), "example.com")
        self.assertEqual(request.META.get("HTTP_X_FORWARDED_PROTO"), "https")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("10.0.0.0/8")])
    def test_untrusted_proxy_removes_headers(self):
        request = self.factory.get("/", **self.default_headers)
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        self.middleware(request)

        self.assertNotIn("HTTP_X_FORWARDED_FOR", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_HOST", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_PROTO", request.META)

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("10.0.0.0/8")])
    def test_missing_remote_addr_removes_headers(self):
        request = self.factory.get("/", **self.default_headers)
        if "REMOTE_ADDR" in request.META:
            del request.META["REMOTE_ADDR"]

        self.middleware(request)

        self.assertNotIn("HTTP_X_FORWARDED_FOR", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_HOST", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_PROTO", request.META)

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("10.0.0.0/8")])
    def test_invalid_remote_addr_removes_headers(self):
        request = self.factory.get("/", **self.default_headers)
        request.META["REMOTE_ADDR"] = "not-an-ip"

        self.middleware(request)

        self.assertNotIn("HTTP_X_FORWARDED_FOR", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_HOST", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_PROTO", request.META)

    @override_settings(TRUSTED_PROXY_NETS=[])
    def test_empty_trusted_nets_removes_headers(self):
        request = self.factory.get("/", **self.default_headers)
        request.META["REMOTE_ADDR"] = "10.0.0.1"

        self.middleware(request)

        self.assertNotIn("HTTP_X_FORWARDED_FOR", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_HOST", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_PROTO", request.META)

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("10.0.0.0/8")])
    def test_missing_headers_handled_gracefully(self):
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # This should not raise any exceptions
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HTTP_X_FORWARDED_FOR", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_HOST", request.META)
        self.assertNotIn("HTTP_X_FORWARDED_PROTO", request.META)
