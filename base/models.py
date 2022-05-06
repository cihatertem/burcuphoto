from django.db import models
import uuid
from base.utils import project_directory_path, portfolio_directory_path, photo_resizer
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


# Create your models here.
class Project(models.Model):
    __slot__ = "id", "title", "meta_title", "meta_description", "slug", "created", "updated", "featured_photo", "alt", "draft", "project_link"
    id = models.UUIDField(default=uuid.uuid4, unique=True,
                          primary_key=True, editable=False)
    title = models.CharField(max_length=200, verbose_name="Title")
    meta_title = models.CharField(
        max_length=100, verbose_name="Meta Title", null=True, blank=True)
    meta_description = models.CharField(
        max_length=200, verbose_name="Meta Description", null=True, blank=True)
    slug = models.SlugField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    featured_photo = models.ImageField(
        max_length=200, upload_to=project_directory_path)
    alt = models.CharField(max_length=100, blank=True,
                           null=True, help_text="Fotoğraf için alt metin.")
    draft = models.BooleanField(default=True)
    project_link = models.URLField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.title

    def save(self):
        image = Image.open(self.featured_photo)

        if image.height > 780 or image.width > 780:
            output = photo_resizer(image, 780)
            self.featured_photo = InMemoryUploadedFile(output, 'ImageField',
                                                       "%s.jpg" % self.featured_photo.name.split('.')[
                                                           0],
                                                       'image/jpeg', sys.getsizeof(output), None)
        if self.draft:
            self.project_link = f'https://burcuatak.com/draft/{self.slug}/'
        elif not self.draft:
            self.project_link = f'https://burcuatak.com/portfolio/{self.slug}/'

        super(Project, self).save()


class ProjectPortfolio(models.Model):
    __slot__ = "id", "project", "photo", "alt", "created", "index", "updated"
    id = models.UUIDField(default=uuid.uuid4, unique=True,
                          primary_key=True, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    photo = models.ImageField(
        max_length=200, upload_to=portfolio_directory_path)
    alt = models.CharField(max_length=100, blank=True,
                           null=True, help_text="Fotoğraf için alt metin.")
    created = models.DateTimeField(auto_now_add=True)
    index = models.IntegerField(default=0, blank=True, null=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('index',)

    def __str__(self):
        return self.project.slug

    def save(self):
        image = Image.open(self.photo)

        if image.height > 780 or image.width > 780:
            output = photo_resizer(image, 780)
            self.photo = InMemoryUploadedFile(output, 'ImageField',
                                              "%s.jpg" % self.photo.name.split('.')[
                                                  0],
                                              'image/jpeg', sys.getsizeof(output), None)
        super(ProjectPortfolio, self).save()


class SpamFilter(models.Model):
    __slot__ = "id", "keyword", "created"
    id = models.UUIDField(default=uuid.uuid4, unique=True,
                          primary_key=True, editable=False)
    keyword = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.keyword
