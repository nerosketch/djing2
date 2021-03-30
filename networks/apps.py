from django.apps import AppConfig


class NetworksConfig(AppConfig):
    name = "networks"

    def ready(self):
        from networks import signals

        print("Imported signals", signals)
