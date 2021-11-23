import logging
from datetime import datetime
from typing import Iterable, Optional

from django.db.models import Subquery, OuterRef
from django.utils.translation import gettext_lazy as _
from addresses.models import AddressModelTypes, AddressModel
from customers_legal.models import CustomerLegalModel
from customers.models import Customer
from sorm_export.models import (
    CommunicationStandardChoices,
    CustomerDocumentTypeChoices,
)
from sorm_export.serializers import individual_entity_serializers
from .base import iterable_export_decorator, simple_export_decorator, format_fname, iterable_gen_export_decorator


def _addr2str(addr: Optional[AddressModel]) -> str:
    if not addr:
        return ''
    return str(addr.title)


@iterable_gen_export_decorator
def export_customer_root(customers: Iterable[Customer], event_time=None):
    """
    Файл данных по абонентам v1.
    В этом файле выгружается корневая запись всей иерархии
    данных об абоненте, ошибки загрузки в этом файле приводят
    к каскадным ошибкам загрузки связанных данных в других файлах.
    :return: data, filename
    """

    def _gen():
        lgl_sb = CustomerLegalModel.objects.filter(branches__id=OuterRef('pk')).values('pk')
        for customer in customers.annotate(legal_id=Subquery(lgl_sb)):
            yield {
                "customer_id": customer.pk,
                "legal_customer_id": customer.legal_id if customer.legal_id is not None else customer.pk,
                # TODO: Upload contract date from contracts
                "contract_start_date": customer.create_date,
                "customer_login": customer.username,
                "communication_standard": CommunicationStandardChoices.ETHERNET.value,
            }

    return (
        individual_entity_serializers.CustomerRootObjectFormat,
        _gen,
        f"ISP/abonents/abonents_v1_{format_fname(event_time)}.txt",
    )


@iterable_export_decorator
def export_contract(contracts, event_time=None):
    """
    Файл данных по договорам.
    В этом файле выгружаются данные по договорам абонентов.
    :return:
    """

    def gen(contract):
        return {
            "contract_id": contract.pk,
            "customer_id": contract.customer_id,
            "contract_start_date": contract.start_service_time.date(),
            'contract_end_date': contract.end_service_time.date() if contract.end_service_time else None,
            "contract_number": contract.contract_number,
            "contract_title": "Договор на оказание услуг связи",
            # "contract_title": contract.title,
        }

    return (
        individual_entity_serializers.CustomerContractObjectFormat,
        gen,
        contracts,
        f"ISP/abonents/contracts_{format_fname(event_time)}.txt",
    )


def _addr_get_parent(addr: AddressModel, err_msg=None):
    # TODO: Cache address hierarchy
    addr_parent_region = addr.get_address_item_by_type(
        addr_type=AddressModelTypes.STREET
    )
    if not addr_parent_region:
        if err_msg is not None:
            logging.error(err_msg)
        return
    return addr_parent_region


@iterable_export_decorator
def export_access_point_address(customers: Iterable[Customer], event_time=None):
    """
    Файл выгрузки адресов точек подключения, версия 1.
    В этом файле выгружается информация о точках подключения оборудования - реальном адресе,
    на котором находится оборудование абонента, с помощью которого он пользуется услугами оператора связи.
    TODO: Выгружать адреса абонентов чъё это оборудование.
    TODO: Записывать адреса к устройствам абонентов. Заполнять при создании устройства.
    Сейчас у нас оборудование абонента ставится у абонента дома, так что это тот же адрес
    что и у абонента.
    """

    def gen(customer: Customer):
        if not hasattr(customer, "address"):
            logging.error(_('Customer "%s" has no address') % customer)
            return
        addr = customer.address
        if not addr:
            logging.error(_('Customer "%s" has no address') % customer)
            return
        if not addr.parent_addr:
            logging.error(_('Customer "%s" has address without parent address object') % customer)
            return
        create_date = customer.create_date
        addr_house = _addr2str(addr.get_address_item_by_type(
            addr_type=AddressModelTypes.HOUSE
        ))
        addr_office = _addr2str(addr.get_address_item_by_type(
            addr_type=AddressModelTypes.OFFICE_NUM
        ))
        if not addr_house and not addr_office:
            logging.error(_('Customer "%s" has no house nor office in address "%s"') % (customer, addr))
            return
        addr_parent_region = _addr_get_parent(
            addr,
            _('Customer "%s" with login "%s" address has no parent street element') % (
                customer,
                customer.username
            )
        )
        addr_building = _addr2str(addr.get_address_item_by_type(
            addr_type=AddressModelTypes.BUILDING
        ))
        addr_corpus = _addr2str(addr.get_address_item_by_type(
            addr_type=AddressModelTypes.CORPUS
        ))

        return {
            "ap_id": addr.pk,
            "customer_id": customer.pk,
            "house": addr_house or addr_office,
            "parent_id_ao": addr_parent_region.pk,
            "house_num": addr_house or None,
            "builing": addr_building,
            "building_corpus": addr_corpus or None,
            "full_address": addr.full_title(),
            "actual_start_time": datetime(create_date.year, create_date.month, create_date.day),
            # TODO: указывать дату конца, когда абонент выключается или удаляется
            # 'actual_end_time':
        }

    return (
        individual_entity_serializers.CustomerAccessPointAddressObjectFormat,
        gen,
        customers.select_related(
            "address", "address__parent_addr"
        ),
        f"ISP/abonents/ap_region_v1_{format_fname(event_time)}.txt",
    )


@iterable_export_decorator
def export_individual_customer(customers_queryset, event_time=None):
    """
    Файл выгрузки данных о физическом лице, версия 2
    В этом файле выгружается информация об абонентах, у которых контракт заключён с физическим лицом.
    Выгружаются только абоненты с паспортными данными.
    """

    def gen(customer: Customer):
        if not hasattr(customer, "passportinfo"):
            logging.error('Customer "%s" has no passport info' % customer)
            return
        addr = customer.address
        if not addr:
            logging.error(_('Customer "%s" has no address') % customer)
            return

        passport = customer.passportinfo
        create_date = customer.create_date
        full_fname = customer.get_full_name()

        addr_house = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.HOUSE
        )
        addr_building = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.BUILDING
        )
        addr_corp = addr.get_address_item_by_type(
            addr_type=AddressModelTypes.BUILDING
        )
        addr_parent_region = _addr_get_parent(
            addr,
            _('Customer "%s" with login "%s" address has no parent street element') % (
                customer,
                customer.username
            )
        )

        r = {
            "contract_id": customer.pk,
            "name": full_fname,
            "surname": full_fname,
            "birthday": customer.birth_day,
            "document_type": CustomerDocumentTypeChoices.PASSPORT_RF,
            "document_serial": passport.series,
            "document_number": passport.number,
            "document_distributor": passport.distributor,
            "passport_code": passport.division_code or "",
            "passport_date": passport.date_of_acceptance,
            "house": addr.title,
            "parent_id_ao": addr_parent_region.pk,
            "house_num": addr_house.title if addr_house else None,
            "building": addr_building.title if addr_building else None,
            "building_corpus": addr_corp.title if addr_corp else None,
            "actual_start_time": datetime(create_date.year, create_date.month, create_date.day),
            # 'actual_end_time':
            "customer_id": customer.pk,
        }
        surname, name, last_name = customer.split_fio()
        if surname is not None:
            r['surname'] = surname
        if name is not None:
            r['name'] = name
        if last_name is not None:
            r['last_name'] = last_name
        return r

    return (
        individual_entity_serializers.CustomerIndividualObjectFormat,
        gen,
        customers_queryset.exclude(passportinfo=None).select_related("group", "passportinfo"),
        f"ISP/abonents/fiz_v2_{format_fname(event_time)}.txt",
    )


@iterable_gen_export_decorator
def export_legal_customer(legal_customers: Iterable[CustomerLegalModel], event_time=None):
    """
    Файл выгрузки данных о юридическом лице версия 5.
    В этом файле выгружается информация об абонентах у которых контракт заключён с юридическим лицом.
    """

    def _iter_customers(legal):
        for customer in legal.branches.all():
            addr: AddressModel = legal.address
            if not addr:
                continue

            if not legal.post_address:
                post_addr = addr
            else:
                post_addr = legal.post_address

            if not legal.delivery_address:
                delivery_addr = legal.address
            else:
                delivery_addr = legal.delivery_address

            addr_parent_region = _addr_get_parent(
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
            res = {
                'legal_id': legal.pk,
                'legal_title': legal.title,
                'inn': legal.tax_number,
                'post_index': legal.post_index,
                'office_addr': _addr2str(addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.OFFICE_NUM
                )),
                'parent_id_ao': addr_parent_region.pk,
                'house': _addr2str(addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.HOUSE
                )) or None,
                'building': _addr2str(addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.BUILDING
                )) or None,
                'building_corpus': _addr2str(addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.CORPUS
                )),
                'full_description': addr.full_title(),
                # TODO: fill contact_telephones
                # 'contact_telephones': '',
                'post_post_index': legal.post_post_index or legal.post_index,
                'office_post_addr': _addr2str(post_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.OFFICE_NUM
                )),
                'post_parent_id_ao': post_addr_parent_region.pk,
                'post_house': _addr2str(post_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.HOUSE
                )) or None,
                'post_building': _addr2str(post_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.BUILDING
                )) or None,
                'post_building_corpus': _addr2str(post_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.BUILDING
                )),
                'post_full_description': post_addr.full_title(),
                'post_delivery_index': legal.delivery_address_post_index or legal.post_index,
                'office_delivery_address': _addr2str(delivery_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.OFFICE_NUM
                )),
                'parent_office_delivery_address_id': delivery_addr_parent_region.pk,
                'office_delivery_address_house': _addr2str(delivery_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.HOUSE
                )) or None,
                'office_delivery_address_building': _addr2str(delivery_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.BUILDING
                )) or None,
                'office_delivery_address_building_corpus': _addr2str(delivery_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.CORPUS
                )),
                'office_delivery_address_full_description': delivery_addr.full_title(),
                'actual_start_time': datetime.combine(customer.create_date, datetime.min.time()),
                #'actual_end_time': '',
                'customer_id': customer.pk,
            }
            bank_info = legal.legalcustomerbankmodel
            if bank_info:
                res.update({
                    'customer_bank': bank_info.title,
                    'customer_bank_num': bank_info.number,
                })
            yield res

    def _gen():
        legals = legal_customers.select_related('address', 'delivery_address', 'post_address')
        for l in legals:
            yield from _iter_customers(l)

    return (
        individual_entity_serializers.CustomerLegalObjectFormat,
        _gen,
        f'ISP/abonents/jur_v5_{format_fname(event_time)}.txt'
    )


@simple_export_decorator
def export_contact(customer_tels, event_time=None):
    """
    Файл данных по контактной информации.
    В этом файле выгружается контактная информация
    для каждого абонента - ФИО, телефон и факс контактного лица.
    """
    ser = individual_entity_serializers.CustomerContactObjectFormat(data=customer_tels, many=True)
    return ser, f"ISP/abonents/contact_phones_v1_{format_fname(event_time)}.txt"
