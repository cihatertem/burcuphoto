from storages.backends.s3 import S3ManifestStaticStorage


class CustomS3ManifestStaticStorage(S3ManifestStaticStorage):
    manifest_strict = False
