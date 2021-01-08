from typing import Iterable

from customers.models import Customer
from sorm_export.models import CommunicationStandardChoices
from sorm_export.serializers import individual_entity_serializers
from .base import iterable_export_decorator, simple_export_decorator, format_fname


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
            'customer_id': customer.pk,
            'contract_start_date': customer.create_date,
            'customer_login': customer.pk,
            'communication_standard': CommunicationStandardChoices.ETHERNET
        }

    return (
        individual_entity_serializers.CustomerIncrementalRootFormat,
        gen, customers,
        f'/home/cdr/ISP/abonents/abonents_v1_{format_fname(event_time)}.txt'
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
            'contract_id': customer.pk,
            'customer_id': customer.pk,
            'contract_start_date': customer.create_date,
            'contract_end_date': '',  # TODO: у нас не логируется когда абонент заканчивает пользоваться услугами
            'contract_number': customer.username,
            'contract_title': ''  # TODO: ??????????
        }

    return (
        individual_entity_serializers.CustomerIncrementalContractFormat,
        gen, customers,
        f'/home/cdr/ISP/abonents/contracts_{format_fname(event_time)}.txt'
    )


@simple_export_decorator
def export_address(customer: Customer, event_time=None):
    """
    Файл выгрузки адресных объектов.
    В этом файле выгружается иерархия адресных объектов, которые фигурируют
    в адресах прописки и точек подключения оборудования.
    """
    # TODO: где брать соответствия кодов фиас сёлам и пгт?
    dat = [
        {
            # Страна
            'address_id': 1,
            'type_id': 1,
            'region_type': 'стр',
            'title': 'Россия',
            'full_title': 'стр. Россия'
        },
        {
            # Город
            'address_id': 624,  # пгт◄═══════════╗
            'parent_id': 1,  # страна            ║
            'type_id': 624,  #                   ║
            'region_type': 'пгт',#               ║
            'title': "Нижнегорский",#            ║
            'full_title': 'пгт. Нижнегорский'  # ║
        },                     #                 ║
        {                      #                 ║
            # улица                              ║
            'address_id': 9129,  #               ║
            'parent_id': 624,  # ►═══════════════╝
            'type_id': 9129,
            'region_type': 'ул',
            'title': customer.street.name,
            'full_title': customer.get_address()
        }
    ]
    ser = individual_entity_serializers.CustomerIncrementalAddressFormat(
        data=dat, many=True
    )
    return ser, f'/home/cdr/ISP/abonents/regions_{format_fname(event_time)}.txt'


@iterable_export_decorator
def export_access_point_address(customers: Iterable[Customer], event_time=None):
    """
    Файл выгрузки адресов точек подключения, версия 1.
    В этом файле выгружается информация о точках подключения оборудования - реальном адресе,
    на котором находится оборудование абонента, с помощью которого он пользуется услугами оператора связи.
    """
    def gen(customer: Customer):
        return {
            ''
        }
    return (
        individual_entity_serializers.CustomerIncrementalAccessPointAddressFormat,
        gen, customers,
        f'/home/cdr/ISP/abonents/ap_region_v1_{format_fname(event_time)}.txt'
    )


@iterable_export_decorator
def export_individual_customer(customers: Iterable[Customer], event_time=None):
    """
    Файл выгрузки данных о физическом лице, версия 1
    В этом файле выгружается информация об абонентах, у которых контракт заключён с физическим лицом.
    """
    def gen(customer: Customer):
        return {
            ''
        }

    return (
        individual_entity_serializers.CustomerIncrementalIndividualFormat,
        gen, customers,
        f'/home/cdr/ISP/abonents/fiz_v1_{format_fname(event_time)}.txt'
    )


@iterable_export_decorator
def export_legal_customer(customers: Iterable[Customer], event_time=None):
    """
    Файл выгрузки данных о юридическом лице версия 4.
    В этом файле выгружается информация об абонентах у которых контракт заключён с юридическим лицом.
    """
    def gen(customer: Customer):
        return {
            ''
        }
    return (
        individual_entity_serializers.CustomerIncrementalLegalFormat,
        gen, customers,
        f'/home/cdr/ISP/abonents/jur_v4_{format_fname(event_time)}.txt'
    )


@simple_export_decorator
def export_contact(customer_tels, event_time=None):
    """
    Файл данных по контактной информации.
    В этом файле выгружается контактная информация
    для каждого абонента - ФИО, телефон и факс контактного лица.
    """
    ser = individual_entity_serializers.CustomerIncrementalContactFormat(
        data=customer_tels, many=True
    )
    return ser, f'/home/cdr/ISP/abonents/contact_phones_v1_{format_fname(event_time)}.txt'
