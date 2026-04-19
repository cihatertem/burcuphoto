import os

from django.contrib.messages import get_messages
from django.contrib.sessions.middleware import SessionMiddleware
from django.core import mail
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from base.views import (
    CAPTCHA_ANS_KEY,
    CAPTCHA_NUM1_KEY,
    CAPTCHA_NUM2_KEY,
    _generate_captcha,
)


class CaptchaSecurityTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _get_request_with_session(self):
        request = self.factory.get("/contact")
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
            results.add(
                (request.session[CAPTCHA_NUM1_KEY], request.session[CAPTCHA_NUM2_KEY])
            )

        # There are 10*10 = 100 possible combinations.
        # We should see more than one unique combination in 100 trials.
        self.assertGreater(len(results), 1)


class ContactViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("base:contact")

        # Initialize session by making a GET request first
        self.client.get(self.url)

    def set_captcha_session(self, ans=8):
        session = self.client.session
        session[CAPTCHA_NUM1_KEY] = 5
        session[CAPTCHA_NUM2_KEY] = 3
        session[CAPTCHA_ANS_KEY] = ans
        session.save()

    def test_contact_post_happy_path(self):
        """Test valid contact form submission sends an email and redirects with success message."""
        self.set_captcha_session(ans=8)

        data = {
            "name": "Test User",
            "email": "test@example.com",
            "message": "This is a test message.",
            "website": "",  # Honeypot empty
            "captcha": "8",
        }

        response = self.client.post(self.url, data)

        # Verify redirect to home
        self.assertRedirects(response, reverse("base:home"))

        # Verify email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("This is a test message.", mail.outbox[0].body)
        self.assertIn("test@example.com", mail.outbox[0].body)

        # Verify captcha was removed from session
        session = self.client.session
        self.assertNotIn(CAPTCHA_ANS_KEY, session)

    def test_contact_post_honeypot_filled(self):
        """Test if honeypot field is filled, bot is assumed, no email sent, but returns success."""
        self.set_captcha_session(ans=8)

        data = {
            "name": "Bot User",
            "email": "bot@example.com",
            "message": "Spam message.",
            "website": "http://spam.com",  # Honeypot filled
            "captcha": "8",
        }

        response = self.client.post(self.url, data)

        # Verify redirect to home
        self.assertRedirects(response, reverse("base:home"))

        # Verify no email sent
        self.assertEqual(len(mail.outbox), 0)

    def test_contact_post_incorrect_captcha(self):
        """Test incorrect captcha redirects back to contact with error message."""
        self.set_captcha_session(ans=8)

        data = {
            "name": "Test User",
            "email": "test@example.com",
            "message": "This is a test message.",
            "website": "",
            "captcha": "9",  # Incorrect
        }

        response = self.client.post(self.url, data)

        # Verify redirect back to contact
        self.assertRedirects(response, self.url)

        # Verify no email sent
        self.assertEqual(len(mail.outbox), 0)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Captcha incorrect. Please try again.")

    def test_contact_post_missing_captcha_session(self):
        """Test missing captcha session data redirects back to contact with error message."""
        # Intentionally not setting session data for captcha
        session = self.client.session
        session.pop(CAPTCHA_ANS_KEY, None)
        session.save()

        data = {
            "name": "Test User",
            "email": "test@example.com",
            "message": "This is a test message.",
            "website": "",
            "captcha": "8",
        }

        response = self.client.post(self.url, data)

        self.assertRedirects(response, self.url)
        self.assertEqual(len(mail.outbox), 0)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Captcha incorrect. Please try again.")

    def test_contact_post_rate_limited(self):
        """Test rate limited request redirects back with error."""
        self.set_captcha_session(ans=8)

        data = {
            "name": "Test User",
            "email": "test@example.com",
            "message": "This is a test message.",
            "website": "",
            "captcha": "8",
        }

        from django.test import RequestFactory

        from base.views import Contact

        factory = RequestFactory()
        request = factory.post(self.url, data)
        request.limited = True

        # We need session and messages framework for the view to work
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

        msg_middleware = MessageMiddleware(lambda req: None)
        msg_middleware.process_request(request)

        view = Contact.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(len(mail.outbox), 0)

        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Çok fazla istek gönderdiniz. Lütfen biraz sonra tekrar deneyin.",
        )
