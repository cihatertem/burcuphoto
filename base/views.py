from django.shortcuts import redirect
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Project
from django.core.mail import send_mail
from django.contrib import messages
import os
from random import random
import math
from .utils import get_client_ip, current_year


# Create your views here.
class YearContext(TemplateView):
    def get_context_data(self, **kwargs):
        context = super(YearContext, self).get_context_data(**kwargs)
        context["year"] = current_year()
        return context


class HomeView(YearContext, TemplateView):
    template_name = 'base/home.html'


class PortfolioList( ListView):
    template_name = 'base/portfolio_list.html'
    model = Project

    def get_queryset(self, **kwargs):
        queryset = super().get_queryset(**kwargs)
        return queryset.filter(draft=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year"] = current_year()
        return context


class PortfolioDetail(DetailView):
    template_name = 'base/portfolio_detail.html'
    model = Project

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year"] = current_year()
        return context


class About(YearContext, TemplateView):
    template_name = "base/about.html"


class Contact(YearContext, TemplateView):
    template_name = "base/contact.html"

    def get_context_data(self, **kwargs):
        context = super(Contact, self).get_context_data(**kwargs)
        num_one = math.floor(random() * 10) + 1
        num_two = math.floor(random() * 10) + 1
        context["num1"] = num_one
        context["num2"] = num_two
        self.request.session["contact_captcha_answer"] = num_one + num_two

        return context

    def post(self, request, *args, **kwargs):
        name = request.POST.get("name")
        email = request.POST.get("email")
        body = request.POST.get("message")
        website = request.POST.get("website", "")
        captcha = request.POST.get("captcha", "")

        if website.strip():
            messages.success(
                request, "Your message was sent successfully.\nThank you!"
            )

            return redirect("base:home")

        try:
            expected = int(request.session.get("contact_captcha_answer", -1))
            got = int(captcha)
        except ValueError:
            got = None

        if got != expected:
            messages.error(request, "Captcha incorrect. Please try again.")
            return redirect("base:contact")

        ip_address = get_client_ip(request)

        send_mail(
            'Web Site Visitor',
            f"""
            From {name}, {email}\n
            \t{body}\n
            {ip_address}
            Site: www.burcuatak.com
            """,
            email,
            [os.getenv("EMAIL_RECEIVER_ONE"), os.getenv("EMAIL_RECEIVER_TWO")],
            fail_silently=False,
        )
        messages.success(
            request, "Your message was sent successfully.\nWe will touch you back soon."
        )

        return redirect("base:home")


class DraftList(LoginRequiredMixin, YearContext, ListView):
    template_name = 'base/portfolio_list.html'
    queryset = Project.objects.filter(draft=True)


class DraftDetail(LoginRequiredMixin, YearContext, DetailView):
    template_name = 'base/portfolio_detail.html'
    queryset = Project.objects.filter(draft=True)
