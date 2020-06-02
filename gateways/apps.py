from django.apps import AppConfig


class GatewaysConfig(AppConfig):
    name = 'gateways'

    def ready(self):
        from gateways import signals
