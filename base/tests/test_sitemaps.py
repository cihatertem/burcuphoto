from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils import timezone

from base.models import Project
from base.sitemaps import BaseSiteMap, ProjectSitemap
from base.tests.mixins import ImageTestMixin


class BaseSiteMapTests(TestCase):
    def test_base_sitemap_items(self):
        sitemap = BaseSiteMap()
        expected_items = [
            "base:home",
            "base:contact",
            "base:portfolio",
            "base:about",
        ]
        self.assertEqual(sitemap.items(), expected_items)

    def test_base_sitemap_location(self):
        sitemap = BaseSiteMap()
        items = sitemap.items()

        self.assertGreater(len(items), 0)

        for item in items:
            self.assertEqual(sitemap.location(item), reverse(item))

    def test_base_sitemap_location_invalid_item(self):
        sitemap = BaseSiteMap()
        with self.assertRaises(NoReverseMatch):
            sitemap.location("base:invalid_route")


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
        # Manually update 'updated' to ensure deterministic ordering
        now = timezone.now()
        Project.objects.filter(pk=self.project1.pk).update(
            updated=now - timedelta(days=2)
        )
        Project.objects.filter(pk=self.project2.pk).update(
            updated=now - timedelta(days=1)
        )

        self.project1.refresh_from_db()
        self.project2.refresh_from_db()

        sitemap = ProjectSitemap()
        items = sitemap.items()

        # ProjectSitemap only returns non-draft projects and orders by updated
        self.assertEqual(list(items), [self.project1, self.project2])

        # Verify that .only("slug", "updated") logic deferred some fields
        deferred = items[0].get_deferred_fields()
        self.assertTrue(len(deferred) > 0)
        self.assertIn("title", deferred)
        self.assertIn("draft", deferred)
        self.assertNotIn("slug", deferred)
        self.assertNotIn("updated", deferred)

    def test_project_sitemap_location(self):
        sitemap = ProjectSitemap()
        location = sitemap.location(self.project1)
        expected_url = reverse("base:portfolio_detail", args=[self.project1.slug])
        self.assertEqual(location, expected_url)

    def test_project_sitemap_location_invalid_item(self):
        sitemap = ProjectSitemap()

        # Test with an object that has no 'slug' attribute
        class InvalidItem:
            pass

        with self.assertRaises(AttributeError):
            sitemap.location(InvalidItem())

        # Test with None
        with self.assertRaises(AttributeError):
            sitemap.location(None)

    def test_project_sitemap_location_no_reverse_match(self):
        sitemap = ProjectSitemap()

        class InvalidSlugItem:
            slug = "invalid/slug/that/wont/match"

        with self.assertRaises(NoReverseMatch):
            sitemap.location(InvalidSlugItem())

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

    def test_project_sitemap_get_latest_lastmod_cache_miss(self):
        now = timezone.now()
        Project.objects.filter(pk=self.project2.pk).update(
            updated=now - timedelta(days=2)
        )
        Project.objects.filter(pk=self.project1.pk).update(
            updated=now - timedelta(days=1)
        )
        Project.objects.filter(pk=self.draft_project.pk).update(updated=now)

        self.project1.refresh_from_db()

        # Ensure the cache is clear
        cache.delete("project_sitemap_lastmod")
        self.assertIsNone(cache.get("project_sitemap_lastmod"))

        # Trigger cache miss and generation
        sitemap = ProjectSitemap()
        latest_lastmod = sitemap.get_latest_lastmod()

        # Assert returned value is correct
        self.assertEqual(latest_lastmod, self.project1.updated)

        # Assert cache is now populated with the expected value
        cached_value = cache.get("project_sitemap_lastmod")
        self.assertEqual(cached_value, self.project1.updated)

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
