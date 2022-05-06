from django.contrib import admin
from .models import Project, ProjectPortfolio, SpamFilter
from django.utils.html import format_html


# Register your models here.
class ProjectPortfolioAdmin(admin.StackedInline):
    __slot__ = "model"
    model = ProjectPortfolio


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    __slot__ = "prepopulated_fields", "inlines", "ordering", "list_display", "list_display_links", "list_editable", "list_filter", "search_fields", "list_per_page"
    prepopulated_fields = {"slug": ("title",)}
    inlines = (ProjectPortfolioAdmin,)
    ordering = ("-created",)
    list_display = ("title", "link", "created", "updated", "draft")
    list_display_links = ("title", "link",)
    list_editable = ('draft',)
    list_filter = ('created', 'updated', "draft")
    search_fields = ('title',)
    list_per_page = 25

    def link(self, obj: Project) -> str:
        return format_html(
            f'<a  href="{obj.project_link}" >{obj.project_link}</a>'
        )

    link.short_description = 'Project Link'
    link.allow_tags = True


@admin.register(ProjectPortfolio)
class ProjectPortfolioAdmin(admin.ModelAdmin):
    __slot__ = "ordering", "list_display", "list_filter", "search_fields", "list_per_page"
    ordering = ("project", "created")
    list_display = ("project", "alt", "created", "updated")
    list_filter = ("project", 'created', 'updated')
    search_fields = ('project',)
    list_per_page = 25


@admin.register(SpamFilter)
class SpamFilterAdmin(admin.ModelAdmin):
    __slot__ = "ordering", "list_display", "list_filter", "search_fields", "list_per_page"
    ordering = ("keyword",)
    list_display = ("keyword",)
    list_filter = ("keyword", 'created')
    search_fields = ('keyword',)
    list_per_page = 25
