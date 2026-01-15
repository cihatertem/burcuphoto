import os
import math
from random import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, ListView, DetailView
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit

from .utils import get_client_ip, current_year, client_ip_key
from .models import Project




CAPTCHA_NUM1_KEY = "contact_captcha_num1"
CAPTCHA_NUM2_KEY = "contact_captcha_num2"
CAPTCHA_ANS_KEY = "contact_captcha_answer"

CONTACT_RATE_LIMIT = "2/m"
CONTACT_RATE_LIMIT_KEY = "ip"

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




def _generate_captcha(request) -> None:
    n1 = math.floor(random() * 10) + 1
    n2 = math.floor(random() * 10) + 1
    request.session[CAPTCHA_NUM1_KEY] = n1
    request.session[CAPTCHA_NUM2_KEY] = n2
    request.session[CAPTCHA_ANS_KEY] = n1 + n2


def _parse_int(value) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def captcha_is_valid(request) -> bool:
    expected = _parse_int(request.session.get(CAPTCHA_ANS_KEY))
    got = _parse_int(request.POST.get("captcha"))
    return expected is not None and got is not None and got == expected


@method_decorator(
    ratelimit(key=client_ip_key, rate=CONTACT_RATE_LIMIT, block=False, method="POST"),
    name="dispatch",
)
class Contact(YearContext, TemplateView):
    template_name = "base/contact.html"

    def get(self, request, *args, **kwargs):
        # Captcha sadece GET’te üretilir (POST’ta asla overwrite edilmez)
        _generate_captcha(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["num1"] = self.request.session.get(CAPTCHA_NUM1_KEY)
        ctx["num2"] = self.request.session.get(CAPTCHA_NUM2_KEY)
        return ctx

    def post(self, request, *args, **kwargs):
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        body = request.POST.get("message", "").strip()
        website = request.POST.get("website", "").strip()  # honeypot

        if getattr(request, "limited", False):
            messages.error(
                request,
                "Çok fazla istek gönderdiniz. Lütfen biraz sonra tekrar deneyin.",
            )
            return redirect("base:home")

        # Honeypot doluysa bot kabul et ve sessizce başarılı gibi dön
        if website:
            messages.success(request, "Your message was sent successfully.\nThank you!")
            return redirect("base:home")

        # Captcha doğrula (session yoksa/bozuksa da False döner)
        if not captcha_is_valid(request):
            messages.error(request, "Captcha incorrect. Please try again.")
            return redirect("base:contact")

        # Tek kullanımlık captcha: doğrulandıktan sonra session'dan sil
        request.session.pop(CAPTCHA_ANS_KEY, None)
        request.session.pop(CAPTCHA_NUM1_KEY, None)
        request.session.pop(CAPTCHA_NUM2_KEY, None)

        ip_address = get_client_ip(request)

        send_mail(
            subject="Web Site Visitor",
            message=(
                f"From {name}, {email}\n\n"
                f"{body}\n\n"
                f"IP: {ip_address}\n"
                f"Site: www.burcuatak.com\n"
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", email) or email,
            recipient_list=[
                os.getenv("EMAIL_RECEIVER_ONE"),
                os.getenv("EMAIL_RECEIVER_TWO"),
            ],
            fail_silently=False,
        )

        messages.success(
            request,
            "Your message was sent successfully.\nWe will touch you back soon.",
        )
        return redirect("base:home")


class DraftList(LoginRequiredMixin, YearContext, ListView):
    template_name = 'base/portfolio_list.html'
    queryset = Project.objects.filter(draft=True)


class DraftDetail(LoginRequiredMixin, YearContext, DetailView):
    template_name = 'base/portfolio_detail.html'
    queryset = Project.objects.filter(draft=True)
