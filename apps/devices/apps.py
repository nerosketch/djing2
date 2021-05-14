from django.apps import AppConfig


class DevicesConfig(AppConfig):
    name = "devices"

    def ready(self):
        from devices import signals  # noqa
