from PIL import Image, ImageOps
from io import BytesIO
from datetime import date
from django.http import HttpRequest
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from http import HTTPStatus


class HealthCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.META['PATH_INFO'] == '/ping':
            return JsonResponse({"response": "pong!"}, status=HTTPStatus.OK)


def project_directory_path(instance, filename: str) -> str:
    return 'projects/{0}/{1}'.format(instance.slug, filename)


def portfolio_directory_path(instance, filename: str) -> str:
    return 'projects/{0}/photos/{1}'.format(instance.project.slug, filename)


def current_year() -> int:
    return date.today().year


def photo_resizer(image: Image.Image, size: int) -> BytesIO:
    output = BytesIO()
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.thumbnail((size, size))
    image = ImageOps.exif_transpose(image)
    image.save(output, format='JPEG', quality=100)
    output.seek(0)
    return output


def get_client_ip(request: HttpRequest) -> dict[str, str]:
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
