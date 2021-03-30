from django.apps import AppConfig


class MessengerConfig(AppConfig):
    name = "messenger"

    def ready(self):
        from messenger import signals

        print("Imported signals", signals)
