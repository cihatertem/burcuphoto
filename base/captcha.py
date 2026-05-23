import base64
import secrets
from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageDraw

CAPTCHA_NUM1_KEY = "contact_captcha_num1"
CAPTCHA_NUM2_KEY = "contact_captcha_num2"
CAPTCHA_ANS_KEY = "contact_captcha_answer"


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


@lru_cache(maxsize=128)
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
