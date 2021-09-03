from django.apps import AppConfig


class RadiusAppConfig(AppConfig):
    name = "radiusapp"

    def ready(self):
        from radiusapp import signals  # noqa
        from radiusapp import tasks  # noqa
