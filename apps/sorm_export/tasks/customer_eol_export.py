from typing import Optional
from uwsgi_tasks import task, TaskExecutor
from datetime import datetime, date
from customers.models import AdditionalTelephone
from addresses.models import AddressModelTypes, AddressModel
from sorm_export.models import ExportStampTypeEnum,  CustomerDocumentTypeChoices
from sorm_export.tasks.task_export import task_export
from sorm_export.hier_export.base import format_fname
from sorm_export.hier_export.customer import (
    general_customer_filter_queryset,
    ContactSimpleExportTree
)
from sorm_export.serializers.individual_entity_serializers import CustomerIndividualObjectFormat
from profiles.models import split_fio


#
# TODO:
# Надо указать даты завершения актуальности данных при выгрузке завершения
# обслуживания абонента.
# При старте нового абонента данные по нему уже должны выгружаться при
# сигнале создания новой учётки, или при заполнении по ней необходимых данных.
# TODO: [Тут не понятно когда именно выгружается новая учётка]
#

def _general_customers_queryset_filter(customer_id: int):
    qs = general_customer_filter_queryset()
    return qs.filter(customer_id=customer_id)


#def export_root_customer_eol(customer_id: int, curr_time: datetime):
#    customers = _general_customers_queryset_filter(customer_id=customer_id)
#    data, fname = export_customer_root(customers=customers, event_time=curr_time)
#    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ROOT)


#def export_customer_contract_eol(customer_id: int, curr_time: datetime):
#    customers_qs = _general_customers_queryset_filter(customer_id=customer_id)
#    contracts = CustomerContractModel.objects.select_related('customer').filter(
#        customer__in=customers_qs,
#        customer_id=customer_id
#    )
#    data, fname = export_contract(contracts=contracts, event_time=curr_time)
#    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_CONTRACT)


def export_individual_customer_eol(customer_id: int,
                                   full_fname: str,
                                   birthday: date,
                                   document_type: CustomerDocumentTypeChoices,
                                   passport_series: str,
                                   passport_number: str,
                                   passport_distributor: str,
                                   passport_date_of_acceptance: date,
                                   house_title: str,
                                   addr_id: int,
                                   actual_start_date: datetime,
                                   actual_end_time: Optional[datetime] = None,
                                   passport_division_code='',
                                   curr_time: datetime=None):
    #  customers = _general_customers_queryset_filter(customer_id=customer_id)
    #  data, fname = export_individual_customer_one(customers_queryset=customers, event_time=curr_time)
    if curr_time is None:
        curr_time = datetime.now()

    # Get parent address id from customer address
    addr_parent_street = AddressModel.objects.get_address_by_type(
        addr_id=addr_id,
        addr_type=AddressModelTypes.STREET
    ).order_by('-address_type').first()
    # --------------------------------------------------
    if not addr_parent_street:
        return

    # Get address details
    addr_house = AddressModel.objects.get_address_by_type(
        addr_id=addr_id,
        addr_type=AddressModelTypes.HOUSE
    ).order_by('-address_type').first()
    addr_building = AddressModel.objects.get_address_by_type(
        addr_id=addr_id,
        addr_type=AddressModelTypes.BUILDING
    ).order_by('-address_type').first()
    addr_corp = AddressModel.objects.get_address_by_type(
        addr_id=addr_id,
        addr_type=AddressModelTypes.CORPUS
    ).order_by('-address_type').first()

    r = {
        "contract_id": customer_id,
        "name": full_fname,
        #  "last_name":   Ниже
        #  "surname":     Ниже
        "surname": full_fname,
        "birthday": birthday,
        "document_type": document_type,
        "document_serial": passport_series,
        "document_number": passport_number,
        "document_distributor": passport_distributor,
        "passport_code": passport_division_code or '',
        "passport_date": passport_date_of_acceptance,
        "house": house_title,
        "parent_id_ao": addr_parent_street.pk,
        "house_num": addr_house.title if addr_house else None,
        "building": addr_building.title if addr_building else None,
        "building_corpus": addr_corp.title if addr_corp else None,
        "actual_start_time": actual_start_date,
        "actual_end_time": actual_end_time,
        "customer_id": customer_id,
    }
    surname, name, last_name = split_fio(full_fname)
    if surname is not None:
        r['surname'] = surname
    if name is not None:
        r['name'] = name
    if last_name is not None:
        r['last_name'] = last_name

    ser = CustomerIndividualObjectFormat(data=r)
    ser.is_valid(raise_exception=True)
    fname = f"ISP/abonents/fiz_v2_{format_fname(curr_time)}.txt"
    task_export(ser.data, fname, ExportStampTypeEnum.CUSTOMER_INDIVIDUAL)


def export_customer_contact_eol(customer_id: int, actual_end_time: datetime, curr_time: datetime=None):
    if curr_time is None:
        curr_time = datetime.now()

    if actual_end_time is None:
        actual_end_time = curr_time

    customers_qs = _general_customers_queryset_filter(
        customer_id=customer_id
    ).only("pk", "telephone", "username", "fio", "create_date")
    customer_tels = [
        {
            "customer_id": c.pk,
            "contact": f"{c.get_full_name()} {c.telephone}",
            "actual_start_time": datetime(c.create_date.year, c.create_date.month, c.create_date.day),
            'actual_end_time': actual_end_time
        }
        for c in customers_qs.iterator()
    ]

    # export additional tels
    tels = AdditionalTelephone.objects.filter(customer__in=customers_qs).select_related("customer")
    customer_tels.extend(
        {
            "customer_id": t.customer_id,
            "contact": f"{t.customer.get_full_name()} {t.telephone}",
            "actual_start_time": t.create_time,
            'actual_end_time': actual_end_time
        }
        for t in tels.iterator()
    )

    exporter = ContactSimpleExportTree(event_time=curr_time)
    data = exporter.export(data=customer_tels, many=True)
    exporter.upload2ftp(data=data)


def customer_export_eol(
        customer_id: int,
        full_fname: str,
        birthday: date,
        document_type: CustomerDocumentTypeChoices,
        passport_series: str,
        passport_number: str,
        passport_distributor: str,
        passport_date_of_acceptance: date,
        house_title: str,
        addr_id: int,
        actual_start_date: datetime,
        curr_time: datetime,
        actual_end_time: Optional[datetime] = None,
        passport_division_code='',
    ):
    if actual_end_time is None:
        actual_end_time = datetime.now()
    export_root_customer_eol(
        customer_id=customer_id,
        curr_time=curr_time
    )
    export_customer_contract_eol(
        customer_id=customer_id,
        curr_time=curr_time
    )
    export_individual_customer_eol(
        customer_id=customer_id,
        full_fname=full_fname,
        birthday=birthday,
        document_type=document_type,
        passport_series=passport_series,
        passport_number=passport_number,
        passport_distributor=passport_distributor,
        passport_date_of_acceptance=passport_date_of_acceptance,
        house_title=house_title,
        addr_id=addr_id,
        actual_start_date=actual_start_date,
        actual_end_time=actual_end_time,
        passport_division_code=passport_division_code,
        curr_time=curr_time,
    )

    export_customer_contact_eol(
        customer_id=customer_id,
        curr_time=curr_time,
        actual_end_time=actual_end_time,
    )


@task(executor=TaskExecutor.SPOOLER)
def customer_export_eol_task(
        customer_id: int,
        full_fname: str,
        birthday: date,
        document_type: CustomerDocumentTypeChoices,
        passport_series: str,
        passport_number: str,
        passport_distributor: str,
        passport_date_of_acceptance: date,
        house_title: str,
        addr_id: int,
        actual_start_date: datetime,
        curr_time: datetime,
        actual_end_time: Optional[datetime] = None,
        passport_division_code='',
    ):
    customer_export_eol(
        customer_id=customer_id,
        full_fname=full_fname,
        birthday=birthday,
        document_type=document_type,
        passport_series=passport_series,
        passport_number=passport_number,
        passport_distributor=passport_distributor,
        passport_date_of_acceptance=passport_date_of_acceptance,
        house_title=house_title,
        addr_id=addr_id,
        actual_start_date=actual_start_date,
        actual_end_time=actual_end_time,
        passport_division_code=passport_division_code,
        curr_time=curr_time,
    )

