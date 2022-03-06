from django.shortcuts import redirect
from django.views.generic import TemplateView, ListView, DetailView, FormView
from .models import Project
from django.core.mail import send_mail
from django.contrib import messages


# Create your views here.
class HomeView(TemplateView):
    template_name = 'base/home.html'


class PortfolioList(ListView):
    template_name = 'base/portfolio_list.html'
    model = Project


class PortfolioDetail(DetailView):
    template_name = 'base/portfolio_detail.html'
    model = Project
    queryset = Project.objects.all().ordered('index')


class About(TemplateView):
    template_name = "base/about.html"


class Contact(TemplateView):
    template_name = "base/contact.html"

    def post(self, request, *args, **kwargs):
        name = request.POST.get("name")
        email = request.POST.get("email")
        body = request.POST.get("message")
        send_mail(
            'Web Site Visitor',
            f"""
            From {name}, {email},\n
            \t{body}
            """,
            email,
            ['atakburcu@gmail.com', 'cihatertem@gmail.com'],
            fail_silently=False,
        )
        messages.success(request, "Your message was sent successfully.\nWe will touch you back soon.")

        return redirect("base:home")
