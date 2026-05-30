from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from base.admin import ProjectAdmin
from base.models import Project


class ProjectAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.project_admin = ProjectAdmin(Project, self.site)

    def test_link_with_https_scheme(self):
        project = Project(project_link="https://example.com")
        html = self.project_admin.link(project)
        self.assertEqual(
            html, '<a  href="https://example.com" >https://example.com</a>'
        )

    def test_link_with_http_scheme(self):
        project = Project(project_link="http://example.com")
        html = self.project_admin.link(project)
        self.assertEqual(html, '<a  href="http://example.com" >http://example.com</a>')

    def test_link_with_javascript_scheme(self):
        project = Project(project_link="javascript:alert(1)")
        html = self.project_admin.link(project)
        self.assertEqual(html, "javascript:alert(1)")

    def test_link_with_leading_spaces_and_javascript_scheme(self):
        project = Project(project_link="   javascript:alert(1)")
        html = self.project_admin.link(project)
        self.assertEqual(html, "javascript:alert(1)")

    def test_link_with_leading_spaces_and_https_scheme(self):
        project = Project(project_link="   https://example.com")
        html = self.project_admin.link(project)
        self.assertEqual(
            html, '<a  href="https://example.com" >https://example.com</a>'
        )

    def test_link_with_none(self):
        project = Project(project_link=None)
        html = self.project_admin.link(project)
        self.assertEqual(html, "")

    def test_link_with_empty_string(self):
        project = Project(project_link="")
        html = self.project_admin.link(project)
        self.assertEqual(html, "")
