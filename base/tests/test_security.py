from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from base.admin import ProjectAdmin
from base.models import Project


class SecurityTestCase(TestCase):
    def test_admin_link_xss(self):
        # We create a Project instance without saving it to the DB
        # to avoid the save() method overwriting project_link
        project = Project(
            title="Test Project",
            slug="test-project",
            project_link='"><script>alert(1)</script>',
        )

        admin = ProjectAdmin(Project, AdminSite())
        link_html = admin.link(project)

        # If vulnerable, <script> will be present unescaped
        self.assertNotIn(
            "<script>",
            link_html,
            "XSS Vulnerability detected: <script> found in output",
        )
