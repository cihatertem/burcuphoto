import base64
from io import BytesIO
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from PIL import Image

from base.captcha import (
    CAPTCHA_ANS_KEY,
    CAPTCHA_NUM1_KEY,
    CAPTCHA_NUM2_KEY,
    _generate_captcha,
    _generate_captcha_image_base64,
    _parse_int,
    captcha_is_valid,
)


class CaptchaTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_generate_captcha(self):
        request = self.factory.get("/")
        # Manually add session to request
        request.session = {}

        _generate_captcha(request)

        n1 = request.session.get(CAPTCHA_NUM1_KEY)
        n2 = request.session.get(CAPTCHA_NUM2_KEY)
        ans = request.session.get(CAPTCHA_ANS_KEY)

        self.assertIsInstance(n1, int)
        self.assertIsInstance(n2, int)
        self.assertIsInstance(ans, int)
        self.assertTrue(1 <= n1 <= 10)
        self.assertTrue(1 <= n2 <= 10)
        self.assertEqual(ans, n1 + n2)

    @patch("base.captcha.secrets.randbelow", side_effect=[0] * 20)
    def test_generate_captcha_image_base64_returns_png_image(self, _mock_randbelow):
        captcha_image_b64 = _generate_captcha_image_base64(5, 3)

        image_bytes = base64.b64decode(captcha_image_b64, validate=True)
        self.assertTrue(image_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

        with Image.open(BytesIO(image_bytes)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.mode, "L")
            self.assertEqual(image.size, (120, 40))

            colors = image.getcolors(maxcolors=120 * 40)
            self.assertIsNotNone(colors)
            self.assertGreater(len(colors), 1)

    def test_parse_int(self):
        self.assertEqual(_parse_int("123"), 123)
        self.assertEqual(_parse_int(123), 123)
        self.assertIsNone(_parse_int("abc"))
        self.assertIsNone(_parse_int(""))
        self.assertIsNone(_parse_int(None))
        self.assertIsNone(_parse_int([1, 2]))
        self.assertIsNone(_parse_int({"a": 1}))

    def test_captcha_is_valid_success(self):
        request = self.factory.post("/", {"captcha": "15"})
        request.session = {CAPTCHA_ANS_KEY: 15}
        self.assertTrue(captcha_is_valid(request))

    def test_captcha_is_valid_fail_wrong_answer(self):
        request = self.factory.post("/", {"captcha": "10"})
        request.session = {CAPTCHA_ANS_KEY: 15}
        self.assertFalse(captcha_is_valid(request))

    def test_captcha_is_valid_fail_missing_post_data(self):
        request = self.factory.post("/")
        request.session = {CAPTCHA_ANS_KEY: 15}
        self.assertFalse(captcha_is_valid(request))

    def test_captcha_is_valid_fail_missing_session_data(self):
        request = self.factory.post("/", {"captcha": "15"})
        request.session = {}
        self.assertFalse(captcha_is_valid(request))

    def test_captcha_is_valid_fail_invalid_post_data_string(self):
        request = self.factory.post("/", {"captcha": "abc"})
        request.session = {CAPTCHA_ANS_KEY: 15}
        self.assertFalse(captcha_is_valid(request))

    def test_captcha_is_valid_fail_invalid_session_data_string(self):
        request = self.factory.post("/", {"captcha": "15"})
        request.session = {CAPTCHA_ANS_KEY: "abc"}
        self.assertFalse(captcha_is_valid(request))

    def test_captcha_is_valid_fail_both_missing(self):
        request = self.factory.post("/")
        request.session = {}
        self.assertFalse(captcha_is_valid(request))

    def test_captcha_is_valid_fail_both_invalid(self):
        request = self.factory.post("/", {"captcha": "def"})
        request.session = {CAPTCHA_ANS_KEY: "abc"}
        self.assertFalse(captcha_is_valid(request))
