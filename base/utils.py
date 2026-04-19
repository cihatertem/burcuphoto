import ipaddress
from datetime import date
from http import HTTPStatus
from io import BytesIO

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from PIL import Image, ImageOps


class HealthCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.META["PATH_INFO"] == "/ping":
            return JsonResponse({"response": "pong!"}, status=HTTPStatus.OK)


def project_directory_path(instance, filename: str) -> str:
    return "projects/{0}/{1}".format(instance.slug, filename)


def portfolio_directory_path(instance, filename: str) -> str:
    return "projects/{0}/photos/{1}".format(instance.project.slug, filename)


def current_year() -> int:
    return date.today().year


def photo_resizer(image: Image.Image, size: int) -> BytesIO:
    output = BytesIO()
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.thumbnail((size, size))
    image = ImageOps.exif_transpose(image)
    image.save(output, format="JPEG", quality=100)
    output.seek(0)
    return output


def get_client_ip(request) -> str | None:
    remote = request.META.get("REMOTE_ADDR")
    if not remote:
        return None

    try:
        ra = ipaddress.ip_address(remote)
    except ValueError:
        return remote

    trusted_nets = getattr(settings, "TRUSTED_PROXY_NETS", None) or []

    if trusted_nets and any(ra in net for net in trusted_nets):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
            for ip_str in reversed(ips):
                try:
                    ip_obj = ipaddress.ip_address(ip_str)
                    if any(ip_obj in net for net in trusted_nets):
                        continue
                    return ip_str
                except ValueError:
                    return ip_str
            if ips:
                return ips[0]

    return remote


def client_ip_key(group, request):
    # request None olmasın, ip yoksa sabit değer ver
    return get_client_ip(request) or "unknown"
