import base64
from io import BytesIO
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from base.captcha import CAPTCHA_ANS_KEY, CAPTCHA_NUM1_KEY, CAPTCHA_NUM2_KEY
from base.models import Project, ProjectPortfolio
from base.tests.mixins import ImageTestMixin
from base.utils import current_year
from base.views import (
    Contact,
    DraftDetail,
    DraftList,
    PortfolioDetail,
    PortfolioList,
    YearContext,
)


class ContactViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("base.views._generate_captcha_image_base64")
    def test_contact_get_context_data(self, mock_generate):
        mock_generate.return_value = "fake_base64"
        view = Contact()
        view.request = self.factory.get("/")
        view.request.session = {CAPTCHA_NUM1_KEY: 5, CAPTCHA_NUM2_KEY: 3}

        ctx = view.get_context_data()

        mock_generate.assert_called_once_with(5, 3)
        self.assertEqual(ctx["captcha_image_b64"], "fake_base64")

    @patch("base.views._generate_captcha_image_base64")
    def test_contact_get_context_data_missing_session_keys(self, mock_generate):
        mock_generate.return_value = "fake_base64_0"
        view = Contact()
        view.request = self.factory.get("/")
        view.request.session = {}

        ctx = view.get_context_data()

        mock_generate.assert_called_once_with(0, 0)
        self.assertEqual(ctx["captcha_image_b64"], "fake_base64_0")

    @patch("base.captcha.secrets.randbelow", side_effect=[4, 2, *([0] * 20)])
    def test_contact_get_generates_captcha_and_renders_image(self, _mock_randbelow):
        response = self.client.get(reverse("base:contact"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session[CAPTCHA_NUM1_KEY], 5)
        self.assertEqual(self.client.session[CAPTCHA_NUM2_KEY], 3)
        self.assertEqual(self.client.session[CAPTCHA_ANS_KEY], 8)

        captcha_image_b64 = response.context["captcha_image_b64"]
        image_bytes = base64.b64decode(captcha_image_b64, validate=True)
        with Image.open(BytesIO(image_bytes)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (120, 40))

        html = response.content.decode()
        self.assertIn(
            f'src="data:image/png;base64,{captcha_image_b64}"',
            html,
        )
        self.assertIn('alt="CAPTCHA Image"', html)
        self.assertNotIn("5 + 3", html)

    @override_settings(
        RATELIMIT_ENABLE=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    @patch("os.getenv")
    def test_contact_post_email_receiver_env_fallback(self, mock_getenv):
        """Test that if EMAIL_RECEIVER_ONE and EMAIL_RECEIVER_TWO are missing, the email still initializes and is sent."""
        import os

        # mock os.getenv to return None for email receivers, otherwise default to actual os.environ
        mock_getenv.side_effect = lambda key: (
            None if "EMAIL_RECEIVER" in key else os.environ.get(key)
        )

        session = self.client.session
        session[CAPTCHA_NUM1_KEY] = 5
        session[CAPTCHA_NUM2_KEY] = 3
        session[CAPTCHA_ANS_KEY] = 8
        session.save()

        post_data = {
            "name": "Env Test User",
            "email": "envtest@example.com",
            "message": "Testing env fallback.",
            "website": "",  # empty for honeypot
            "captcha": "8",
        }

        with patch("base.views.email_executor.submit", autospec=True) as mock_submit:

            def side_effect(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_submit.side_effect = side_effect

            response = self.client.post(reverse("base:contact"), data=post_data)

        # Confirm the form submission redirected successfully
        self.assertRedirects(response, reverse("base:home"))

        # If both env vars are None, EmailMessage.to is [None, None].
        # msg.recipients() filters out empty values, so it will be an empty list.
        # EmailMessage.send() returns 0 and does not use the connection if there are no recipients.
        # Therefore, mail.outbox will be empty.
        self.assertEqual(len(mail.outbox), 0)

        # Check that the success message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Your message was sent successfully.\nWe will touch you back soon.",
        )
        self.assertEqual(messages[0].level_tag, "success")

    @override_settings(
        RATELIMIT_ENABLE=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    @patch("os.getenv")
    def test_contact_post_email_receiver_env_partial_fallback(self, mock_getenv):
        """Test that if only one EMAIL_RECEIVER is present, the email is sent to that receiver."""
        import os

        mock_getenv.side_effect = lambda key: (
            "admin@example.com"
            if key == "EMAIL_RECEIVER_ONE"
            else (None if key == "EMAIL_RECEIVER_TWO" else os.environ.get(key))
        )

        session = self.client.session
        session[CAPTCHA_NUM1_KEY] = 5
        session[CAPTCHA_NUM2_KEY] = 3
        session[CAPTCHA_ANS_KEY] = 8
        session.save()

        post_data = {
            "name": "Env Test User 2",
            "email": "envtest2@example.com",
            "message": "Testing env fallback partial.",
            "website": "",  # empty for honeypot
            "captcha": "8",
        }

        with patch("base.views.email_executor.submit", autospec=True) as mock_submit:

            def side_effect(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_submit.side_effect = side_effect

            response = self.client.post(reverse("base:contact"), data=post_data)

        # Confirm the form submission redirected successfully
        self.assertRedirects(response, reverse("base:home"))

        # Check that exactly one email was sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.subject, "Web Site Visitor")
        self.assertEqual(email.to, ["admin@example.com", None])

    @override_settings(
        RATELIMIT_ENABLE=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_contact_post_email_html_injection(self):
        """Test that submitting the contact form with HTML tags prevents HTML injection."""
        session = self.client.session
        session[CAPTCHA_NUM1_KEY] = 5
        session[CAPTCHA_NUM2_KEY] = 3
        session[CAPTCHA_ANS_KEY] = 8
        session.save()

        post_data = {
            "name": "<script>alert('name')</script>",
            "email": "test@example.com",
            "message": "<b>Hello</b>, this is a test.",
            "website": "",  # empty for honeypot
            "captcha": "8",
        }

        # Patch the submit method to directly execute the function synchronously for the test
        with patch("base.views.email_executor.submit", autospec=True) as mock_submit:

            def side_effect(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_submit.side_effect = side_effect

            response = self.client.post(reverse("base:contact"), data=post_data)

        # Confirm the form submission succeeded
        self.assertRedirects(response, reverse("base:home"))

        # Verify email was constructed correctly
        from django.core.mail import outbox

        self.assertEqual(len(outbox), 1)
        self.assertIn(
            "&lt;script&gt;alert(&#x27;name&#x27;)&lt;/script&gt;", outbox[0].body
        )
        self.assertIn("&lt;b&gt;Hello&lt;/b&gt;", outbox[0].body)
        self.assertNotIn("<script>", outbox[0].body)
        self.assertNotIn("<b>", outbox[0].body)

    @override_settings(
        RATELIMIT_ENABLE=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_contact_post_email_header_injection(self):
        """Test that submitting the contact form with newlines in the email field prevents header injection."""
        session = self.client.session
        session[CAPTCHA_NUM1_KEY] = 5
        session[CAPTCHA_NUM2_KEY] = 3
        session[CAPTCHA_ANS_KEY] = 8
        session.save()

        post_data = {
            "name": "Test User\nBcc: attacker@example.com",
            "email": "test@example.com",
            "message": "Hello, this is a test.",
            "website": "",  # empty for honeypot
            "captcha": "8",
        }

        # Validate_email blocks test\n@example.com.
        # Instead of directly raising BadHeaderError, since subject is generated as
        # "Web Site Visitor" without user input, we use a mock to raise it to verify
        # that the exception handling works as intended in the view.
        with patch.object(Contact, "_send_contact_email") as mock_send:
            from django.core.mail import BadHeaderError

            mock_send.side_effect = BadHeaderError("Invalid header found.")
            response = self.client.post(reverse("base:contact"), data=post_data)

        # Confirm the form submission redirected back to the contact page
        self.assertRedirects(response, reverse("base:contact"))

        # Check that the error message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invalid header found.")
        self.assertEqual(messages[0].level_tag, "error")

    @patch("base.views.validate_email")
    def test_is_email_invalid_raises_validation_error(self, mock_validate_email):
        """Test that _is_email_invalid returns True and adds an error message when a ValidationError occurs."""
        mock_validate_email.side_effect = ValidationError("Invalid email")

        view = Contact()
        request = self.factory.get("/")
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        result = view._is_email_invalid(request, "invalid-email")

        self.assertTrue(result)
        mock_validate_email.assert_called_once_with("invalid-email")

        messages_list = list(messages)
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Invalid email address.")
        self.assertEqual(messages_list[0].level_tag, "error")

    @override_settings(
        RATELIMIT_ENABLE=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_contact_post_invalid_email(self):
        """Test that submitting the contact form with an invalid email redirects with an error."""
        session = self.client.session
        session[CAPTCHA_NUM1_KEY] = 5
        session[CAPTCHA_NUM2_KEY] = 3
        session[CAPTCHA_ANS_KEY] = 8
        session.save()

        post_data = {
            "name": "Test User",
            "email": "invalid-email",
            "message": "Hello, this is a test.",
            "website": "",  # empty for honeypot
            "captcha": "8",
        }

        response = self.client.post(reverse("base:contact"), data=post_data)

        # Confirm the form submission redirected back to the contact page
        self.assertRedirects(response, reverse("base:contact"))

        # Check that no email was sent
        self.assertEqual(len(mail.outbox), 0)

        # Check that the error message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invalid email address.")
        self.assertEqual(messages[0].level_tag, "error")

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
    def test_contact_post_sends_email_asynchronously(self):
        """Test that posting to the Contact view sends an email asynchronously using a thread."""
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

        # Patch the submit method to directly execute the function synchronously for the test
        with patch("base.views.email_executor.submit", autospec=True) as mock_submit:

            def side_effect(func, *args, **kwargs):
                return func(*args, **kwargs)

            mock_submit.side_effect = side_effect

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


class PortfolioListTest(ImageTestMixin, TestCase):
    def setUp(self):
        self.draft_project = Project.objects.create(
            title="Draft Project",
            slug="draft-project",
            draft=True,
            featured_photo=self._create_image(100, 100),
        )
        self.published_project = Project.objects.create(
            title="Published Project",
            slug="published-project",
            draft=False,
            featured_photo=self._create_image(100, 100),
        )

    def test_get_queryset_filters_drafts(self):
        view = PortfolioList()
        view.kwargs = {}
        qs = view.get_queryset()

        self.assertEqual(qs.count(), 1)
        self.assertIn(self.published_project, qs)
        self.assertNotIn(self.draft_project, qs)

        # also test view via client
        response = self.client.get(reverse("base:portfolio"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.published_project, response.context["object_list"])
        self.assertNotIn(self.draft_project, response.context["object_list"])

    def test_get_queryset_queries_count(self):
        # Create some portfolios to ensure they are fetched
        ProjectPortfolio.objects.create(
            project=self.published_project,
            photo=self._create_image(10, 10),
            index=1,
        )
        ProjectPortfolio.objects.create(
            project=self.published_project,
            photo=self._create_image(10, 10),
            index=2,
        )

        with self.assertNumQueries(1):
            view = PortfolioList()
            view.kwargs = {}
            qs = view.get_queryset()
            # Evaluate the queryset to trigger the DB queries
            list(qs)

    def test_portfolio_list_view_template(self):
        response = self.client.get(reverse("base:portfolio"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base/portfolio_list.html")

    def test_portfolio_list_view_context(self):
        response = self.client.get(reverse("base:portfolio"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("year", response.context)
        self.assertEqual(response.context["year"], current_year())

    def test_empty_list(self):
        # Delete all projects to test the empty list scenario
        Project.objects.all().delete()

        response = self.client.get(reverse("base:portfolio"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["object_list"]), [])


class PortfolioDetailTest(ImageTestMixin, TestCase):
    def setUp(self):
        self.draft_project = Project.objects.create(
            title="Draft Project Detail",
            slug="draft-project-detail",
            draft=True,
            featured_photo=self._create_image(100, 100),
        )
        self.published_project = Project.objects.create(
            title="Published Project Detail",
            slug="published-project-detail",
            draft=False,
            featured_photo=self._create_image(100, 100),
        )

    def test_get_queryset_filters_drafts_and_prefetches(self):
        view = PortfolioDetail()
        view.kwargs = {"slug": "published-project-detail"}
        qs = view.get_queryset()

        self.assertEqual(qs.count(), 1)
        self.assertIn(self.published_project, qs)
        self.assertNotIn(self.draft_project, qs)
        self.assertIn("projectportfolio_set", qs._prefetch_related_lookups)

        # also test view via client
        response = self.client.get(
            reverse(
                "base:portfolio_detail", kwargs={"slug": "published-project-detail"}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["object"], self.published_project)

        # draft project should return 404
        response_draft = self.client.get(
            reverse("base:portfolio_detail", kwargs={"slug": "draft-project-detail"})
        )
        self.assertEqual(response_draft.status_code, 404)

    def test_get_context_data_includes_portfolios(self):
        # Create related portfolio photos
        portfolio1 = ProjectPortfolio.objects.create(
            project=self.published_project,
            photo=self._create_image(100, 100),
            alt="photo 1",
            index=1,
        )
        portfolio2 = ProjectPortfolio.objects.create(
            project=self.published_project,
            photo=self._create_image(100, 100),
            alt="photo 2",
            index=2,
        )

        view = PortfolioDetail()
        request = RequestFactory().get("/")
        view.request = request
        # We must use the prefetch_related for context
        view.object = Project.objects.prefetch_related("projectportfolio_set").get(
            pk=self.published_project.pk
        )
        view.kwargs = {"slug": "published-project-detail"}

        context = view.get_context_data()

        self.assertIn("portfolios", context)
        portfolios = context["portfolios"]
        self.assertEqual(list(portfolios), [portfolio1, portfolio2])

    def test_get_queryset_queries_count(self):
        # Create some portfolios to ensure they are fetched
        ProjectPortfolio.objects.create(
            project=self.published_project,
            photo=self._create_image(10, 10),
            index=1,
        )
        ProjectPortfolio.objects.create(
            project=self.published_project,
            photo=self._create_image(10, 10),
            index=2,
        )

        with self.assertNumQueries(2):
            view = PortfolioDetail()
            view.kwargs = {"slug": "published-project-detail"}
            qs = view.get_queryset()
            # Evaluate the queryset to trigger the DB queries
            projects = list(qs)
            # Access related data to ensure no extra queries are fired
            for project in projects:
                list(project.projectportfolio_set.all())
        self.assertIn("projectportfolio_set", qs._prefetch_related_lookups)

    def test_portfolio_detail_view_template(self):
        response = self.client.get(
            reverse(
                "base:portfolio_detail", kwargs={"slug": "published-project-detail"}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base/portfolio_detail.html")

    def test_portfolio_detail_view_context(self):
        response = self.client.get(
            reverse(
                "base:portfolio_detail", kwargs={"slug": "published-project-detail"}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("year", response.context)
        self.assertEqual(response.context["year"], current_year())
        self.assertIn("portfolios", response.context)


class DraftListTest(ImageTestMixin, TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(
            username="testuser", password="password", is_staff=True
        )
        self.non_staff_user = User.objects.create_user(
            username="nonstaff", password="password"
        )

        self.draft_project = Project.objects.create(
            title="Draft Project",
            slug="draft-project",
            draft=True,
            featured_photo=self._create_image(100, 100),
        )
        self.published_project = Project.objects.create(
            title="Published Project",
            slug="published-project",
            draft=False,
            featured_photo=self._create_image(100, 100),
        )

    def test_get_queryset_filters_drafts(self):
        view = DraftList()
        view.kwargs = {}
        qs = view.get_queryset()

        self.assertEqual(qs.count(), 1)
        self.assertIn(self.draft_project, qs)
        self.assertNotIn(self.published_project, qs)

        # test via client authenticated
        self.client.login(username="testuser", password="password")
        response = self.client.get(reverse("base:draft"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.draft_project, response.context["object_list"])
        self.assertNotIn(self.published_project, response.context["object_list"])
        self.assertTemplateUsed(response, "base/portfolio_list.html")

    def test_draft_list_unauthenticated(self):
        response = self.client.get(reverse("base:draft"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_draft_list_non_staff(self):
        self.client.login(username="nonstaff", password="password")
        response = self.client.get(reverse("base:draft"))
        self.assertEqual(response.status_code, 403)

    def test_get_queryset_queries_count(self):
        ProjectPortfolio.objects.create(
            project=self.draft_project,
            photo=self._create_image(10, 10),
            index=1,
        )
        ProjectPortfolio.objects.create(
            project=self.draft_project,
            photo=self._create_image(10, 10),
            index=2,
        )

        with self.assertNumQueries(1):
            view = DraftList()
            view.kwargs = {}
            qs = view.get_queryset()
            list(qs)


class DraftDetailTest(ImageTestMixin, TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(
            username="testuser", password="password", is_staff=True
        )
        self.non_staff_user = User.objects.create_user(
            username="nonstaff", password="password"
        )

        self.draft_project = Project.objects.create(
            title="Draft Project Detail",
            slug="draft-project-detail",
            draft=True,
            featured_photo=self._create_image(100, 100),
        )
        self.published_project = Project.objects.create(
            title="Published Project Detail",
            slug="published-project-detail",
            draft=False,
            featured_photo=self._create_image(100, 100),
        )
        self.portfolio1 = ProjectPortfolio.objects.create(
            project=self.draft_project,
            photo=self._create_image(10, 10),
            index=1,
        )
        self.portfolio2 = ProjectPortfolio.objects.create(
            project=self.draft_project,
            photo=self._create_image(10, 10),
            index=2,
        )

    def test_get_queryset_filters_drafts_and_prefetches(self):
        view = DraftDetail()
        view.kwargs = {"slug": "draft-project-detail"}
        qs = view.get_queryset()

        self.assertEqual(qs.count(), 1)
        self.assertIn(self.draft_project, qs)
        self.assertNotIn(self.published_project, qs)
        self.assertIn("projectportfolio_set", qs._prefetch_related_lookups)

    def test_get_context_data_includes_portfolios(self):
        view = DraftDetail()
        view.object = Project.objects.prefetch_related("projectportfolio_set").get(
            pk=self.draft_project.pk
        )
        context = view.get_context_data()
        self.assertIn("portfolios", context)
        self.assertEqual(
            list(context["portfolios"]), [self.portfolio1, self.portfolio2]
        )

    def test_draft_detail_view_authenticated(self):
        self.client.login(username="testuser", password="password")
        response = self.client.get(
            reverse("base:draft_detail", kwargs={"slug": "draft-project-detail"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("portfolios", response.context)
        self.assertEqual(
            list(response.context["portfolios"]), [self.portfolio1, self.portfolio2]
        )
        self.assertEqual(response.context["object"], self.draft_project)

    def test_get_queryset_queries_count(self):
        # We already have self.portfolio1 and self.portfolio2 related to self.draft_project
        with self.assertNumQueries(2):
            view = DraftDetail()
            view.kwargs = {"slug": "draft-project-detail"}
            qs = view.get_queryset()
            projects = list(qs)
            for project in projects:
                list(project.projectportfolio_set.all())
        self.assertIn("projectportfolio_set", qs._prefetch_related_lookups)

    def test_draft_detail_view_unauthenticated(self):
        response = self.client.get(
            reverse("base:draft_detail", kwargs={"slug": "draft-project-detail"})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_draft_detail_view_non_staff(self):
        self.client.login(username="nonstaff", password="password")
        response = self.client.get(
            reverse("base:draft_detail", kwargs={"slug": "draft-project-detail"})
        )
        self.assertEqual(response.status_code, 403)

    def test_draft_detail_view_published_project_returns_404(self):
        self.client.login(username="testuser", password="password")
        response = self.client.get(
            reverse("base:draft_detail", kwargs={"slug": "published-project-detail"})
        )
        self.assertEqual(response.status_code, 404)


class YearContextTest(TestCase):
    def test_get_context_data(self):
        ctx = YearContext()
        ctx.request = RequestFactory().get("/")
        context = ctx.get_context_data()
        self.assertIn("year", context)
        self.assertEqual(context["year"], current_year())


class AboutViewTest(TestCase):
    def test_about_view_status_code(self):
        response = self.client.get(reverse("base:about"))
        self.assertEqual(response.status_code, 200)

    def test_about_view_template(self):
        response = self.client.get(reverse("base:about"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base/about.html")

    def test_about_view_context(self):
        response = self.client.get(reverse("base:about"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("year", response.context)
        self.assertEqual(response.context["year"], current_year())


class HomeViewTest(TestCase):
    def test_home_view_status_code(self):
        response = self.client.get(reverse("base:home"))
        self.assertEqual(response.status_code, 200)

    def test_home_view_template(self):
        response = self.client.get(reverse("base:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base/home.html")

    def test_home_view_context(self):
        response = self.client.get(reverse("base:home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("year", response.context)
        self.assertEqual(response.context["year"], current_year())
