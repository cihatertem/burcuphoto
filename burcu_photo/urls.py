from django.conf import settings
from django.contrib import admin
from django.urls import path, include
# static media urls
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
#  dotenv
import os

urlpatterns = [
    path(os.getenv("ADMIN_ADDRESS"), admin.site.urls),
    path('', include('base.urls', namespace='base')),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('yandex_697c73042871080e.html', TemplateView.as_view(template_name='yandex_697c73042871080e.html'))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
