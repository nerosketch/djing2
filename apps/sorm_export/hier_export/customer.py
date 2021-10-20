import logging
from datetime import datetime
from typing import Iterable, Optional

from addresses.models import AddressModelTypes, AddressModel
from customers_legal.models import CustomerLegalModel
from customers.models import Customer
from sorm_export.models import (
    CommunicationStandardChoices,
    CustomerDocumentTypeChoices,
)
from sorm_export.serializers import individual_entity_serializers
from .base import iterable_export_decorator, simple_export_decorator, format_fname, iterable_gen_export_decorator



@iterable_export_decorator
def export_customer_root(customers: Iterable[Customer], event_time=None):
    """
    Файл данных по абонентам v1.
    В этом файле выгружается корневая запись всей иерархии
    данных об абоненте, ошибки загрузки в этом файле приводят
    к каскадным ошибкам загрузки связанных данных в других файлах.
    :return: data, filename
    """

    def gen(customer: Customer):
        return {
            "customer_id": customer.pk,
            "legal_customer_id": customer.pk,
            "contract_start_date": customer.create_date,
            "customer_login": customer.username,
            "communication_standard": CommunicationStandardChoices.ETHERNET.value,
        }

    return (
        individual_entity_serializers.CustomerRootObjectFormat,
        gen,
        customers,
        f"ISP/abonents/abonents_v1_{format_fname(event_time)}.txt",
    )


@iterable_export_decorator
def export_contract(customers: Iterable[Customer], event_time=None):
    """
    Файл данных по договорам.
    В этом файле выгружаются данные по договорам абонентов.
    :return:
    """

    def gen(customer: Customer):
        return {
            "contract_id": customer.pk,
            "customer_id": customer.pk,
            "contract_start_date": customer.create_date,
            # TODO: contract_end_date заполняем когда контракт закончился
            # 'contract_end_date': customer.create_date + timedelta(days=3650),
            "contract_number": customer.username,
            # TODO: Название контракта а не имя абонента
            "contract_title": "Договор на оказание услуг связи" # customer.get_full_name(),
        }

    return (
        individual_entity_serializers.CustomerContractObjectFormat,
        gen,
        customers,
        f"ISP/abonents/contracts_{format_fname(event_time)}.txt",
    )


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
            return
        addr = customer.address
        if not addr.parent_addr:
            return
        return {
            "ap_id": addr.pk,
            "customer_id": customer.pk,
            "house": addr.title,
            "full_address": addr.full_title(),
            "parent_id_ao": addr.parent_addr_id,
            "house_num": customer.house,
            "actual_start_time": customer.create_date,
            # TODO: указывать дату конца, когда абонент выключается или удаляется
            # 'actual_end_time':
        }

    return (
        individual_entity_serializers.CustomerAccessPointAddressObjectFormat,
        gen,
        customers.select_related(
            "address"
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
            logging.warning('Customer "%s" has no passport info' % customer)
            return
        addr = customer.address
        if not addr:
            logging.warning('Customer "%s" has no address info' % customer)
            return

        passport = customer.passportinfo
        create_date = customer.create_date
        full_fname = customer.get_full_name()

        parent_addr_id = addr.parent_addr_id
        if not parent_addr_id:
            logging.warning("Address '%s' has no parent object" % addr)
            return

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
            "parent_id_ao": parent_addr_id,
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
def export_legal_customer(customers: Iterable[CustomerLegalModel], event_time=None):
    """
    Файл выгрузки данных о юридическом лице версия 5.
    В этом файле выгружается информация об абонентах у которых контракт заключён с юридическим лицом.
    """

    def _addr2str(addr: Optional[AddressModel]) -> str:
        if not addr:
            return ''
        return str(addr.title)

    def gen(legal: CustomerLegalModel):
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

            res = {
                'legal_id': legal.pk,
                'legal_title': legal.title,
                'inn': legal.tax_number,
                'post_index': legal.post_index,
                'office_addr': _addr2str(addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.OFFICE_NUM
                )),
                'parent_id_ao': legal.address_id,
                'house': _addr2str(addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.HOUSE
                )),
                'building': _addr2str(addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.BUILDING
                )),
                'building_corpus': _addr2str(addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.CORPUS
                )),
                'full_description': addr.full_title(),
                #'contact_telephones': '',
                'post_post_index': legal.post_post_index or legal.post_index,
                'office_post_addr': _addr2str(post_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.OFFICE_NUM
                )),
                'post_parent_id_ao': post_addr.pk,
                'post_house': _addr2str(post_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.HOUSE
                )),
                'post_building': _addr2str(post_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.BUILDING
                )),
                'post_building_corpus': _addr2str(post_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.BUILDING
                )),
                'post_full_description': post_addr.full_title(),
                'post_delivery_index': legal.delivery_address_post_index or legal.post_index,
                'office_delivery_address': _addr2str(delivery_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.OFFICE_NUM
                )),
                'parent_office_delivery_address_id': delivery_addr.pk,
                'office_delivery_address_house': _addr2str(delivery_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.HOUSE
                )),
                'office_delivery_address_building': _addr2str(delivery_addr.get_address_item_by_type(
                    addr_type=AddressModelTypes.BUILDING
                )),
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

    return (
        individual_entity_serializers.CustomerLegalObjectFormat,
        gen, customers.select_related('address', 'delivery_address', 'delivery_address'),
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
