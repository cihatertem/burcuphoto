FROM python:3.13-slim

LABEL maintainer="Cihat Ertem <cihatertem@gmail.com>"

ENV PYTHONUNBUFFERED=1

RUN groupadd -r django && useradd --no-log-init -r -g django django

COPY requirements.txt /tmp

RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade --no-cache-dir pip \
    && /venv/bin/pip install --upgrade --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

ENV PATH="/venv/bin:$PATH"

WORKDIR /app

COPY . .

RUN chown -R django:django /app

USER django

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "burcu_photo.wsgi:application"]
