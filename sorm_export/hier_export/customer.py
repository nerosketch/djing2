from datetime import datetime
from typing import Iterable

from customers.models import Customer
from sorm_export.models import (
    CommunicationStandardChoices,
    CustomerDocumentTypeChoices, FiasAddrGroupModel, ExportFailedStatus
)
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
            'customer_login': customer.username,
            'communication_standard': CommunicationStandardChoices.ETHERNET
        }

    return (
        individual_entity_serializers.CustomerRootObjectFormat,
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
            # TODO: contract_end_date заполняем когда контракт закончился
            # 'contract_end_date': customer.create_date + timedelta(days=3650),
            'contract_number': customer.username,
            # TODO: Название контракта а не имя абонента
            'contract_title': customer.get_full_name()
        }

    return (
        individual_entity_serializers.CustomerContractObjectFormat,
        gen, customers,
        f'/home/cdr/ISP/abonents/contracts_{format_fname(event_time)}.txt'
    )


@simple_export_decorator
def export_address(customer: Customer, event_time=None):
    """
    Файл выгрузки адресных объектов.
    В этом файле выгружается иерархия адресных объектов, которые фигурируют
    в адресах прописки и точек подключения оборудования.
    За один вызов этой процедуры выгружается адресная
    инфа по одному абоненту. Чтобы выгрузить адресы по пачке абонентов
    можно вызвать её в цикле.
    """

    # 1 - находим группу абонента
    group = customer.group
    # получаем населённый пункт по группе
    # TODO: Opimize
    if not hasattr(group, 'fiasaddr'):
        raise ExportFailedStatus('Customer "%s" group has not fias addr' % customer.get_short_name())
    if not hasattr(group.fiasaddr, 'fias_recursive_address'):
        raise ExportFailedStatus('fias addr has not info')
    addr_group = group.fiasaddr.fias_recursive_address

    # Получаем иерархию адресных объектов абонента

    dat = []
    while addr_group is not None:
        dat.append({
            'address_id': addr_group.pk,
            'parent_id': addr_group.parent_ao_id,
            'type_id': addr_group.ao_type,
            'region_type': addr_group.get_ao_type_display(),
            'title': addr_group.title,
            'full_title': "%s %s" % (addr_group.get_ao_type_display(), addr_group.title)
        })
        addr_group = addr_group.parent_ao

    ser = individual_entity_serializers.CustomerAddressObjectFormat(
        data=dat, many=True
    )
    return ser, f'/home/cdr/ISP/abonents/regions_{format_fname(event_time)}.txt'


@iterable_export_decorator
def export_access_point_address(customers: Iterable[Customer], event_time=None):
    """
    Файл выгрузки адресов точек подключения, версия 1.
    В этом файле выгружается информация о точках подключения оборудования - реальном адресе,
    на котором находится оборудование абонента, с помощью которого он пользуется услугами оператора связи.
    TODO: Выгружать адреса вбонентов чъё это оборудование.
    TODO: Записывать адреса к устройствам абонентов. Заполнять при создании устройства.
    """
    def gen(customer: Customer):
        return {
            ''
        }
    return (
        individual_entity_serializers.CustomerAccessPointAddressObjectFormat,
        gen, customers,
        f'/home/cdr/ISP/abonents/ap_region_v1_{format_fname(event_time)}.txt'
    )


@iterable_export_decorator
def export_individual_customer(customers: Iterable[Customer], event_time=None):
    """
    Файл выгрузки данных о физическом лице, версия 1
    В этом файле выгружается информация об абонентах, у которых контракт заключён с физическим лицом.
    Выгружаются только абоненты с паспортными данными.
    """
    def gen(customer: Customer):
        if not hasattr(customer, 'passportinfo'):
            print('Customer "%s" has no passport info' % customer)
            return
        passport = customer.passportinfo
        create_date = customer.create_date
        return {
            'customer_id': customer.pk,
            'name': customer.fio,
            'surname': customer.get_full_name(),
            'birthday': customer.birth_day,
            'document_type': CustomerDocumentTypeChoices.PASSPORT_RF,
            'document_serial': passport.series,
            'document_number': passport.number,
            'document_distributor': passport.distributor,
            # 'passport_code': passport.,
            'passport_date': passport.date_of_acceptance,
            'house': customer.house,
            # 'parent_id_ao': None,  # FIXME: ????
            'actual_start_time': datetime(create_date.year, create_date.month, create_date.day),
            # 'actual_end_time':
        }

    return (
        individual_entity_serializers.CustomerIndividualObjectFormat,
        gen, customers.exclude(passportinfo=None),
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
        individual_entity_serializers.CustomerLegalObjectFormat,
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
    ser = individual_entity_serializers.CustomerContactObjectFormat(
        data=customer_tels, many=True
    )
    return ser, f'/home/cdr/ISP/abonents/contact_phones_v1_{format_fname(event_time)}.txt'
