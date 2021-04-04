from abc import ABC, abstractmethod
from typing import Optional


class BaseGateway(ABC):
    @property
    @abstractmethod
    def description(self):
        """
        :return: Returned a description of gateway implementation
        """
        raise NotImplementedError

    @abstractmethod
    def send_command_add_customer(self, *args, **kwargs) -> Optional[str]:
        """
        Try to open service for subscriber on gateway
        :return: text representation of error if it happened
        """

    @abstractmethod
    def send_command_del_customer(self, *args, **kwargs) -> Optional[str]:
        """
        Try to close service for subscriber on gateway
        :return: text representation of error if it happened
        """

    @abstractmethod
    def send_command_sync_customer(self, *args, **kwargs) -> Optional[str]:
        """
        Try to synchronize subscriber service on gateway
        :return: text representation of error if it happened
        """

    @abstractmethod
    def ping_customer(self, *args, **kwargs) -> Optional[str]:
        """
        Try to ping-pong with subscribers device
        :return: text representation of error if it happened
        """
