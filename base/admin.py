from django.contrib import admin
from .models import Project, ProjectPortfolio


# Register your models here.
class ProjectPortfolioAdmin(admin.StackedInline):
    model = ProjectPortfolio


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProjectPortfolioAdmin]
    ordering = ["-created"]
    list_display = ["title", "created", "updated"]


    class Meta:
        model = Project


@admin.register(ProjectPortfolio)
class ProjectPortfolioAdmin(admin.ModelAdmin):
    ordering = ["index", "project", "created"]
    list_display = ["project", "alt", "created", "updated"]
