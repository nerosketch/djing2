import abc


class IAddressObject:
    @abc.abstractmethod
    def is_street(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def is_locality(self) -> bool:
        raise NotImplementedError


class IAddressContaining:
    @abc.abstractmethod
    def get_address(self) -> IAddressObject:
        raise NotImplementedError
