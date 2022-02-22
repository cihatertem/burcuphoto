from django.urls import path
from . import views

app_name = "base"

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('portfolio/', views.PortfolioList.as_view(), name='portfolio'),
    path('portfolio/<slug:slug>/', views.PortfolioDetail.as_view(), name='portfolio_detail'),
    path('about/', views.About.as_view(), name="about"),
    path('contact/', views.Contact.as_view(), name="contact"),
]
