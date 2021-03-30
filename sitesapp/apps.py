from django.apps import AppConfig


class SitesAppConfig(AppConfig):
    name = "sitesapp"

    def ready(self):
        from sitesapp import signals

        print("Imported signals", signals)
