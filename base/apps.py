from django.apps import AppConfig


class BaseConfig(AppConfig):
    __slot__ = "default_auto_field", "name"
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'base'
