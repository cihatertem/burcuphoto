import base64
import os
import secrets
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.mail import BadHeaderError, EmailMessage
from django.core.validators import validate_email
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView, TemplateView
from django_ratelimit.decorators import ratelimit
from PIL import Image, ImageDraw

from .models import Project
from .utils import client_ip_key, current_year, get_client_ip

CAPTCHA_NUM1_KEY = "contact_captcha_num1"
CAPTCHA_NUM2_KEY = "contact_captcha_num2"
CAPTCHA_ANS_KEY = "contact_captcha_answer"

CONTACT_RATE_LIMIT = "2/m"
CONTACT_RATE_LIMIT_KEY = "ip"


# Create your views here.
from django.views.generic.base import ContextMixin


class YearContext(ContextMixin):
    extra_context = {"year": current_year()}


class HomeView(YearContext, TemplateView):
    template_name = "base/home.html"


class PortfolioList(YearContext, ListView):
    template_name = "base/portfolio_list.html"
    model = Project

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(draft=False).prefetch_related("projectportfolio_set")


class PortfolioDetail(YearContext, DetailView):
    template_name = "base/portfolio_detail.html"
    model = Project

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(draft=False).prefetch_related("projectportfolio_set")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["portfolios"] = self.object.projectportfolio_set.all()
        return context


class About(YearContext, TemplateView):
    template_name = "base/about.html"


def _generate_captcha(request) -> None:
    n1 = secrets.randbelow(10) + 1
    n2 = secrets.randbelow(10) + 1
    request.session[CAPTCHA_NUM1_KEY] = n1
    request.session[CAPTCHA_NUM2_KEY] = n2
    request.session[CAPTCHA_ANS_KEY] = n1 + n2


def _parse_int(value) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def _generate_captcha_image_base64(n1: int, n2: int) -> str:
    image = Image.new("RGB", (60, 20), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    text = f"{n1} + {n2} ="
    draw.text((5, 5), text, fill=(0, 0, 0))

    # Scale it up
    image = image.resize((120, 40), Image.Resampling.NEAREST)

    # Draw noise on the larger image
    draw = ImageDraw.Draw(image)
    for _ in range(5):
        draw.line(
            [
                (secrets.randbelow(120), secrets.randbelow(40)),
                (secrets.randbelow(120), secrets.randbelow(40)),
            ],
            fill=(100, 100, 100),
        )

    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


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
            msg = EmailMessage(
                subject="Web Site Visitor",
                body=(
                    f"From {name}, {email}\n\n"
                    f"{body}\n\n"
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
            msg.send(fail_silently=False)
        except BadHeaderError:
            messages.error(request, "Invalid header found.")
            return redirect("base:contact")

        messages.success(
            request,
            "Your message was sent successfully.\nWe will touch you back soon.",
        )
        return redirect("base:home")


class DraftList(LoginRequiredMixin, YearContext, ListView):
    template_name = "base/portfolio_list.html"
    queryset = Project.objects.filter(draft=True).prefetch_related(
        "projectportfolio_set"
    )


class DraftDetail(LoginRequiredMixin, YearContext, DetailView):
    template_name = "base/portfolio_detail.html"
    queryset = Project.objects.filter(draft=True).prefetch_related(
        "projectportfolio_set"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["portfolios"] = self.object.projectportfolio_set.all()
        return context
