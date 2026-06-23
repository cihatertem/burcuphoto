import sys
from unittest.mock import patch

from django.test import TestCase

import manage


class ManageCommandTest(TestCase):
    def test_manage_import_error(self):
        """Test manage.py main() behavior when Django is not installed."""
        with patch.dict("sys.modules", {"django.core.management": None}):
            with self.assertRaisesMessage(ImportError, "Couldn't import Django"):
                manage.main()
