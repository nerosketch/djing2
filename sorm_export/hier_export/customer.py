from customers.models import Customer
from sorm_export.models import CommunicationStandardChoices
from sorm_export.serializers import individual_entity_serializers
from .base import exp_dec, format_fname


@exp_dec
def export_customer_root(customer: Customer):
    """
    Файл данных по абонентам v1.
    В этом файле выгружается корневая запись всей иерархии
    данных об абоненте, ошибки загрузки в этом файле приводят
    к каскадным ошибкам загрузки связанных данных в других файлах.
    :return: data, filename
    """
    fname = f'abonents_v1_{format_fname()}.txt'
    dat = [{
        'customer_id': customer.pk,
        'contract_start_date': customer.create_date,
        'customer_login': customer.pk,
        'communication_standard': CommunicationStandardChoices.ETHERNET
    }]

    ser = individual_entity_serializers.CustomerIncrementalRootFormat(
        data=dat, many=True
    )
    return ser, fname


@exp_dec
def export_contract(customer: Customer):
    """
    Файл данных по договорам.
    В этом файле выгружаются данные по договорам абонентов.
    :return:
    """
    fname = f'contracts_{format_fname()}.txt'
    dat = [{
        'contract_id': customer.pk,
        'customer_id': customer.pk,
        'contract_start_date': customer.create_date,
        'contract_end_date': '',  # TODO: у нас не логируется когда абонент заканчивает пользоваться услугами
        'contract_number': customer.username,
        'contract_title': ''  # TODO: ??????????
    }]
    ser = individual_entity_serializers.CustomerIncrementalContractFormat(
        data=dat, many=True
    )
    return ser, fname


@exp_dec
def export_address(customer: Customer):
    """
    Файл выгрузки адресных объектов.
    В этом файле выгружается иерархия адресных объектов, которые фигурируют
    в адресах прописки и точек подключения оборудования.
    """
    fname = f'regions_{format_fname()}.txt'
    # TODO: где брать соответствия кодов фиас, сёлами и пгт.
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
    return ser, fname


@exp_dec
def export_access_point_address(customer: Customer):
    """
    Файл выгрузки адресов точек подключения, версия 1.
    В этом файле выгружается информация о точках подключения оборудования - реальном адресе,
    на котором находится оборудование абонента, с помощью которого он пользуется услугами оператора связи.
    """
    fname = f'ap_region_v1_{format_fname()}.txt'
    # TODO: что писать в id точки? У нас нет такой сущьности
    dat = [{
        ''
    }]
    ser = individual_entity_serializers.CustomerIncrementalAccessPointAddressFormat(
        data=dat, many=True
    )
    return ser, fname


@exp_dec
def export_individual_customer(customer: Customer):
    """
    Файл выгрузки данных о физическом лице, версия 1
    В этом файле выгружается информация об абонентах, у которых контракт заключён с физическим лицом.
    """
    fname = f'fiz_v1_{format_fname()}.txt'
    # TODO: make fill data
    dat = [{
        ''
    }]
    ser = individual_entity_serializers.CustomerIncrementalIndividualFormat(
        dat=dat, many=True
    )
    return ser, fname


@exp_dec
def export_legal_customer(customer: Customer):
    """
    Файл выгрузки данных о юридическом лице версия 4.
    В этом файле выгружается информация об абонентах у которых контракт заключён с юридическим лицом.
    """
    fname = f'jur_v4_{format_fname()}.txt'
    dat = [{
        ''
    }]
    ser = individual_entity_serializers.CustomerIncrementalLegalFormat(
        data=dat, many=True
    )
    return ser, fname


@exp_dec
def export_contact(customer: Customer):
    """
    Файл данных по контактной информации.
    В этом файле выгружается контактная информация
    для каждого абонента - ФИО, телефон и факс контактного лица.
    """
    fname = f'contact_phones_v1_{format_fname()}.txt'
    dat = [{
        ''
    }]
    ser = individual_entity_serializers.CustomerIncrementalContactFormat(
        data=dat, many=True
    )
    return ser, fname
