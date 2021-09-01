from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    name = "profiles"

    def ready(self):
        from profiles import signals  # noqa
        from profiles import tasks  # noqa
