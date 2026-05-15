import ipaddress
from datetime import date
from functools import lru_cache
from http import HTTPStatus
from io import BytesIO

from django.conf import settings
from django.http import JsonResponse
from PIL import Image, ImageOps


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META["PATH_INFO"] == "/ping":
            return JsonResponse({"response": "pong!"}, status=HTTPStatus.OK)

        return self.get_response(request)


def project_directory_path(instance, filename: str) -> str:
    return "projects/{0}/{1}".format(instance.slug, filename)


def portfolio_directory_path(instance, filename: str) -> str:
    return "projects/{0}/photos/{1}".format(instance.project.slug, filename)


def current_year() -> int:
    return date.today().year


def photo_resizer(image: Image.Image, size: int) -> BytesIO:
    output = BytesIO()
    if hasattr(image, "draft"):
        image.draft("RGB", (size, size))
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "P", "LA"):
        image = image.convert("RGB")
    image.thumbnail((size, size))
    image.save(output, format="JPEG", quality=85, optimize=True)
    output.seek(0)
    return output


@lru_cache(maxsize=1)
def _get_trusted_networks_optimized(trusted_nets_tuple):
    trusted_ips = set()
    trusted_subnets = []
    for net in trusted_nets_tuple:
        if net.prefixlen == net.max_prefixlen:
            trusted_ips.add(net.network_address)
        else:
            trusted_subnets.append(net)
    return trusted_ips, trusted_subnets


@lru_cache(maxsize=128)
def _parse_ip(ip_str):
    return ipaddress.ip_address(ip_str)


def _is_ip_trusted(ip_obj, trusted_ips, trusted_subnets) -> bool:
    if ip_obj in trusted_ips:
        return True
    for net in trusted_subnets:
        if ip_obj in net:
            return True
    return False


def _is_trusted_proxy_ip(ip_str: str, trusted_ips, trusted_subnets) -> bool:
    try:
        ip_obj = _parse_ip(ip_str)
        return _is_ip_trusted(ip_obj, trusted_ips, trusted_subnets)
    except ValueError:
        return False


def _get_trusted_proxies():
    trusted_nets = getattr(settings, "TRUSTED_PROXY_NETS", None) or []
    if not trusted_nets:
        return None, None
    return _get_trusted_networks_optimized(tuple(trusted_nets))


def _get_ip_from_xff(xff, trusted_ips, trusted_subnets) -> str | None:
    last_valid_ip = None
    end = len(xff)
    while end > 0:
        start = xff.rfind(",", 0, end)
        if start == -1:
            ip_str = xff[:end].strip()
            end = 0
        else:
            ip_str = xff[start + 1 : end].strip()
            end = start

        if not ip_str:
            continue

        last_valid_ip = ip_str
        if _is_trusted_proxy_ip(ip_str, trusted_ips, trusted_subnets):
            continue
        return ip_str

    return last_valid_ip


def get_client_ip(request) -> str | None:
    remote = request.META.get("REMOTE_ADDR")
    if not remote:
        return None

    trusted_ips, trusted_subnets = _get_trusted_proxies()
    if trusted_ips is None:
        return remote

    if not _is_trusted_proxy_ip(remote, trusted_ips, trusted_subnets):
        return remote

    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if not xff:
        return remote

    return _get_ip_from_xff(xff, trusted_ips, trusted_subnets) or remote


def client_ip_key(group, request):
    # request None olmasın, ip yoksa sabit değer ver
    return get_client_ip(request) or "unknown"
