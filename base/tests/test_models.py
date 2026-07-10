from unittest.mock import patch

from django.core.cache import cache
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
        self.assertNotEqual(result, img)  # Should return a new processed file
        with Image.open(result) as processed_img:
            self.assertEqual(processed_img.width, 500)
            self.assertEqual(processed_img.height, 500)

    @patch("base.models.logger.warning")
    def test_process_none(self, mock_logger):
        """Test processing None input."""
        result = process_image_field(None)
        self.assertIsNone(result)
        mock_logger.assert_called_once()

    @patch("base.models.logger.warning")
    def test_process_non_image(self, mock_logger):
        """Test processing non-image input."""
        txt = SimpleUploadedFile("test.txt", b"hello", content_type="text/plain")
        result = process_image_field(txt)
        self.assertEqual(result, txt)
        mock_logger.assert_called_once()

    @patch("base.models.logger.warning")
    @patch("base.models.Image.open")
    def test_process_corrupt_image(self, mock_image_open, mock_logger):
        """Test processing a corrupt image is gracefully handled."""
        mock_image_open.side_effect = OSError("Corrupt image")
        img = self._create_image(500, 500)
        result = process_image_field(img)
        self.assertEqual(result, img)
        mock_logger.assert_called_once()


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

    @patch("base.models.cache.delete")
    def test_project_delete_calls_cache_delete(self, mock_cache_delete):
        """Test that deleting a project explicitly calls cache.delete."""
        project = Project.objects.create(
            title="Delete Cache Mock", slug="delete-cache-mock", draft=False
        )
        mock_cache_delete.reset_mock()
        project.delete()
        mock_cache_delete.assert_called_once_with("project_sitemap_lastmod")

    def test_project_delete_clears_cache(self):
        """Test that deleting a project clears the project_sitemap_lastmod cache."""
        project = Project.objects.create(
            title="Delete Me", slug="delete-me", draft=False
        )
        cache.set("project_sitemap_lastmod", "some_value")
        self.assertEqual(cache.get("project_sitemap_lastmod"), "some_value")

        project.delete()

        self.assertIsNone(cache.get("project_sitemap_lastmod"))
        self.assertFalse(Project.objects.filter(slug="delete-me").exists())

    @patch("django.db.models.Model.delete")
    def test_project_delete_kwargs(self, mock_super_delete):
        """Test that delete kwargs are properly forwarded to the parent class."""
        project = Project(
            title="Kwargs Delete Project", slug="kwargs-delete-project", draft=False
        )

        project.delete(keep_parents=True)

        mock_super_delete.assert_called_once_with(keep_parents=True)


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

    @patch("django.db.models.Model.save")
    def test_project_portfolio_save_kwargs(self, mock_super_save):
        """Test that save kwargs are properly forwarded to the parent class."""
        project = Project(slug="test-slug")
        portfolio = ProjectPortfolio(project=project)

        portfolio.save(
            force_insert=True,
            force_update=False,
            using="default",
            update_fields=["index"],
        )

        mock_super_save.assert_called_once_with(
            force_insert=True,
            force_update=False,
            using="default",
            update_fields=["index"],
        )
