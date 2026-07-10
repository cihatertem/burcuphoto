from urllib.parse import urlparse

from django.contrib import admin
from django.utils.html import escape, format_html

from .models import Project, ProjectPortfolio


# Register your models here.
class ProjectPortfolioAdmin(admin.StackedInline):
    model = ProjectPortfolio


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    inlines = (ProjectPortfolioAdmin,)
    ordering = ("-created",)
    list_display = ("title", "link", "created", "updated", "draft")
    list_display_links = (
        "title",
        "link",
    )
    list_editable = ("draft",)
    list_filter = ("created", "updated", "draft")
    search_fields = ("title",)
    list_per_page = 25

    def link(self, obj: Project) -> str:
        if not obj.project_link:
            return ""

        url = obj.project_link.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return escape(url)

        return format_html('<a  href="{}" >{}</a>', url, url)

    link.short_description = "Project Link"


@admin.register(ProjectPortfolio)
class ProjectPortfolioAdmin(admin.ModelAdmin):
    ordering = ("project", "created")
    list_display = ("project", "alt", "created", "updated")
    list_select_related = ("project",)
    list_filter = ("project", "created", "updated")
    search_fields = ("project",)
    list_per_page = 25
