from io import BytesIO

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from base.models import Project, ProjectPortfolio
from base.views import CAPTCHA_ANS_KEY, CAPTCHA_NUM1_KEY, CAPTCHA_NUM2_KEY


class ContactViewTest(TestCase):
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
