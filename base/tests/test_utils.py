import ipaddress
from io import BytesIO

from django.test import RequestFactory, TestCase, override_settings
from PIL import Image

from base.utils import get_client_ip, photo_resizer


class GetClientIPTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_no_remote_addr(self):
        request = self.factory.get('/')
        # RequestFactory.get() might set REMOTE_ADDR to 127.0.0.1 by default
        if 'REMOTE_ADDR' in request.META:
            del request.META['REMOTE_ADDR']
        self.assertIsNone(get_client_ip(request))

    @override_settings(TRUSTED_PROXY_NETS=[])
    def test_untrusted_proxy_returns_remote_addr(self):
        request = self.factory.get('/', REMOTE_ADDR='1.2.3.4', HTTP_X_FORWARDED_FOR='5.6.7.8')
        self.assertEqual(get_client_ip(request), '1.2.3.4')

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network('127.0.0.1/32')])
    def test_trusted_proxy_no_xff(self):
        request = self.factory.get('/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(get_client_ip(request), '127.0.0.1')

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network('127.0.0.1/32')])
    def test_trusted_proxy_with_xff(self):
        request = self.factory.get('/', REMOTE_ADDR='127.0.0.1', HTTP_X_FORWARDED_FOR='5.6.7.8')
        self.assertEqual(get_client_ip(request), '5.6.7.8')

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network('127.0.0.1/32')])
    def test_trusted_proxy_with_multiple_xff(self):
        request = self.factory.get('/', REMOTE_ADDR='127.0.0.1', HTTP_X_FORWARDED_FOR='5.6.7.8, 9.10.11.12')
        self.assertEqual(get_client_ip(request), '5.6.7.8')

    @override_settings(TRUSTED_PROXY_NETS=[ipaddress.ip_network('192.168.1.0/24')])
    def test_trusted_network_range(self):
        request = self.factory.get('/', REMOTE_ADDR='192.168.1.50', HTTP_X_FORWARDED_FOR='10.0.0.1')
        self.assertEqual(get_client_ip(request), '10.0.0.1')

    def test_trusted_proxy_nets_not_set(self):
        # Ensure it works when TRUSTED_PROXY_NETS is not in settings
        with self.settings(TRUSTED_PROXY_NETS=None):
            request = self.factory.get('/', REMOTE_ADDR='127.0.0.1', HTTP_X_FORWARDED_FOR='5.6.7.8')
            self.assertEqual(get_client_ip(request), '127.0.0.1')


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
