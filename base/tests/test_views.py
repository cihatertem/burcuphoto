import base64
from io import BytesIO
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from base.models import Project, ProjectPortfolio
from base.utils import current_year
from base.views import (
    CAPTCHA_ANS_KEY,
    CAPTCHA_NUM1_KEY,
    CAPTCHA_NUM2_KEY,
    Contact,
    DraftDetail,
    DraftList,
    PortfolioDetail,
    PortfolioList,
    YearContext,
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

    @patch("base.views.secrets.randbelow", side_effect=[0] * 20)
    def test_generate_captcha_image_base64_returns_png_image(self, _mock_randbelow):
        captcha_image_b64 = _generate_captcha_image_base64(5, 3)

        image_bytes = base64.b64decode(captcha_image_b64, validate=True)
        self.assertTrue(image_bytes.startswith(b"\x89PNG\r\n\x1a\n"))

        with Image.open(BytesIO(image_bytes)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.mode, "RGB")
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

    @patch("base.views.secrets.randbelow", side_effect=[4, 2, *([0] * 20)])
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

        # Patch the start method of EmailThread to directly call run, making it synchronous for the test
        with patch("base.views.EmailThread.start", autospec=True) as mock_start:

            def side_effect(self_instance):
                self_instance.run()

            mock_start.side_effect = side_effect

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

        # Patch the start method of EmailThread to directly call run, making it synchronous for the test
        with patch("base.views.EmailThread.start", autospec=True) as mock_start:

            def side_effect(self_instance):
                self_instance.run()

            mock_start.side_effect = side_effect

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

    def test_get_queryset_filters_drafts_and_prefetches(self):
        view = PortfolioList()
        view.kwargs = {}
        qs = view.get_queryset()

        self.assertEqual(qs.count(), 1)
        self.assertIn(self.published_project, qs)
        self.assertNotIn(self.draft_project, qs)
        self.assertIn("projectportfolio_set", qs._prefetch_related_lookups)

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

        with self.assertNumQueries(2):
            view = PortfolioList()
            view.kwargs = {}
            qs = view.get_queryset()
            # Evaluate the queryset to trigger the DB queries
            projects = list(qs)
            # Access related data to ensure no extra queries are fired
            for project in projects:
                list(project.projectportfolio_set.all())

    def test_portfolio_list_view_template(self):
        response = self.client.get(reverse("base:portfolio"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base/portfolio_list.html")

    def test_portfolio_list_view_context(self):
        response = self.client.get(reverse("base:portfolio"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("year", response.context)
        self.assertEqual(response.context["year"], current_year())


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
        view.object = self.published_project
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

        self.user = User.objects.create_user(username="testuser", password="password")

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

    def test_get_queryset_filters_drafts_and_prefetches(self):
        view = DraftList()
        view.kwargs = {}
        qs = view.get_queryset()

        self.assertEqual(qs.count(), 1)
        self.assertIn(self.draft_project, qs)
        self.assertNotIn(self.published_project, qs)
        self.assertIn("projectportfolio_set", qs._prefetch_related_lookups)

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

        with self.assertNumQueries(2):
            view = DraftList()
            view.kwargs = {}
            qs = view.get_queryset()
            projects = list(qs)
            for project in projects:
                portfolios = list(project.projectportfolio_set.all())


class DraftDetailTest(ImageTestMixin, TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username="testuser", password="password")

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
        view.object = self.draft_project
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
                portfolios = list(project.projectportfolio_set.all())

    def test_draft_detail_view_unauthenticated(self):
        response = self.client.get(
            reverse("base:draft_detail", kwargs={"slug": "draft-project-detail"})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

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
