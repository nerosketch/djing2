from abc import ABC, abstractmethod
from datetime import datetime
from typing import AnyStr, Optional, Union


class ServiceBase(ABC):
    @abstractmethod
    def calc_cost(self) -> float:
        """Calculates total cost of payment"""
        raise NotImplementedError

    @abstractmethod
    def calc_deadline(self) -> datetime:
        """Calculate deadline date"""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> AnyStr:
        """
        Usage in djing2.lib.IntegerChoicesClassAdapter for choices fields.
        :return: human readable description
        """

    @staticmethod
    def manage_access(customer) -> bool:
        """Manage for access to customer services"""
        if not customer.is_active:
            return False
        act_srv = customer.active_service()
        if act_srv:
            return True
        return False

    @classmethod
    def __str__(cls):
        return cls.description


class PeriodicPayCalcBase(ABC):
    @abstractmethod
    def calc_amount(self, model_object) -> float:
        """
        :param model_object: it is a instance of models.PeriodicPay model
        :return: float: amount for the service
        """
        raise NotImplementedError

    @abstractmethod
    def get_next_time_to_pay(self, model_object, last_time_payment: Optional[Union[datetime, None]]) -> datetime:
        """
        :param model_object: it is a instance of models.PeriodicPay model
        :param last_time_payment: May be None if first pay
        :return: datetime.datetime: time for next pay
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> AnyStr:
        """Return text description.
        Uses in djing2.lib.IntegerChoicesClassAdapter for CHOICES fields"""


class OneShotBaseService(ABC):
    @property
    @abstractmethod
    def description(self) -> AnyStr:
        """Return text description.
        Uses in djing2.lib.IntegerChoicesClassAdapter for CHOICES fields"""

    @abstractmethod
    def calc_cost(self, model_object, customer) -> float:
        """
        :param model_object: it is a instance of models.OneShotPay model
        :param customer: instance of custmers.Customer model
        :return: float: amount for the service
        """
        raise NotImplementedError

    @abstractmethod
    def before_pay(self, customer):
        raise NotImplementedError

    @abstractmethod
    def after_pay(self, customer):
        raise NotImplementedError
