from django.dispatch import Signal

# Signal raises when monitoring event triggered
# Params:
# - sender: Device class
# - instance: Device instance
# - recipients: Profile pk list
# - text: Notification text
device_monitoring_event_signal = Signal()
