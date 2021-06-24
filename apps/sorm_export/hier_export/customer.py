from datetime import datetime
from typing import Iterable

from customers.models import Customer, CustomerStreet
from sorm_export.models import (
    CommunicationStandardChoices,
    CustomerDocumentTypeChoices,
    ExportFailedStatus,
    FiasRecursiveAddressModel
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
            'legal_customer_id': customer.pk,
            'contract_start_date': customer.create_date,
            'customer_login': customer.username,
            'communication_standard': CommunicationStandardChoices.ETHERNET.value
        }

    return (
        individual_entity_serializers.CustomerRootObjectFormat,
        gen, customers,
        f'ISP/abonents/abonents_v1_{format_fname(event_time)}.txt'
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
        f'ISP/abonents/contracts_{format_fname(event_time)}.txt'
    )


@simple_export_decorator
def export_address_object(fias_addr: FiasRecursiveAddressModel, event_time=None):
    """
    Файл выгрузки адресных объектов.
    В этом файле выгружается иерархия адресных объектов, которые фигурируют
    в адресах прописки и точек подключения оборудования.
    За один вызов этой процедуры выгружается адресная
    инфа по одному адресному объекту. Чтобы выгрузить несколько адресных объектов -
    можно вызвать её в цикле.
    """

    dat = {
        'address_id': str(fias_addr.pk),
        'parent_id': str(fias_addr.parent_ao_id) if fias_addr.parent_ao_id is not None else '',
        'type_id': fias_addr.ao_type,
        'region_type': fias_addr.get_ao_type_display(),
        'title': fias_addr.title,
        'full_title': "%s %s" % (fias_addr.get_ao_type_display(), fias_addr.title)
    }

    ser = individual_entity_serializers.AddressObjectFormat(
        data=dat
    )
    return ser, f'ISP/abonents/regions_{format_fname(event_time)}.txt'


def make_address_street_object(street: CustomerStreet, event_time=None):
    """
    Тут формируется формат выгрузки улицы в дополение в выгрузкам адресных объектов.
    :param street: customers.CustomerStreet model instance.
    :param event_time:
    :return:
    """
    # FIXME: расчитывать код улицы.
    dat = {
        'address_id': str(street.pk),
        'parent_id': str(street.group_id),
        'type_id': 6576,
        'region_type': 'ул.',
        'title': street.name,
        'full_title': "ул. %s" % street.name
    }
    ser = individual_entity_serializers.AddressObjectFormat(
        data=dat
    )
    return ser


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
        if not hasattr(customer, 'group'):
            return
        group = customer.group
        if not hasattr(group, 'fiasrecursiveaddressmodel'):
            return
        if not hasattr(group.fiasrecursiveaddressmodel, 'fias_recursive_address'):
            return
        addr_group = group.fiasrecursiveaddressmodel.fias_recursive_address
        if not addr_group.parent_ao:
            return
        parent_id_ao = addr_group.parent_ao_id
        return {
            'ap_id': addr_group.pk,
            'customer_id': customer.pk,
            'house': customer.house,
            'full_address': customer.get_address(),
            'parent_id_ao': parent_id_ao,
            'house_num': customer.house,
            'actual_start_time': customer.create_date,
            # TODO: указывать дату конца, когда абонент выключается или удаляется
            # 'actual_end_time':
        }
    return (
        individual_entity_serializers.CustomerAccessPointAddressObjectFormat,
        gen, customers.select_related(
            'group',
            'group__fiasrecursiveaddressmodel',
            'group__fiasrecursiveaddressmodel__fias_recursive_address'
        ),
        f'ISP/abonents/ap_region_v1_{format_fname(event_time)}.txt'
    )


@iterable_export_decorator
def export_individual_customer(customers_queryset, event_time=None):
    """
    Файл выгрузки данных о физическом лице, версия 2
    В этом файле выгружается информация об абонентах, у которых контракт заключён с физическим лицом.
    Выгружаются только абоненты с паспортными данными.
    """
    def gen(customer: Customer):
        if not hasattr(customer, 'passportinfo'):
            print('Customer "%s" has no passport info' % customer)
            return
        if not hasattr(customer, 'group'):
            return
        group = customer.group

        addr_group = group.fiasrecursiveaddressmodel_set.first()
        if addr_group is None:
            return
        passport = customer.passportinfo
        create_date = customer.create_date
        return {
            'contract_id': customer.pk,
            'name': customer.fio,
            'surname': customer.get_full_name(),
            'birthday': customer.birth_day,
            'document_type': CustomerDocumentTypeChoices.PASSPORT_RF,
            'document_serial': passport.series,
            'document_number': passport.number,
            'document_distributor': passport.distributor,
            'passport_code': passport.division_code or '',
            'passport_date': passport.date_of_acceptance,
            'house': customer.house,
            'parent_id_ao': addr_group.pk,
            'actual_start_time': datetime(create_date.year, create_date.month, create_date.day),
            # 'actual_end_time':
            'customer_id': customer.pk
        }

    return (
        individual_entity_serializers.CustomerIndividualObjectFormat,
        gen, customers_queryset.exclude(passportinfo=None).select_related(
            'group', 'passportinfo'
        ),
        f'ISP/abonents/fiz_v2_{format_fname(event_time)}.txt'
    )


@iterable_export_decorator
def export_legal_customer(customers: Iterable[Customer], event_time=None):
    """
    Файл выгрузки данных о юридическом лице версия 4.
    В этом файле выгружается информация об абонентах у которых контракт заключён с юридическим лицом.
    """
    raise ExportFailedStatus('Not implemented')
    # def gen(customer: Customer):
    #     return {
    #         ''
    #     }
    # return (
    #     individual_entity_serializers.CustomerLegalObjectFormat,
    #     gen, customers,
    #     f'ISP/abonents/jur_v4_{format_fname(event_time)}.txt'
    # )


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
    return ser, f'ISP/abonents/contact_phones_v1_{format_fname(event_time)}.txt'
