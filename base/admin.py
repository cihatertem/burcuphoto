from django.contrib import admin
from django.utils.html import format_html

from .models import Project, ProjectPortfolio


# Register your models here.
class ProjectPortfolioAdmin(admin.StackedInline):
    __slot__ = "model"
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
            '<a  href="{}" >{}</a>',
            obj.project_link,
            obj.project_link
        )

    link.short_description = 'Project Link'


@admin.register(ProjectPortfolio)
class ProjectPortfolioAdmin(admin.ModelAdmin):
    ordering = ("project", "created")
    list_display = ("project", "alt", "created", "updated")
    list_filter = ("project", 'created', 'updated')
    search_fields = ('project',)
    list_per_page = 25

