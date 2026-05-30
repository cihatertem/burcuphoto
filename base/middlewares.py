from base.utils import _get_trusted_proxies, _is_trusted_proxy_ip


class TrustedProxyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._is_trusted_proxy(request):
            request.META.pop("HTTP_X_FORWARDED_FOR", None)
            request.META.pop("HTTP_X_FORWARDED_HOST", None)
            request.META.pop("HTTP_X_FORWARDED_PROTO", None)

        return self.get_response(request)

    @staticmethod
    def _is_trusted_proxy(request) -> bool:
        remote = request.META.get("REMOTE_ADDR")
        if not remote:
            return False

        trusted_ips, trusted_subnets = _get_trusted_proxies()
        if trusted_ips is None:
            return False

        return _is_trusted_proxy_ip(remote, trusted_ips, trusted_subnets)
