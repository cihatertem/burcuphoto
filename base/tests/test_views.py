from io import BytesIO

from django.contrib.messages import get_messages
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from base.models import Project, ProjectPortfolio
from base.views import (
    CAPTCHA_ANS_KEY,
    CAPTCHA_NUM1_KEY,
    CAPTCHA_NUM2_KEY,
    _generate_captcha,
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


class ContactViewTest(TestCase):
    @override_settings(
        RATELIMIT_ENABLE=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_contact_post_honeypot(self):
        """Test that submitting the contact form with honeypot field filled redirects with success but sends no email."""
        session = self.client.session
        session[CAPTCHA_NUM1_KEY] = 5
        session[CAPTCHA_NUM2_KEY] = 3
        session[CAPTCHA_ANS_KEY] = 8
        session.save()

        post_data = {
            "name": "Spam Bot",
            "email": "bot@example.com",
            "message": "Buy cheap stuff!",
            "website": "http://spam.com",  # filled honeypot
            "captcha": "8",
        }

        response = self.client.post(reverse("base:contact"), data=post_data)

        # Confirm the form submission redirected back to the home page silently
        self.assertRedirects(response, reverse("base:home"))

        # Check that no email was sent
        self.assertEqual(len(mail.outbox), 0)

        # Check that the success message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Your message was sent successfully.\nThank you!"
        )
        self.assertEqual(messages[0].level_tag, "success")

    @override_settings(
        RATELIMIT_ENABLE=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_contact_post_sends_email_synchronously(self):
        """Test that posting to the Contact view sends an email synchronously without using a thread."""
        session = self.client.session
        session[CAPTCHA_NUM1_KEY] = 5
        session[CAPTCHA_NUM2_KEY] = 3
        session[CAPTCHA_ANS_KEY] = 8
        session.save()

        post_data = {
            "name": "Test User",
            "email": "test@example.com",
            "message": "Hello, this is a test.",
            "website": "",  # empty for honeypot
            "captcha": "8",
        }

        response = self.client.post(reverse("base:contact"), data=post_data)

        # Confirm the form submission redirected successfully
        self.assertRedirects(response, reverse("base:home"))

        # Check that exactly one email was sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "Web Site Visitor")
        self.assertIn("Hello, this is a test.", email.body)
        self.assertEqual(email.reply_to, ["test@example.com"])

    @override_settings(
        RATELIMIT_ENABLE=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_contact_post_incorrect_captcha(self):
        """Test that submitting the contact form with an incorrect captcha redirects with an error."""
        session = self.client.session
        session[CAPTCHA_NUM1_KEY] = 5
        session[CAPTCHA_NUM2_KEY] = 3
        session[CAPTCHA_ANS_KEY] = 8
        session.save()

        post_data = {
            "name": "Test User",
            "email": "test@example.com",
            "message": "Hello, this is a test.",
            "website": "",  # empty for honeypot
            "captcha": "9",  # incorrect captcha
        }

        response = self.client.post(reverse("base:contact"), data=post_data)

        # Confirm the form submission redirected back to the contact page
        self.assertRedirects(response, reverse("base:contact"))

        # Check that no email was sent
        self.assertEqual(len(mail.outbox), 0)

        # Check that the error message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Captcha incorrect. Please try again.")
        self.assertEqual(messages[0].level_tag, "error")

    @override_settings(RATELIMIT_ENABLE=True)
    def test_contact_rate_limit(self):
        """Test that submitting the form too many times triggers the rate limit."""
        # Ensure cache is clear so rate limits are reset
        cache.clear()

        post_data = {
            "name": "Test User",
            "email": "test@example.com",
            "message": "Hello, this is a test.",
            "website": "",
            "captcha": "8",
        }

        # The limit is 2/m, so the first two requests should go through
        self.client.post(
            reverse("base:contact"), data=post_data, REMOTE_ADDR="127.0.0.1"
        )
        self.client.post(
            reverse("base:contact"), data=post_data, REMOTE_ADDR="127.0.0.1"
        )

        # The 3rd request should be rate limited
        response = self.client.post(
            reverse("base:contact"),
            data=post_data,
            REMOTE_ADDR="127.0.0.1",
            follow=True,
        )

        self.assertRedirects(response, reverse("base:contact"))
        messages = [str(m) for m in response.context["messages"]]
        self.assertIn(
            "Çok fazla istek gönderdiniz. Lütfen biraz sonra tekrar deneyin.", messages
        )


class ImageTestMixin:
    def _create_image(self, width, height, filename="test.jpg"):
        """Creates a dummy image and returns it as a SimpleUploadedFile."""
        file = BytesIO()
        image = Image.new("RGB", (width, height), "white")
        image.save(file, "jpeg")
        file.seek(0)
        return SimpleUploadedFile(filename, file.read(), content_type="image/jpeg")


class ProjectModelTest(ImageTestMixin, TestCase):
    def test_project_save_image_resizing(self):
        """Test that images larger than 780px are resized to 780px when saved."""
        large_image = self._create_image(1000, 1000)
        project = Project.objects.create(
            title="Test Resizing Project",
            slug="test-resizing",
            featured_photo=large_image,
        )

        # Open the saved image to verify dimensions
        with Image.open(project.featured_photo) as img:
            self.assertEqual(img.width, 780)
            self.assertEqual(img.height, 780)

    def test_project_save_image_no_resizing(self):
        """Test that images smaller than or equal to 780px are not resized."""
        small_image = self._create_image(500, 500)
        project = Project.objects.create(
            title="Test No Resizing Project",
            slug="test-no-resizing",
            featured_photo=small_image,
        )

        # Open the saved image to verify dimensions
        with Image.open(project.featured_photo) as img:
            self.assertEqual(img.width, 500)
            self.assertEqual(img.height, 500)

    def test_project_save_link_draft(self):
        """Test that project_link is correctly generated when draft is True."""
        small_image = self._create_image(500, 500)
        project = Project.objects.create(
            title="Draft Project",
            slug="draft-project",
            featured_photo=small_image,
            draft=True,
        )
        self.assertEqual(
            project.project_link, "https://burcuatak.com/draft/draft-project/"
        )

    def test_project_save_link_not_draft(self):
        """Test that project_link is correctly generated when draft is False."""
        small_image = self._create_image(500, 500)
        project = Project.objects.create(
            title="Published Project",
            slug="published-project",
            featured_photo=small_image,
            draft=False,
        )
        self.assertEqual(
            project.project_link, "https://burcuatak.com/portfolio/published-project/"
        )


class ProjectPortfolioModelTest(ImageTestMixin, TestCase):
    def setUp(self):
        small_image = self._create_image(10, 10)
        self.project = Project.objects.create(
            title="Parent Project",
            slug="parent-project",
            featured_photo=small_image,
        )

    def test_project_portfolio_save_image_resizing(self):
        """Test that ProjectPortfolio images larger than 780px are resized to 780px when saved."""
        large_image = self._create_image(1000, 1000)
        portfolio = ProjectPortfolio.objects.create(
            project=self.project,
            photo=large_image,
        )

        # Open the saved image to verify dimensions
        with Image.open(portfolio.photo) as img:
            self.assertEqual(img.width, 780)
            self.assertEqual(img.height, 780)

    def test_project_portfolio_save_image_no_resizing(self):
        """Test that ProjectPortfolio images smaller than or equal to 780px are not resized."""
        small_image = self._create_image(500, 500)
        portfolio = ProjectPortfolio.objects.create(
            project=self.project,
            photo=small_image,
        )

        # Open the saved image to verify dimensions
        with Image.open(portfolio.photo) as img:
            self.assertEqual(img.width, 500)
            self.assertEqual(img.height, 500)
