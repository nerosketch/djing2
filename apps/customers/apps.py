from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = "customers"

    def ready(self):
        from customers import signals  # noqa
        from customers import tasks  # noqa
