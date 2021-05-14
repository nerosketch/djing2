from django.apps import AppConfig


class MessengerConfig(AppConfig):
    name = "messenger"

    def ready(self):
        from messenger import signals  # noqa
