from django.apps import AppConfig


class NetworksConfig(AppConfig):
    name = "networks"

    def ready(self):
        from networks import signals  # noqa
        from networks import tasks  # noqa
