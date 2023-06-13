from django.shortcuts import redirect, render
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Project, SpamFilter
from django.core.mail import send_mail
from django.contrib import messages
import os
from dotenv import load_dotenv
from random import random
import math
from .utils import spam_checker, get_client_ip
from datetime import date

load_dotenv()

YEAR = date.today().year


# Create your views here.
class YearContext(TemplateView):
    def get_context_data(self, **kwargs):
        context = super(YearContext, self).get_context_data(**kwargs)
        context["year"] = YEAR
        return context


class HomeView(YearContext, TemplateView):
    __slot__ = "template_name"
    template_name = 'base/home.html'


class PortfolioList(ListView):
    __slot__ = "template_name", "queryset"
    template_name = 'base/portfolio_list.html'
    queryset = Project.objects.filter(draft=False)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context["year"] = YEAR
        return context


class PortfolioDetail( DetailView):
    __slot__ = "template_name", "queryset"
    template_name = 'base/portfolio_detail.html'
    queryset = Project.objects.filter(draft=False)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context["year"] = YEAR
        return context

class About(YearContext, TemplateView):
    __slot__ = "template_name"
    template_name = "base/about.html"


class Contact(YearContext, TemplateView):
    __slot__ = "template_name"
    template_name = "base/contact.html"

    def get_context_data(self, **kwargs):
        context = super(Contact, self).get_context_data(**kwargs)
        num_one = math.floor(random() * 10) + 1
        num_two = math.floor(random() * 10) + 1
        context["num1"] = num_one
        context["num2"] = num_two
        return context

    def post(self, request, *args, **kwargs):
        name = request.POST.get("name")
        email = request.POST.get("email")
        body = request.POST.get("message")

        if spam_checker(body):
            messages.success(
                request, "Your message was not sent .\nDONT MAKE SPAM!")

            return redirect("base:home")

        ip_address = get_client_ip(request)

        send_mail(
            'Web Site Visitor',
            f"""
            From {name}, {email}, {ip_address}\n
            \t{body}
            Site: www.burcuatak.com
            """,
            email,
            [os.getenv("EMAIL_RECEIVER_ONE"), os.getenv("EMAIL_RECEIVER_TWO")],
            fail_silently=False,
        )
        messages.success(
            request, "Your message was sent successfully.\nWe will touch you back soon.")

        return redirect("base:home")


class DraftList(LoginRequiredMixin, YearContext, ListView):
    __slot__ = "template_name", "queryset"
    template_name = 'base/portfolio_list.html'
    queryset = Project.objects.filter(draft=True)


class DraftDetail(LoginRequiredMixin, YearContext, DetailView):
    __slot__ = "template_name", "queryset"
    template_name = 'base/portfolio_detail.html'
    queryset = Project.objects.filter(draft=True)
