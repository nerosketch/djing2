from django.apps import AppConfig


class DevicesConfig(AppConfig):
    name = "devices"

    def ready(self):
        from devices import signals  # noqa
        from devices import tasks  # noqa
        # from devices.device_config import pon, switch  # noqa
