import importlib
import os
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

import burcu_photo.urls


class UrlsTests(TestCase):
    def test_improperly_configured_admin_url_in_production(self):
        with patch.dict(os.environ, {"DEBUG": "0", "ADMIN_ADDRESS": "admin/"}):
            with override_settings(DEBUG=False):
                with self.assertRaises(ImproperlyConfigured) as context:
                    importlib.reload(burcu_photo.urls)
                self.assertIn(
                    "ADMIN_ADDRESS must be set to a custom, unpredictable path in production.",
                    str(context.exception),
                )

    def test_valid_admin_url_in_production(self):
        with patch.dict(os.environ, {"DEBUG": "0", "ADMIN_ADDRESS": "secret-admin/"}):
            with override_settings(DEBUG=False):
                try:
                    importlib.reload(burcu_photo.urls)
                except ImproperlyConfigured:
                    self.fail(
                        "importlib.reload(burcu_photo.urls) raised ImproperlyConfigured unexpectedly!"
                    )

    def test_default_admin_url_in_debug(self):
        with patch.dict(os.environ, {"DEBUG": "1", "ADMIN_ADDRESS": "admin/"}):
            with override_settings(DEBUG=True):
                try:
                    importlib.reload(burcu_photo.urls)
                except ImproperlyConfigured:
                    self.fail(
                        "importlib.reload(burcu_photo.urls) raised ImproperlyConfigured unexpectedly!"
                    )
