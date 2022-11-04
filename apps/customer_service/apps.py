from django.apps import AppConfig


class CustomerServiceConfig(AppConfig):
    name = 'customer_service'

    def ready(self) -> None:
        from customer_service import signals  # noqa
        from customer_service import tasks  # noqa
