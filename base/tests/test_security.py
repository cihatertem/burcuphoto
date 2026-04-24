from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from base.admin import ProjectAdmin
from base.models import Project


class SecurityTestCase(TestCase):
    def test_admin_link_xss(self):
        # We create a Project instance without saving it to the DB
        # to avoid the save() method overwriting project_link
        project = Project(
            title="Test Project",
            slug="test-project",
            project_link='"><script>alert(1)</script>',
        )

        admin = ProjectAdmin(Project, AdminSite())
        link_html = admin.link(project)

        # If vulnerable, <script> will be present unescaped
        self.assertNotIn(
            "<script>",
            link_html,
            "XSS Vulnerability detected: <script> found in output",
        )


class OpenRedirectSecurityTest(TestCase):
    def test_portfolio_detail_open_redirect(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import Client
        from django.urls import reverse
        from PIL import Image

        client = Client()

        # Create a valid image file
        file_obj = BytesIO()
        image = Image.new("RGB", (100, 100), "white")
        image.save(file_obj, "JPEG")
        file_obj.seek(0)
        img = SimpleUploadedFile(
            "test_image.jpg", file_obj.read(), content_type="image/jpeg"
        )

        project = Project.objects.create(
            title="Test Redirect Project",
            slug="test-redirect-project",
            draft=False,
            featured_photo=img,
        )

        malicious_url = "http://malicious.example.com"
        response = client.get(
            reverse("base:portfolio_detail", kwargs={"slug": project.slug}),
            HTTP_REFERER=malicious_url,
        )

        content = response.content.decode("utf-8")

        # Verify the malicious URL is not rendered in the template output
        self.assertNotIn(
            malicious_url,
            content,
            "Open Redirect vulnerability: HTTP_REFERER was rendered in the output",
        )

        # Verify the safe default URL is used
        safe_url = reverse("base:portfolio")
        self.assertIn(
            safe_url,
            content,
            "The safe default portfolio URL was not found in the output",
        )
