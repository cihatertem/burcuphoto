from django.urls import path
from . import views
from base.sitemaps import BaseSiteMap, ProjectSitemap
from django.contrib.sitemaps.views import sitemap

app_name = "base"

sitemaps = {
    "pages": BaseSiteMap,
    "projects": ProjectSitemap
}

urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    path('', views.HomeView.as_view(), name='home'),
    path('portfolio/', views.PortfolioList.as_view(), name='portfolio'),
    path('portfolio/<slug:slug>/', views.PortfolioDetail.as_view(), name='portfolio_detail'),
    path('about/', views.About.as_view(), name="about"),
    path('contact/', views.Contact.as_view(), name="contact"),
    path('draft/', views.DraftList.as_view(), name='draft'),
    path('draft/<slug:slug>/', views.DraftDetail.as_view(), name='draft_detail'),
    path("health", views.health_check, name="healtch_check"),
]
