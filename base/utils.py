from PIL import Image, ImageOps
from io import BytesIO
from base import models
from django.http import HttpRequest


def project_directory_path(instance, filename: str) -> str:
    return 'projects/{0}/{1}'.format(instance.slug, filename)


def portfolio_directory_path(instance, filename: str) -> str:
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


def spam_checker(mail_body: str) -> bool | None:
    spam_keywords = models.SpamFilter.objects.all()

    spam_list = []

    for keyword in spam_keywords:
        spam_list.append(keyword.keyword.lower())

    body_words = mail_body.strip().split(" ")
    stripped_words = []

    for body_word in body_words:
        body_word = body_word.strip(".?!:;* '\"-_,`").lower()
        if not body_word:
            continue
        stripped_words.append(body_word)

    for stripped_word in stripped_words:
        if stripped_word in spam_list:
            return True


def get_client_ip(request: HttpRequest) -> str:
    return {
        "HTTP_X_FORWARDED_FOR":  request.META.get('HTTP_X_FORWARDED_FOR', None),
        "REMOTE_ADDR": request.META.get('REMOTE_ADDR', None),
        "X_Real_IP": request.META.get('X_Real_IP', None),
        "HTTP_X_Real_IP": request.META.get('HTTP_X_Real_IP', None),
        'X_FORWARDED_FOR':  request.META.get('X_FORWARDED_FOR', None),
        'HTTP_CLIENT_IP':  request.META.get('HTTP_CLIENT_IP', None),
        'HTTP_X_FORWARDED':  request.META.get('HTTP_X_FORWARDED', None),
        'HTTP_X_CLUSTER_CLIENT_IP':  request.META.get('HTTP_X_CLUSTER_CLIENT_IP', None),
        'HTTP_FORWARDED_FOR':  request.META.get('HTTP_FORWARDED_FOR', None),
        'HTTP_FORWARDED':  request.META.get('HTTP_FORWARDED', None),
        'HTTP_VIA':  request.META.get('HTTP_VIA', None),
    }
