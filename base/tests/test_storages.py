from django.test import TestCase
from base.storages import CustomS3ManifestStaticStorage

class StorageTestCase(TestCase):
    def test_custom_s3_manifest_static_storage_strictness(self):
        self.assertFalse(CustomS3ManifestStaticStorage.manifest_strict)
