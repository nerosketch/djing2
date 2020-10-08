from abc import ABC, abstractmethod
from django.utils.translation import gettext_lazy as _


class BaseMessengerInterface(ABC):
    data_value = 0
    description = _('Undefined')

    @abstractmethod
    def send_webhook(self):
        raise NotImplementedError

    @abstractmethod
    def remove_webhook(self):
        raise NotImplementedError

    @abstractmethod
    def send_message_to_accs(self, receivers, msg_text: str):
        raise NotImplementedError

    @abstractmethod
    def send_message(self, msg_text: str):
        raise NotImplementedError

    @abstractmethod
    def inbox_data(self, data):
        raise NotImplementedError
