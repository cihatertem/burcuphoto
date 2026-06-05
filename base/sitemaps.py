from django.contrib.sitemaps import Sitemap
from django.core.cache import cache
from django.db import models
from django.urls import reverse

from base.models import Project


class BaseSiteMap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return [
            "base:home",
            "base:contact",
            "base:portfolio",
            "base:about",
        ]

    def location(self, item):
        return reverse(item)


class ProjectSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return (
            Project.objects.filter(draft=False)
            .only("slug", "updated")
            .order_by("updated", "pk")
        )

    def location(self, item):
        return reverse("base:portfolio_detail", args=[item.slug])

    def lastmod(self, item):
        return item.updated

    def get_latest_lastmod(self):
        return cache.get_or_set(
            "project_sitemap_lastmod",
            lambda: Project.objects.filter(draft=False).aggregate(
                latest=models.Max("updated")
            )["latest"],
            3600,
        )
