from django.apps import AppConfig


class RadiusAppConfig(AppConfig):
    name = "radiusapp"

    def ready(self):
        from radiusapp import signals  # noqa
