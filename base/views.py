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
from .utils import spam_checker

load_dotenv()


# Create your views here.
class HomeView(TemplateView):
    template_name = 'base/home.html'


class PortfolioList(ListView):
    template_name = 'base/portfolio_list.html'
    queryset = Project.objects.filter(draft=False)


class PortfolioDetail(DetailView):
    template_name = 'base/portfolio_detail.html'
    queryset = Project.objects.filter(draft=False)


class About(TemplateView):
    template_name = "base/about.html"


class Contact(TemplateView):
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

        send_mail(
            'Web Site Visitor',
            f"""
            From {name}, {email},\n
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


class DraftList(LoginRequiredMixin, ListView):
    template_name = 'base/portfolio_list.html'
    queryset = Project.objects.filter(draft=True)


class DraftDetail(LoginRequiredMixin, DetailView):
    template_name = 'base/portfolio_detail.html'
    queryset = Project.objects.filter(draft=True)
