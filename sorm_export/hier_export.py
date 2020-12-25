from datetime import datetime

from customers.models import Customer
from sorm_export.models import CommunicationStandardChoices
from sorm_export.serializers import individual_entity_serializers

_fname_date_format = '%d%m%Y%H%M%S'


def _format_fname(fname_timestamp=None) -> str:
    if fname_timestamp is None:
        fname_timestamp = datetime.now()
    return fname_timestamp.strftime(_fname_date_format)


def export_customer_root(customer: Customer):
    """
    Файл данных по абонентам v1.
    В этом файле выгружается корневая запись всей иерархии
    данных об абоненте, ошибки загрузки в этом файле приводят
    к каскадным ошибкам загрузки связанных данных в других файлах.
    :return: data, filename
    """
    fname = f'abonents_v1_{_format_fname()}.txt'
    dat = [
        {
            'customer_id': customer.pk,
            'contract_start_date': customer.create_date,
            'customer_login': customer.pk,
            'communication_standard': CommunicationStandardChoices.FNDT
        },
    ]

    ser = individual_entity_serializers.CustomerIncrementalRootFormat(data=dat, many=True)
    ser.is_valid(raise_exception=True)
    return ser.data, fname


def export_contract(customer: Customer):
    """
    Файл данных по договорам.
    В этом файле выгружаются данные по договорам абонентов.
    :return:
    """
    fname = f'contracts_{_format_fname()}.txt'
    dat = [
        {
            'contract_id': customer.pk,
            'customer_id': customer.pk,
            'contract_start_date': customer.create_date,
            'contract_end_date': '',  # TODO: у нас не логируется когда абонент заканчивает пользоваться услугами
            'contract_number': customer.username,
            'contract_title': ''  # TODO: ??????????
        }
    ]
    ser = individual_entity_serializers.CustomerIncrementalContractFormat(data=dat, many=True)
    ser.is_valid(raise_exception=True)
    return ser.data, fname
