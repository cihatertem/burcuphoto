import sys
import uuid

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.utils.translation import gettext_lazy as _
from PIL import Image

from base.utils import photo_resizer, portfolio_directory_path, project_directory_path

PHOTO_ALT_TEXT = _("Alt text for the photo.")


def process_image_field(image_field, max_size=780):
    """Resizes an image field to max_size if it exceeds its dimensions."""
    with Image.open(image_field) as image:
        if image.height > max_size or image.width > max_size:
            output = photo_resizer(image, max_size)
            return InMemoryUploadedFile(
                output,
                "ImageField",
                "%s.jpg" % image_field.name.split(".")[0],
                "image/jpeg",
                sys.getsizeof(output),
                None,
            )
    return image_field


class Project(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, primary_key=True, editable=False
    )
    title = models.CharField(max_length=200, verbose_name="Title")
    meta_title = models.CharField(
        max_length=100, verbose_name="Meta Title", null=True, blank=True
    )
    meta_description = models.CharField(
        max_length=200, verbose_name="Meta Description", null=True, blank=True
    )
    slug = models.SlugField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    featured_photo = models.ImageField(max_length=200, upload_to=project_directory_path)
    alt = models.CharField(
        max_length=100, blank=True, null=True, help_text=PHOTO_ALT_TEXT
    )
    draft = models.BooleanField(default=True)
    project_link = models.URLField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.title

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if self.featured_photo and not getattr(self.featured_photo, "_committed", True):
            self.featured_photo = process_image_field(self.featured_photo)

        if self.draft:
            self.project_link = f"https://burcuatak.com/draft/{self.slug}/"
        elif not self.draft:
            self.project_link = f"https://burcuatak.com/portfolio/{self.slug}/"

        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class ProjectPortfolio(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, primary_key=True, editable=False
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    photo = models.ImageField(max_length=200, upload_to=portfolio_directory_path)
    alt = models.CharField(
        max_length=100, blank=True, null=True, help_text=PHOTO_ALT_TEXT
    )
    created = models.DateTimeField(auto_now_add=True)
    index = models.IntegerField(default=0, blank=True, null=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("index",)

    def __str__(self):
        return self.project.slug

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if self.photo and not getattr(self.photo, "_committed", True):
            self.photo = process_image_field(self.photo)

        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
