from django.db import models
import uuid
from base.utils import project_directory_path, portfolio_directory_path


# Create your models here.
class Project(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    title = models.CharField(max_length=200, verbose_name="Title")
    slug = models.SlugField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    featured_photo = models.ImageField(max_length=200, upload_to=project_directory_path)
    alt = models.CharField(max_length=100, blank=True, null=True, help_text="Fotoğraf için alt metin.")

    def __str__(self):
        return self.title


class ProjectPortfolio(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    photo = models.ImageField(max_length=200, upload_to=portfolio_directory_path)
    alt = models.CharField(max_length=100, blank=True, null=True, help_text="Fotoğraf için alt metin.")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.project.slug
