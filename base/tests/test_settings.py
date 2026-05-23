from unittest.mock import mock_open, patch

from django.test import TestCase

from burcu_photo.settings import get_secret


class GetSecretTests(TestCase):
    @patch("os.getenv")
    @patch("os.path.isfile")
    def test_get_secret_from_file(self, mock_isfile, mock_getenv):
        mock_getenv.return_value = "/run/secrets/my_secret"
        mock_isfile.return_value = True

        m_open = mock_open(read_data="super_secret_value\n")
        with patch("builtins.open", m_open):
            result = get_secret("MY_SECRET")

        self.assertEqual(result, "super_secret_value")
        mock_getenv.assert_called_once_with("MY_SECRET", "")
        mock_isfile.assert_called_once_with("/run/secrets/my_secret")
        m_open.assert_called_once_with("/run/secrets/my_secret")

    @patch("os.getenv")
    @patch("os.path.isfile")
    def test_get_secret_from_env_var(self, mock_isfile, mock_getenv):
        mock_getenv.return_value = "direct_secret_value\n"
        mock_isfile.return_value = False

        result = get_secret("MY_SECRET")

        self.assertEqual(result, "direct_secret_value")
        mock_getenv.assert_called_once_with("MY_SECRET", "")
        mock_isfile.assert_called_once_with("direct_secret_value\n")

    @patch("os.getenv")
    @patch("os.path.isfile")
    def test_get_secret_default_value(self, mock_isfile, mock_getenv):
        mock_getenv.return_value = "default_value\n"
        mock_isfile.return_value = False

        result = get_secret("MY_SECRET", "default_value\n")

        self.assertEqual(result, "default_value")
        mock_getenv.assert_called_once_with("MY_SECRET", "default_value\n")
        mock_isfile.assert_called_once_with("default_value\n")
