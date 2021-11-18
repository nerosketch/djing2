from django.apps import AppConfig


class DevicesConfig(AppConfig):
    name = "devices"

    def ready(self):
        from devices import signals  # noqa
        from devices import tasks  # noqa

        # init device configs, i.e. add them to base_device_strategy.global_device_types_map
        # via BaseDeviceStrategyContext.set_device_type()
        from devices.device_config import pon, switch  # noqa
