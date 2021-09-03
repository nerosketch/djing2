from django.apps import AppConfig


class SormExportConfig(AppConfig):
    name = "sorm_export"

    def ready(self):
        from sorm_export import signals  # noqa
        from sorm_export import tasks  # noqa
