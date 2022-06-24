from typing import overload, AnyStr
from dataclasses import dataclass
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from addresses.models import AddressModel, AddressModelTypes
from customers.models import Customer, PassportInfo
from customers_legal.models import CustomerLegalModel


@dataclass(frozen=True)
class CustomerChecksRes:
    passport: PassportInfo
    passport_parent_addr: AddressModel
    parent_street: AddressModel


class CheckFailedException(ValidationError): pass


@overload
def _addr_get_parent(addr: AddressModel) -> AddressModel: ...
@overload
def _addr_get_parent(addr: AddressModel, err_msg: AnyStr) -> AddressModel: ...

def _addr_get_parent(addr, err_msg=None):
    # TODO: Cache address hierarchy
    addr_parent_region = addr.get_address_item_by_type(
        addr_type=AddressModelTypes.STREET
    )
    if not addr_parent_region:
        if err_msg is not None:
            raise CheckFailedException(str(err_msg))
        raise CheckFailedException('Parent street does not exists for "%s"' % addr)
    return addr_parent_region


def customer_checks(customer: Customer) -> CustomerChecksRes:
    if not hasattr(customer, "address"):
        raise CheckFailedException(
            _('Customer "%s" [%s] has no address') % (
                customer, customer.username
            ))

    if not hasattr(customer, "passportinfo"):
        raise CheckFailedException(_('Customer "%s" [%s] has no passport info') % (
            customer,
            customer.username
        ))

    if not customer.customercontractmodel_set.exists():
        raise CheckFailedException(
            _('Customer "%s" [%s] has no contract') % (
                customer, customer.username
            ))

    passport = customer.passportinfo

    passport_addr = passport.registration_address
    if not passport_addr:
        raise CheckFailedException(
            _('Customer \"%s\" [%s] has no address in passport') % (
                customer, customer.username
            )
        )

    if not customer.address.parent_addr:
        raise CheckFailedException(
            _('Customer "%s" has address without parent address object') % customer
        )

    addr_passport_parent_region = _addr_get_parent(
        passport_addr,
        _('Customer "%s" with login "%s" passport registration address has no parent street element') % (
            customer,
            customer.username
        )
    )

    addr_parent_street_region = _addr_get_parent(
        customer.address,
        _('Customer "%s" with login "%s" address has no parent street element') % (
            customer,
            customer.username
        )
    )

    return CustomerChecksRes(
        passport=passport,
        passport_parent_addr=addr_passport_parent_region,
        parent_street=addr_parent_street_region
    )


@dataclass(frozen=True)
class CustomerLegalCheckRes:
    addr: AddressModel
    parent_street: AddressModel
    post_addr: AddressModel
    post_addr_parent_street: AddressModel
    delivery_addr: AddressModel
    delivery_parent_street: AddressModel


def customer_legal_checks(legal: CustomerLegalModel) -> CustomerLegalCheckRes:
    """Тут проверяются все требования для абонентских учёток,
       которые являются филиалами ЮЛ.
    """
    addr: AddressModel = legal.address

    if legal.post_address:
        post_addr = legal.post_address
    else:
        post_addr = addr

    if legal.delivery_address:
        delivery_addr = legal.delivery_address
    else:
        delivery_addr = addr

    addr_parent_street_region = _addr_get_parent(
        addr,
        _('Legal customer "%s" with login "%s" address has no parent street element') % (
            legal,
            legal.username
        )
    )
    post_addr_parent_region = _addr_get_parent(
        post_addr,
        _('Legal customer "%s" with login "%s" post address has no parent street element') % (
            legal,
            legal.username
        )
    )
    delivery_addr_parent_region = _addr_get_parent(
        delivery_addr,
        _('Legal customer "%s" with login "%s" delivery address has no parent street element') % (
            legal,
            legal.username
        )
    )

    return CustomerLegalCheckRes(
        addr=addr,
        parent_street=addr_parent_street_region,
        post_addr=post_addr,
        post_addr_parent_street=post_addr_parent_region,
        delivery_addr=delivery_addr,
        delivery_parent_street=delivery_addr_parent_region,
    )


def customer_legal_branch_checks(customer_branch: Customer):
    pass
