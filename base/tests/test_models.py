from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from base.models import Project, ProjectPortfolio, process_image_field
from base.tests.mixins import ImageTestMixin


class ProcessImageFieldTest(ImageTestMixin, TestCase):
    def test_process_large_image(self):
        """Test processing an image larger than max_size."""
        img = self._create_image(1000, 1000)
        result = process_image_field(img)
        with Image.open(result) as processed_img:
            self.assertEqual(processed_img.width, 780)
            self.assertEqual(processed_img.height, 780)

    def test_process_small_image(self):
        """Test processing an image smaller than max_size."""
        img = self._create_image(500, 500)
        result = process_image_field(img)
        self.assertEqual(result, img)

    def test_process_none(self):
        """Test processing None input."""
        result = process_image_field(None)
        self.assertIsNone(result)

    def test_process_non_image(self):
        """Test processing non-image input."""
        txt = SimpleUploadedFile("test.txt", b"hello", content_type="text/plain")
        result = process_image_field(txt)
        self.assertEqual(result, txt)


class ProjectModelTest(ImageTestMixin, TestCase):
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

    def test_project_str(self):
        """Test the string representation of the Project model."""
        project = Project(title="Test Project Title")
        self.assertEqual(str(project), "Test Project Title")

    @patch("django.db.models.Model.save")
    def test_project_save_kwargs(self, mock_super_save):
        """Test that save kwargs are properly forwarded to the parent class."""
        project = Project(title="Kwargs Project", slug="kwargs-project", draft=False)

        project.save(
            force_insert=True,
            force_update=False,
            using="default",
            update_fields=["title"],
        )

        mock_super_save.assert_called_once_with(
            force_insert=True,
            force_update=False,
            using="default",
            update_fields=["title"],
        )


class ProjectPortfolioModelTest(ImageTestMixin, TestCase):
    def test_project_portfolio_save_image_resizing(self):
        """Test that images larger than 780px are resized to 780px when saved."""
        large_image = self._create_image(1000, 1000)
        project = Project.objects.create(
            title="Test Resizing Project",
            slug="test-resizing",
        )
        portfolio = ProjectPortfolio.objects.create(
            project=project,
            photo=large_image,
        )

        # Open the saved image to verify dimensions
        with Image.open(portfolio.photo) as img:
            self.assertEqual(img.width, 780)
            self.assertEqual(img.height, 780)

    def test_project_portfolio_save_image_no_resizing(self):
        """Test that images smaller than or equal to 780px are not resized."""
        small_image = self._create_image(500, 500)
        project = Project.objects.create(
            title="Test No Resizing Project",
            slug="test-no-resizing",
        )
        portfolio = ProjectPortfolio.objects.create(
            project=project,
            photo=small_image,
        )

        # Open the saved image to verify dimensions
        with Image.open(portfolio.photo) as img:
            self.assertEqual(img.width, 500)
            self.assertEqual(img.height, 500)

    def test_project_portfolio_str(self):
        """Test the string representation of the ProjectPortfolio model."""
        project = Project(slug="test-slug")
        portfolio = ProjectPortfolio(project=project)
        self.assertEqual(str(portfolio), "test-slug")
