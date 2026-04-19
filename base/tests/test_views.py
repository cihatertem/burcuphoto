from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from base.views import _generate_captcha, CAPTCHA_NUM1_KEY, CAPTCHA_NUM2_KEY, CAPTCHA_ANS_KEY

# Create your tests here.

class CaptchaSecurityTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request_with_session(self):
        request = self.factory.get('/contact')
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_generate_captcha_values_range(self):
        request = self._get_request_with_session()
        for _ in range(100):
            _generate_captcha(request)
            n1 = request.session[CAPTCHA_NUM1_KEY]
            n2 = request.session[CAPTCHA_NUM2_KEY]
            ans = request.session[CAPTCHA_ANS_KEY]

            self.assertTrue(1 <= n1 <= 10)
            self.assertTrue(1 <= n2 <= 10)
            self.assertEqual(ans, n1 + n2)

    def test_generate_captcha_is_random(self):
        # This is a bit non-deterministic but with 100 trials,
        # identical results should be extremely rare if it's random.
        request = self._get_request_with_session()
        results = set()
        for _ in range(100):
            _generate_captcha(request)
            results.add((request.session[CAPTCHA_NUM1_KEY], request.session[CAPTCHA_NUM2_KEY]))

        # There are 10*10 = 100 possible combinations.
        # We should see more than one unique combination in 100 trials.
        self.assertGreater(len(results), 1)

