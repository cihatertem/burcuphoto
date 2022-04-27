from django.contrib import admin
from .models import Project, ProjectPortfolio, SpamFilter
from django.utils.html import format_html


# Register your models here.
class ProjectPortfolioAdmin(admin.StackedInline):
    model = ProjectPortfolio


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
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
    ordering = ("project", "created")
    list_display = ("project", "alt", "created", "updated")
    list_filter = ("project", 'created', 'updated')
    search_fields = ('project',)
    list_per_page = 25


@admin.register(SpamFilter)
class SpamFilterAdmin(admin.ModelAdmin):
    ordering = ("keyword",)
    list_display = ("keyword",)
    list_filter = ("keyword", 'created')
    search_fields = ('keyword',)
    list_per_page = 25
