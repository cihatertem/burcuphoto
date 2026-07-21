import ipaddress
import json
from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.core.exceptions import DisallowedHost
from django.http import JsonResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from PIL import Image

from base.utils import (
    HealthCheckMiddleware,
    RateLimitHMAC,
    _get_ip_from_xff,
    _get_trusted_networks_optimized,
    _get_trusted_proxies,
    _is_ip_trusted,
    _is_trusted_proxy_ip,
    _parse_ip,
    client_ip_key,
    current_year,
    get_client_ip,
    photo_resizer,
    portfolio_directory_path,
    project_directory_path,
)


class ParseIpTests(TestCase):
    def test_valid_ipv4(self):
        """Test parsing a valid IPv4 address."""
        ip = _parse_ip("192.168.1.1")
        self.assertEqual(ip, ipaddress.IPv4Address("192.168.1.1"))

    def test_valid_ipv6(self):
        """Test parsing a valid IPv6 address."""
        ip = _parse_ip("2001:db8::1")
        self.assertEqual(ip, ipaddress.IPv6Address("2001:db8::1"))

    def test_invalid_ip(self):
        """Test parsing an invalid IP string raises ValueError."""
        with self.assertRaises(ValueError):
            _parse_ip("invalid-ip")

    def test_lru_cache(self):
        """Test that the LRU cache is working as expected."""
        # Clear cache before testing to avoid interference from other tests
        _parse_ip.cache_clear()

        # Initial call
        _parse_ip("10.0.0.1")
        info = _parse_ip.cache_info()
        self.assertEqual(info.hits, 0)
        self.assertEqual(info.misses, 1)

        # Cached call
        _parse_ip("10.0.0.1")
        info = _parse_ip.cache_info()
        self.assertEqual(info.hits, 1)
        self.assertEqual(info.misses, 1)


class IsIpTrustedTests(TestCase):
    def test_ip_in_trusted_ips(self):
        ip_obj = ipaddress.ip_address("192.168.1.1")
        trusted_ips = {
            ipaddress.ip_address("192.168.1.1"),
            ipaddress.ip_address("10.0.0.1"),
        }
        trusted_subnets = []
        self.assertTrue(_is_ip_trusted(ip_obj, trusted_ips, trusted_subnets))

    def test_ip_in_trusted_subnets(self):
        ip_obj = ipaddress.ip_address("192.168.1.50")
        trusted_ips = set()
        trusted_subnets = [ipaddress.ip_network("192.168.1.0/24")]
        self.assertTrue(_is_ip_trusted(ip_obj, trusted_ips, trusted_subnets))

    def test_ip_not_in_trusted(self):
        ip_obj = ipaddress.ip_address("8.8.8.8")
        trusted_ips = {ipaddress.ip_address("192.168.1.1")}
        trusted_subnets = [ipaddress.ip_network("10.0.0.0/8")]
        self.assertFalse(_is_ip_trusted(ip_obj, trusted_ips, trusted_subnets))

    def test_empty_trusted_lists(self):
        ip_obj = ipaddress.ip_address("192.168.1.1")
        trusted_ips = set()
        trusted_subnets = []
        self.assertFalse(_is_ip_trusted(ip_obj, trusted_ips, trusted_subnets))

    def test_ipv6_in_trusted_subnets(self):
        ip_obj = ipaddress.ip_address("2001:db8::1234")
        trusted_ips = set()
        trusted_subnets = [ipaddress.ip_network("2001:db8::/32")]
        self.assertTrue(_is_ip_trusted(ip_obj, trusted_ips, trusted_subnets))


class GetTrustedNetworksOptimizedTests(TestCase):
    def test_empty_tuple(self):
        trusted_ips, trusted_subnets = _get_trusted_networks_optimized(())
        self.assertEqual(trusted_ips, set())
        self.assertEqual(trusted_subnets, [])

    def test_single_ips(self):
        nets = (
            ipaddress.ip_network("192.168.1.1/32"),
            ipaddress.ip_network("10.0.0.1/32"),
            ipaddress.ip_network("::1/128"),
        )
        trusted_ips, trusted_subnets = _get_trusted_networks_optimized(nets)
        expected_ips = {
            ipaddress.ip_address("192.168.1.1"),
            ipaddress.ip_address("10.0.0.1"),
            ipaddress.ip_address("::1"),
        }
        self.assertEqual(trusted_ips, expected_ips)
        self.assertEqual(trusted_subnets, [])

    def test_subnets(self):
        nets = (
            ipaddress.ip_network("192.168.1.0/24"),
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("2001:db8::/32"),
        )
        trusted_ips, trusted_subnets = _get_trusted_networks_optimized(nets)
        self.assertEqual(trusted_ips, set())
        self.assertEqual(list(trusted_subnets), list(nets))

    def test_mixed_ips_and_subnets(self):
        nets = (
            ipaddress.ip_network("192.168.1.1/32"),
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("::1/128"),
            ipaddress.ip_network("2001:db8::/32"),
        )
        trusted_ips, trusted_subnets = _get_trusted_networks_optimized(nets)
        expected_ips = {
            ipaddress.ip_address("192.168.1.1"),
            ipaddress.ip_address("::1"),
        }
        expected_subnets = [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("2001:db8::/32"),
        ]
        self.assertEqual(trusted_ips, expected_ips)
        self.assertEqual(list(trusted_subnets), expected_subnets)


class GetTrustedProxiesTests(TestCase):
    def test_get_trusted_proxies_without_settings(self):
        trusted_ips, trusted_subnets = _get_trusted_proxies()
        self.assertIsNone(trusted_ips)
        self.assertIsNone(trusted_subnets)

    def test_trusted_proxy_nets_not_set(self):
        with self.settings(TRUSTED_PROXY_NETS=None):
            trusted_ips, trusted_subnets = _get_trusted_proxies()
            self.assertIsNone(trusted_ips)
            self.assertIsNone(trusted_subnets)

    @override_settings(TRUSTED_PROXY_NETS=[])
    def test_trusted_proxy_nets_empty(self):
        trusted_ips, trusted_subnets = _get_trusted_proxies()
        self.assertIsNone(trusted_ips)
        self.assertIsNone(trusted_subnets)

    @override_settings(
        TRUSTED_PROXY_NETS=[
            ipaddress.ip_network("192.168.1.1/32"),
            ipaddress.ip_network("10.0.0.0/8"),
        ]
    )
    def test_trusted_proxy_nets_with_values(self):
        trusted_ips, trusted_subnets = _get_trusted_proxies()
        self.assertEqual(trusted_ips, {ipaddress.ip_address("192.168.1.1")})
        self.assertEqual(trusted_subnets, [ipaddress.ip_network("10.0.0.0/8")])


class IsTrustedProxyIpTests(TestCase):
    def test_ip_in_trusted_ips(self):
        trusted_ips = {ipaddress.ip_address("192.168.1.1")}
        self.assertTrue(_is_trusted_proxy_ip("192.168.1.1", trusted_ips, []))

    def test_ip_in_trusted_subnets(self):
        trusted_subnets = [ipaddress.ip_network("10.0.0.0/8")]
        self.assertTrue(_is_trusted_proxy_ip("10.0.0.1", set(), trusted_subnets))

    def test_ip_not_trusted(self):
        trusted_ips = {ipaddress.ip_address("192.168.1.1")}
        trusted_subnets = [ipaddress.ip_network("10.0.0.0/8")]
        self.assertFalse(
            _is_trusted_proxy_ip("172.16.0.1", trusted_ips, trusted_subnets)
        )

    @patch("base.utils._parse_ip", side_effect=ValueError)
    def test_value_error_returns_false(self, mock_parse_ip):
        result = _is_trusted_proxy_ip("invalid_ip", set(), [])
        self.assertFalse(result)


class GetClientIPTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_no_remote_addr(self):
        request = self.factory.get("/")
        # RequestFactory.get() might set REMOTE_ADDR to 127.0.0.1 by default
        if "REMOTE_ADDR" in request.META:
            del request.META["REMOTE_ADDR"]
        self.assertIsNone(get_client_ip(request))

    def test_empty_remote_addr(self):
        request = self.factory.get("/", REMOTE_ADDR="")
        self.assertIsNone(get_client_ip(request))

    def test_invalid_remote_addr(self):
        request = self.factory.get("/", REMOTE_ADDR="invalid_ip")
        self.assertEqual(get_client_ip(request), "invalid_ip")

    @override_settings(TRUSTED_PROXY_NETS=[])
    def test_untrusted_proxy_returns_remote_addr(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="1.2.3.4", HTTP_X_FORWARDED_FOR="5.6.7.8"
        )
        self.assertEqual(get_client_ip(request), "1.2.3.4")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("127.0.0.1/32")])
    def test_trusted_proxy_no_xff(self):
        request = self.factory.get("/", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(get_client_ip(request), "127.0.0.1")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("127.0.0.1/32")])
    def test_trusted_proxy_with_xff(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8"
        )
        self.assertEqual(get_client_ip(request), "5.6.7.8")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("127.0.0.1/32")])
    def test_trusted_proxy_empty_xff(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR=""
        )
        self.assertEqual(get_client_ip(request), "127.0.0.1")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("127.0.0.1/32")])
    def test_trusted_proxy_with_multiple_xff(self):
        # The rightmost non-trusted IP should be returned
        request = self.factory.get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8, 9.10.11.12"
        )
        self.assertEqual(get_client_ip(request), "9.10.11.12")

    @override_settings(
        TRUSTED_PROXY_NETS=[
            ipaddress.ip_network("127.0.0.1/32"),
            ipaddress.ip_network("10.0.0.0/8"),
        ]
    )
    def test_trusted_proxy_with_multiple_xff_and_multiple_trusted_proxies(self):
        # 10.0.0.1 is trusted, so it should be skipped and 9.10.11.12 should be returned
        request = self.factory.get(
            "/",
            REMOTE_ADDR="127.0.0.1",
            HTTP_X_FORWARDED_FOR="5.6.7.8, 9.10.11.12, 10.0.0.1",
        )
        self.assertEqual(get_client_ip(request), "9.10.11.12")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("127.0.0.1/32")])
    def test_trusted_proxy_with_spoofed_ip(self):
        # Malicious client sends X-Forwarded-For: 1.2.3.4
        # Proxy adds real client IP 9.10.11.12
        request = self.factory.get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4, 9.10.11.12"
        )
        self.assertEqual(get_client_ip(request), "9.10.11.12")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("127.0.0.1/32")])
    def test_trusted_proxy_with_invalid_ip(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8, invalid_ip"
        )
        self.assertEqual(get_client_ip(request), "invalid_ip")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("192.168.1.0/24")])
    def test_trusted_network_range(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="192.168.1.50", HTTP_X_FORWARDED_FOR="10.0.0.1"
        )
        self.assertEqual(get_client_ip(request), "10.0.0.1")

    def test_trusted_proxy_nets_not_set(self):
        # Ensure it works when TRUSTED_PROXY_NETS is not in settings
        with self.settings(TRUSTED_PROXY_NETS=None):
            request = self.factory.get(
                "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8"
            )
            self.assertEqual(get_client_ip(request), "127.0.0.1")

    def test_trusted_proxy_nets_absent(self):
        # Ensure it works when TRUSTED_PROXY_NETS is naturally absent from settings
        request = self.factory.get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8"
        )
        self.assertEqual(get_client_ip(request), "127.0.0.1")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("127.0.0.1/32")])
    def test_get_client_ip_with_multiple_malformed_xff_ips(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR=" , , "
        )
        self.assertEqual(get_client_ip(request), "127.0.0.1")

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network("192.168.1.1/32")])
    def test_untrusted_proxy(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="5.6.7.8"
        )
        self.assertEqual(get_client_ip(request), "127.0.0.1")


class GetIpFromXffTests(TestCase):
    def test_get_ip_from_xff_empty_strings(self):
        # Direct tests for the _get_ip_from_xff function edge cases
        trusted_ips, trusted_subnets = set(), []
        self.assertIsNone(_get_ip_from_xff("", trusted_ips, trusted_subnets))
        self.assertIsNone(_get_ip_from_xff("   ", trusted_ips, trusted_subnets))
        self.assertIsNone(_get_ip_from_xff(",,", trusted_ips, trusted_subnets))
        self.assertIsNone(_get_ip_from_xff(" , , ", trusted_ips, trusted_subnets))

    def test_single_ip(self):
        trusted_ips, trusted_subnets = set(), []
        self.assertEqual(
            _get_ip_from_xff("1.2.3.4", trusted_ips, trusted_subnets), "1.2.3.4"
        )
        self.assertEqual(
            _get_ip_from_xff(" 1.2.3.4 ", trusted_ips, trusted_subnets), "1.2.3.4"
        )

    def test_multiple_ips_all_untrusted(self):
        trusted_ips, trusted_subnets = set(), []
        # Since 5.6.7.8 is not a trusted proxy, it should break and return 5.6.7.8
        self.assertEqual(
            _get_ip_from_xff("1.2.3.4, 5.6.7.8", trusted_ips, trusted_subnets),
            "5.6.7.8",
        )

    def test_multiple_ips_with_trusted_proxy(self):
        trusted_ips, trusted_subnets = {ipaddress.ip_address("5.6.7.8")}, []
        # 5.6.7.8 is trusted proxy, so it skips it and returns 1.2.3.4
        self.assertEqual(
            _get_ip_from_xff("1.2.3.4, 5.6.7.8", trusted_ips, trusted_subnets),
            "1.2.3.4",
        )

        # 10.0.0.1 is trusted proxy, skips it. 5.6.7.8 is not trusted, breaks and returns 5.6.7.8.
        trusted_ips = {ipaddress.ip_address("10.0.0.1")}
        self.assertEqual(
            _get_ip_from_xff(
                "1.2.3.4, 5.6.7.8, 10.0.0.1", trusted_ips, trusted_subnets
            ),
            "5.6.7.8",
        )

    def test_multiple_ips_all_trusted_proxies(self):
        trusted_ips = {
            ipaddress.ip_address("5.6.7.8"),
            ipaddress.ip_address("10.0.0.1"),
        }
        trusted_subnets = []
        # Both are trusted, so it skips both and would return the left-most IP which is 1.2.3.4,
        # since 1.2.3.4 is evaluated next. If it's not a proxy, it breaks and returns it.
        self.assertEqual(
            _get_ip_from_xff(
                "1.2.3.4, 5.6.7.8, 10.0.0.1", trusted_ips, trusted_subnets
            ),
            "1.2.3.4",
        )

        # If ALL are trusted proxies, including 1.2.3.4, it returns the left-most.
        trusted_ips.add(ipaddress.ip_address("1.2.3.4"))
        self.assertEqual(
            _get_ip_from_xff(
                "1.2.3.4, 5.6.7.8, 10.0.0.1", trusted_ips, trusted_subnets
            ),
            "1.2.3.4",
        )

    def test_malformed_ips_in_xff(self):
        trusted_ips = {ipaddress.ip_address("5.6.7.8")}
        trusted_subnets = []
        # Rightmost is valid trusted proxy, next is invalid IP.
        # `_is_trusted_proxy_ip` handles ValueError and returns False, so the invalid IP is treated as untrusted.
        # Thus, it returns the invalid IP string.
        self.assertEqual(
            _get_ip_from_xff(
                "1.2.3.4, invalid_ip, 5.6.7.8", trusted_ips, trusted_subnets
            ),
            "invalid_ip",
        )


class PhotoResizerTests(TestCase):
    def test_resize_rgb_image(self):
        # Create a dummy RGB image of size 800x600
        image = Image.new("RGB", (800, 600))
        target_size = 400

        output = photo_resizer(image, size=target_size)

        # Verify output is a BytesIO object
        self.assertIsInstance(output, BytesIO)

        # Load the output back into an Image to verify properties
        result_image = Image.open(output)

        # Verify the format is JPEG
        self.assertEqual(result_image.format, "JPEG")

        # Verify the dimensions (aspect ratio should be preserved)
        # thumbnail((400, 400)) on 800x600 should yield 400x300
        self.assertEqual(result_image.size, (400, 300))

    def test_resize_rgba_image(self):
        # Create a dummy RGBA image to test mode conversion
        image = Image.new("RGBA", (1000, 1000))
        target_size = 500

        output = photo_resizer(image, size=target_size)

        self.assertIsInstance(output, BytesIO)

        result_image = Image.open(output)
        self.assertEqual(result_image.format, "JPEG")
        self.assertEqual(result_image.size, (500, 500))

    def test_resize_p_image(self):
        # Create a dummy P (palette) image to test mode conversion
        image = Image.new("P", (600, 800))
        target_size = 300

        output = photo_resizer(image, size=target_size)

        self.assertIsInstance(output, BytesIO)

        result_image = Image.open(output)
        self.assertEqual(result_image.format, "JPEG")
        # thumbnail((300, 300)) on 600x800 should yield 225x300
        self.assertEqual(result_image.size, (225, 300))

    def test_resize_image_with_exif_orientation(self):
        # Create a dummy RGB image of size 800x600
        image = Image.new("RGB", (800, 600))

        # Set EXIF orientation to 6 (Rotated 90 degrees counter-clockwise, meaning it needs 270 degrees CW rotation)
        exif = image.getexif()
        exif[274] = 6
        image.info["exif"] = exif.tobytes()

        target_size = 400

        output = photo_resizer(image, size=target_size)
        self.assertIsInstance(output, BytesIO)

        result_image = Image.open(output)
        self.assertEqual(result_image.format, "JPEG")

        # thumbnail((400, 400)) on 800x600 yields 400x300.
        # But due to EXIF orientation 6, exif_transpose will rotate it, swapping width and height.
        # So the result should be 300x400.
        self.assertEqual(result_image.size, (300, 400))

    def test_resize_l_image(self):
        # Create a dummy L (grayscale) image
        image = Image.new("L", (800, 600))
        target_size = 400

        output = photo_resizer(image, size=target_size)
        self.assertIsInstance(output, BytesIO)

        result_image = Image.open(output)
        self.assertEqual(result_image.format, "JPEG")
        self.assertEqual(result_image.size, (400, 300))

    def test_resize_la_image(self):
        # Create a dummy LA (grayscale with alpha) image to test mode conversion
        image = Image.new("LA", (800, 600))
        target_size = 400

        output = photo_resizer(image, size=target_size)
        self.assertIsInstance(output, BytesIO)

        result_image = Image.open(output)
        self.assertEqual(result_image.format, "JPEG")
        self.assertEqual(result_image.size, (400, 300))


class ClientIpKeyTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_with_remote_addr(self):
        request = self.factory.get("/", REMOTE_ADDR="1.2.3.4")
        self.assertEqual(client_ip_key(None, request), "1.2.3.4")

    def test_no_remote_addr(self):
        request = self.factory.get("/")
        if "REMOTE_ADDR" in request.META:
            del request.META["REMOTE_ADDR"]
        self.assertEqual(client_ip_key(None, request), "unknown")

    def test_with_none_request(self):
        self.assertEqual(client_ip_key(None, None), "unknown")


class CurrentYearTests(TestCase):
    @patch("base.utils.date")
    def test_current_year(self, mock_date):
        # Set a fixed date for today()
        mock_date.today.return_value = date(2025, 1, 15)
        self.assertEqual(current_year(), 2025)

        # Test another year
        mock_date.today.return_value = date(1999, 12, 31)
        self.assertEqual(current_year(), 1999)


class DirectoryPathTests(TestCase):
    def test_project_directory_path(self):
        from unittest.mock import MagicMock

        instance = MagicMock()
        instance.slug = "my-project"
        path = project_directory_path(instance, "test.jpg")
        self.assertEqual(path, "projects/my-project/test.jpg")

    def test_portfolio_directory_path(self):
        from unittest.mock import MagicMock

        instance = MagicMock()
        instance.project.slug = "my-project"
        path = portfolio_directory_path(instance, "test.jpg")
        self.assertEqual(path, "projects/my-project/photos/test.jpg")


class HealthCheckMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = HealthCheckMiddleware(
            lambda r: JsonResponse({"response": "chain"})
        )

    def test_ping_returns_pong(self):
        request = self.factory.get("/ping")
        response = self.middleware(request)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"response": "pong!"})

    def test_other_path_not_intercepted(self):
        request = self.factory.get("/some-other-path")
        response = self.middleware(request)
        # It should return the response from the chain
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(json.loads(response.content), {"response": "chain"})

    def test_ping_invalid_host(self):
        request = self.factory.get("/ping", HTTP_HOST="badhost.com")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)

    @patch.object(
        RequestFactory().get("/ping").__class__, "get_host", side_effect=DisallowedHost
    )
    def test_ping_disallowed_host_exception(self, mock_get_host):
        request = self.factory.get("/ping")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)

    def test_ping_post_returns_pong(self):
        request = self.factory.post("/ping")
        response = self.middleware(request)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"response": "pong!"})

    def test_integration_ping(self):
        client = Client()
        response = client.get("/ping")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"response": "pong!"})

    def test_integration_ping_post(self):
        client = Client()
        response = client.post("/ping")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"response": "pong!"})


class RateLimitHMACTest(TestCase):
    def test_hexdigest_returns_correct_hash(self):
        # We just need to check if the generated hash correctly matches what hmac.new creates
        import hashlib
        import hmac

        from django.conf import settings

        value = b"127.0.0.1"
        expected_digest = hmac.new(
            key=settings.SECRET_KEY.encode("utf-8"),
            msg=value,
            digestmod=hashlib.sha256,
        ).hexdigest()

        rate_limit_hmac = RateLimitHMAC(value)
        self.assertEqual(rate_limit_hmac.hexdigest(), expected_digest)

    @override_settings(SECRET_KEY="test_secret")
    def test_hexdigest_uses_secret_key(self):
        import hashlib
        import hmac

        value = b"test_value"
        expected_digest = hmac.new(
            key=b"test_secret",
            msg=value,
            digestmod=hashlib.sha256,
        ).hexdigest()

        rate_limit_hmac = RateLimitHMAC(value)
        self.assertEqual(rate_limit_hmac.hexdigest(), expected_digest)

    def test_hexdigest_different_values_produce_different_hashes(self):
        value1 = b"127.0.0.1"
        value2 = b"192.168.1.1"

        hmac1 = RateLimitHMAC(value1)
        hmac2 = RateLimitHMAC(value2)

        self.assertNotEqual(hmac1.hexdigest(), hmac2.hexdigest())
