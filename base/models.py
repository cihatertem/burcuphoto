from django.db import models
import uuid
from base.utils import project_directory_path, portfolio_directory_path, photo_resizer
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


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

    def save(self):
        image = Image.open(self.featured_photo)

        if image.height > 780 or image.width > 780:
            output = photo_resizer(image, 780)
            self.featured_photo = InMemoryUploadedFile(output, 'ImageField',
                                                       "%s.jpg" % self.featured_photo.name.split('.')[0],
                                                       'image/jpeg', sys.getsizeof(output), None)
        super(Project, self).save()


class ProjectPortfolio(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    photo = models.ImageField(max_length=200, upload_to=portfolio_directory_path)
    alt = models.CharField(max_length=100, blank=True, null=True, help_text="Fotoğraf için alt metin.")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.project.slug

    def save(self):
        image = Image.open(self.photo)

        if image.height > 780 or image.width > 780:
            output = photo_resizer(image, 780)
            self.photo = InMemoryUploadedFile(output, 'ImageField',
                                              "%s.jpg" % self.photo.name.split('.')[0],
                                              'image/jpeg', sys.getsizeof(output), None)
        super(ProjectPortfolio, self).save()
