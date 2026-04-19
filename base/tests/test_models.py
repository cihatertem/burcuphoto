from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from base.models import Project


class ProjectModelTest(TestCase):
    def _create_image(self, width, height, filename="test.jpg"):
        """Creates a dummy image and returns it as a SimpleUploadedFile."""
        file = BytesIO()
        image = Image.new("RGB", (width, height), "white")
        image.save(file, "jpeg")
        file.seek(0)
        return SimpleUploadedFile(filename, file.read(), content_type="image/jpeg")

    def test_project_save_image_resizing(self):
        """Test that images larger than 780px are resized to 780px when saved."""
        large_image = self._create_image(1000, 1000)
        project = Project.objects.create(
            title="Test Resizing Project",
            slug="test-resizing",
            featured_photo=large_image,
        )

        # Open the saved image to verify dimensions
        with Image.open(project.featured_photo) as img:
            self.assertEqual(img.width, 780)
            self.assertEqual(img.height, 780)

    def test_project_save_image_no_resizing(self):
        """Test that images smaller than or equal to 780px are not resized."""
        small_image = self._create_image(500, 500)
        project = Project.objects.create(
            title="Test No Resizing Project",
            slug="test-no-resizing",
            featured_photo=small_image,
        )

        # Open the saved image to verify dimensions
        with Image.open(project.featured_photo) as img:
            self.assertEqual(img.width, 500)
            self.assertEqual(img.height, 500)

    def test_project_save_link_draft(self):
        """Test that project_link is correctly generated when draft is True."""
        small_image = self._create_image(500, 500)
        project = Project.objects.create(
            title="Draft Project",
            slug="draft-project",
            featured_photo=small_image,
            draft=True,
        )
        self.assertEqual(
            project.project_link, "https://burcuatak.com/draft/draft-project/"
        )

    def test_project_save_link_not_draft(self):
        """Test that project_link is correctly generated when draft is False."""
        small_image = self._create_image(500, 500)
        project = Project.objects.create(
            title="Published Project",
            slug="published-project",
            featured_photo=small_image,
            draft=False,
        )
        self.assertEqual(
            project.project_link, "https://burcuatak.com/portfolio/published-project/"
        )
