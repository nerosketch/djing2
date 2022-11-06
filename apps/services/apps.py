from django.apps import AppConfig


class ServicesConfig(AppConfig):
    name = "services"

    def ready(self) -> None:
        from service import signals  # noqa
