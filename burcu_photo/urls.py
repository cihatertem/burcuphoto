import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.urls import include, path
from django.views.generic import TemplateView

admin_url = os.getenv("ADMIN_ADDRESS", "admin/")
debug_mode = os.environ.get("DEBUG", "0") == "1" or settings.DEBUG

if not debug_mode and admin_url in ["admin/", "admin"]:
    raise ImproperlyConfigured("ADMIN_ADDRESS must be set to a custom, unpredictable path in production.")

urlpatterns = [
    path(admin_url, admin.site.urls),
    path('', include('base.urls', namespace='base')),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('yandex_697c73042871080e.html', TemplateView.as_view(template_name='yandex_697c73042871080e.html'))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
