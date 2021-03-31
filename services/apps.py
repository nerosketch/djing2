from django.apps import AppConfig


class ServicesConfig(AppConfig):
    name = "services"

    def ready(self):
        from services import signals  # noqa
