from django.apps import AppConfig


class ServicesConfig(AppConfig):
    name = "services"

    def ready(self) -> None:
        from services import signals  # noqa
        from services import tasks  # noqa
