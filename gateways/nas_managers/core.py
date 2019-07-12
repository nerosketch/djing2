from abc import ABC, abstractmethod
from typing import Iterator, Tuple, Optional
from djing2 import ping
from gateways.nas_managers.structs import SubnetQueue, VectorQueue


# Raised if gw has returned failed result
class GatewayFailedResult(Exception):
    pass


# Raised when is no connection to the gw
class GatewayNetworkError(Exception):
    pass


# Communicate with gateway
class BaseTransmitter(ABC):
    @property
    @abstractmethod
    def description(self):
        """
        :return: Returnd a description of gateway implementation
        """

    def __init__(self, ip: str, *args, **kwargs):
        if not ping(ip):
            raise GatewayNetworkError('Gateway %(ip_addr)s does not pinged' % {
                'ip_addr': ip
            })

    @classmethod
    def get_description(cls):
        return cls.description

    @abstractmethod
    def add_user_range(self, queue_list: VectorQueue):
        """add customers list to gateway
        :param queue_list: Vector of instances of customers
        """

    @abstractmethod
    def remove_user_range(self, queues):
        """remove customers list
        :param queues: Vector of instances of customers
        """

    @abstractmethod
    def add_user(self, queue: SubnetQueue, *args):
        """add customer
        :param queue: Customer instance
        """

    @abstractmethod
    def remove_user(self, queue: SubnetQueue):
        """
        remove customer
        :param queue: Customer instance
        """

    @abstractmethod
    def update_user(self, queue: SubnetQueue, *args):
        """
        Update customer by uid, you can change everything except its uid.
        Customer will found by UID.
        :param queue: Customer instance
        """

    @abstractmethod
    def ping(self, host: str, count=10, arp=False) -> Optional[Tuple[int, int]]:
        """
        :param host: ip address in text view, for example '192.168.0.1'
        :param count: count of ping queries
        :param arp: Is use arp ping
        :return: None if not response, else tuple it contains count returned and count sent
        for example (received, sent) -> (7, 10).
        """

    @abstractmethod
    def read_users(self) -> VectorQueue:
        pass

    @abstractmethod
    def sync_nas(self, users_from_db: Iterator):
        """
        Synchronize db with gateway
        :param users_from_db: Queryset of allowed users
        :return: nothing
        """


# def diff_set(one: set, two: set) -> Tuple[set, set]:
#     list_for_del = (one ^ two) - one
#     list_for_add = one - two
#     return list_for_add, list_for_del
