from PIL import Image, ImageOps
from io import BytesIO


def project_directory_path(instance, filename):
    return 'projects/{0}/{1}'.format(instance.slug, filename)


def portfolio_directory_path(instance, filename):
    return 'projects/{0}/photos/{1}'.format(instance.project.slug, filename)


def photo_resizer(image: Image, size: int) -> BytesIO:
    output = BytesIO()
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.thumbnail((size, size))
    image = ImageOps.exif_transpose(image)
    image.save(output, format='JPEG', quality=100)
    output.seek(0)
    return output
