import os
import threading

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.mail import BadHeaderError, EmailMessage
from django.core.validators import validate_email
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.base import ContextMixin
from django_ratelimit.decorators import ratelimit

from .captcha import (
    CAPTCHA_ANS_KEY,
    CAPTCHA_NUM1_KEY,
    CAPTCHA_NUM2_KEY,
    _generate_captcha,
    _generate_captcha_image_base64,
    captcha_is_valid,
)
from .models import Project
from .utils import client_ip_key, current_year, get_client_ip

CONTACT_RATE_LIMIT = "2/m"
CONTACT_RATE_LIMIT_KEY = "ip"


# Create your views here.


class YearContext(ContextMixin):
    extra_context = {"year": current_year()}


class PortfolioContextMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["portfolios"] = self.object.projectportfolio_set.all()
        return context


class PortfolioQuerySetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(draft=False).prefetch_related("projectportfolio_set")


class HomeView(YearContext, TemplateView):
    template_name = "base/home.html"


class PortfolioList(YearContext, PortfolioQuerySetMixin, ListView):
    template_name = "base/portfolio_list.html"
    model = Project


class PortfolioDetail(
    YearContext, PortfolioContextMixin, PortfolioQuerySetMixin, DetailView
):
    template_name = "base/portfolio_detail.html"
    model = Project


class About(YearContext, TemplateView):
    template_name = "base/about.html"


class EmailThread(threading.Thread):
    def __init__(self, email_message):
        self.email_message = email_message
        threading.Thread.__init__(self)

    def run(self):
        self.email_message.send(fail_silently=False)


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
        n1 = self.request.session.get(CAPTCHA_NUM1_KEY, 0)
        n2 = self.request.session.get(CAPTCHA_NUM2_KEY, 0)
        ctx["captcha_image_b64"] = _generate_captcha_image_base64(n1, n2)
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
            return redirect("base:contact")

        # Honeypot doluysa bot kabul et ve sessizce başarılı gibi dön
        if website:
            messages.success(request, "Your message was sent successfully.\nThank you!")
            return redirect("base:home")

        # Captcha doğrula (session yoksa/bozuksa da False döner)
        if not captcha_is_valid(request):
            messages.error(request, "Captcha incorrect. Please try again.")
            return redirect("base:contact")

        # Validate the email address
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email address.")
            return redirect("base:contact")

        # Tek kullanımlık captcha: doğrulandıktan sonra session'dan sil
        request.session.pop(CAPTCHA_ANS_KEY, None)
        request.session.pop(CAPTCHA_NUM1_KEY, None)
        request.session.pop(CAPTCHA_NUM2_KEY, None)

        ip_address = get_client_ip(request)

        try:
            self._send_contact_email(name, email, body, ip_address)
        except BadHeaderError:
            messages.error(request, "Invalid header found.")
            return redirect("base:contact")

        messages.success(
            request,
            "Your message was sent successfully.\nWe will touch you back soon.",
        )
        return redirect("base:home")

    def _send_contact_email(
        self, name: str, email: str, body: str, ip_address: str
    ) -> None:
        # Prevent email header injection synchronously
        if email and ("\n" in email or "\r" in email):
            raise BadHeaderError("Invalid header found.")

        msg = EmailMessage(
            subject="Web Site Visitor",
            body=(
                f"From {escape(name)}, {escape(email)}\n\n"
                f"{escape(body)}\n\n"
                f"IP: {ip_address}\n"
                f"Site: www.burcuatak.com\n"
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            to=[
                os.getenv("EMAIL_RECEIVER_ONE"),
                os.getenv("EMAIL_RECEIVER_TWO"),
            ],
            reply_to=[email] if email else None,
        )
        EmailThread(msg).start()


class DraftList(LoginRequiredMixin, YearContext, ListView):
    template_name = "base/portfolio_list.html"
    queryset = Project.objects.filter(draft=True)


class DraftDetail(LoginRequiredMixin, YearContext, PortfolioContextMixin, DetailView):
    template_name = "base/portfolio_detail.html"
    queryset = Project.objects.filter(draft=True).prefetch_related(
        "projectportfolio_set"
    )
