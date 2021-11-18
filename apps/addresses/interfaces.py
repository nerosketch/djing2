import abc


class IAddressObject:
    @abc.abstractmethod
    def is_street(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def is_locality(self) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def str_representation(self) -> str:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.str_representation()


class IAddressContaining:
    @abc.abstractmethod
    def get_address(self) -> IAddressObject:
        raise NotImplementedError
