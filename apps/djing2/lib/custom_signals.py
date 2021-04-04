from django.dispatch import Signal

# Signal raises when some notification occurs
# Params:
# - sender: sender class
# - instance: sender instance
# - recipients: Profile pk list
# - text: Notification text
notification_signal = Signal()
