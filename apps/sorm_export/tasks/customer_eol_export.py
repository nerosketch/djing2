from uwsgi_tasks import task
from datetime import datetime
from customers.models import AdditionalTelephone
from customer_contract.models import CustomerContractModel
from sorm_export.models import ExportStampTypeEnum
from sorm_export.tasks.task_export import task_export
from sorm_export.hier_export.customer import (
    export_customer_root,
    export_contract,
    export_individual_customer,
    export_contact,
    general_customer_filter_queryset,
)


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


def export_root_customer_eol(customer_id: int):
    customers = _general_customers_queryset_filter(customer_id=customer_id)
    data, fname = export_customer_root(customers=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ROOT)


def export_customer_contract_eol(customer_id: int):
    customers_qs = _general_customers_queryset_filter(customer_id=customer_id)
    contracts = CustomerContractModel.objects.select_related('customer').filter(
        customer__in=customers_qs,
        customer_id=customer_id
    )
    data, fname = export_contract(contracts=contracts, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_CONTRACT)


def export_individual_customer_eol(customer_id: int):
    customers = _general_customers_queryset_filter(customer_id=customer_id)
    data, fname = export_individual_customer(customers_queryset=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_INDIVIDUAL)


def export_customer_contact_eol(customer_id: int):
    now =datetime.now()
    customers_qs = _general_customers_queryset_filter(
        customer_id=customer_id
    ).only("pk", "telephone", "username", "fio", "create_date")
    customer_tels = [
        {
            "customer_id": c.pk,
            "contact": f"{c.get_full_name()} {c.telephone}",
            "actual_start_time": datetime(c.create_date.year, c.create_date.month, c.create_date.day),
            'actual_end_time': now
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
            'actual_end_time': now
        }
        for t in tels.iterator()
    )

    data, fname = export_contact(customer_tels=customer_tels, event_time=datetime.now())

    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_CONTACT)

def customer_export_eol(customer_id: int):
    funcs = (
        export_root_customer_eol,
        export_customer_contract_eol,
        export_individual_customer_eol,
        export_customer_contact_eol
    )
    for fn in funcs:
        fn(customer_id=customer_id)


@task()
def customer_export_eol_task(customer_id: int):
    customer_export_eol(customer_id=customer_id)

