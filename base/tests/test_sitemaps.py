from datetime import timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from base.models import Project
from base.sitemaps import BaseSiteMap, ProjectSitemap


class ImageTestMixin:
    def _create_image(self, width, height, filename="test.jpg"):
        """Creates a dummy image and returns it as a SimpleUploadedFile."""
        file = BytesIO()
        image = Image.new("RGB", (width, height), "white")
        image.save(file, "jpeg")
        file.seek(0)
        return SimpleUploadedFile(filename, file.read(), content_type="image/jpeg")


class BaseSiteMapTests(TestCase):
    def test_base_sitemap_items(self):
        sitemap = BaseSiteMap()
        items = sitemap.items()
        expected_items = [
            "base:home",
            "base:contact",
            "base:portfolio",
            "base:about",
        ]
        self.assertEqual(list(items), expected_items)

    def test_base_sitemap_location(self):
        sitemap = BaseSiteMap()
        self.assertEqual(sitemap.location("base:home"), reverse("base:home"))
        self.assertEqual(sitemap.location("base:contact"), reverse("base:contact"))


class ProjectSitemapTests(ImageTestMixin, TestCase):
    def setUp(self):
        self.project1 = Project.objects.create(
            title="Project 1",
            slug="project-1",
            featured_photo=self._create_image(100, 100),
            draft=False,
        )
        self.project2 = Project.objects.create(
            title="Project 2",
            slug="project-2",
            featured_photo=self._create_image(100, 100),
            draft=False,
        )
        self.draft_project = Project.objects.create(
            title="Draft Project",
            slug="draft-project",
            featured_photo=self._create_image(100, 100),
            draft=True,
        )

    def test_project_sitemap_items(self):
        sitemap = ProjectSitemap()
        items = sitemap.items()
        # ProjectSitemap only returns non-draft projects.
        self.assertEqual(items.count(), 2)
        self.assertIn(self.project1, items)
        self.assertIn(self.project2, items)
        self.assertNotIn(self.draft_project, items)

    def test_project_sitemap_location(self):
        sitemap = ProjectSitemap()
        location = sitemap.location(self.project1)
        expected_url = reverse("base:portfolio_detail", args=[self.project1.slug])
        self.assertEqual(location, expected_url)

    def test_project_sitemap_lastmod(self):
        sitemap = ProjectSitemap()
        self.assertEqual(sitemap.lastmod(self.project1), self.project1.updated)

    def test_project_sitemap_get_latest_lastmod(self):
        now = timezone.now()
        Project.objects.filter(pk=self.project2.pk).update(
            updated=now - timedelta(days=2)
        )
        Project.objects.filter(pk=self.project1.pk).update(
            updated=now - timedelta(days=1)
        )
        Project.objects.filter(pk=self.draft_project.pk).update(updated=now)

        self.project1.refresh_from_db()

        sitemap = ProjectSitemap()
        self.assertEqual(sitemap.get_latest_lastmod(), self.project1.updated)

    def test_project_sitemap_get_latest_lastmod_empty(self):
        Project.objects.filter(draft=False).delete()
        sitemap = ProjectSitemap()
        self.assertIsNone(sitemap.get_latest_lastmod())


class SitemapViewTests(ImageTestMixin, TestCase):
    def setUp(self):
        Project.objects.create(
            title="Test Project",
            slug="test-project",
            featured_photo=self._create_image(100, 100),
            draft=False,
        )

    def test_sitemap_xml_response(self):
        response = self.client.get(
            reverse("base:django.contrib.sitemaps.views.sitemap")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")

        # Check for some expected URLs in the response
        content = response.content.decode()
        self.assertIn(reverse("base:home"), content)
        self.assertIn(reverse("base:portfolio"), content)
        self.assertIn(reverse("base:portfolio_detail", args=["test-project"]), content)
