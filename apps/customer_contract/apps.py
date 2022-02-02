from django.apps import AppConfig


class CustomerContractConfig(AppConfig):
    name = 'customer_contract'

    def ready(self):
        from customer_contract import signals  # noqa
        from customer_contract import tasks  # noqa
