from abc import ABC, abstractmethod


class BaseMessengerInterface(ABC):

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
