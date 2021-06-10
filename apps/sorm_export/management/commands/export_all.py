from datetime import datetime
from typing import Any
from django.core.management.base import BaseCommand

from customers.models import (
    Customer, CustomerService,
    AdditionalTelephone
)
from services.models import Service
from sorm_export.hier_export.customer import (
    export_customer_root, export_contract,
    export_address_object, export_access_point_address,
    export_individual_customer, export_legal_customer,
    export_contact
)
from sorm_export.hier_export.networks import export_ip_leases
from sorm_export.hier_export.service import (
    export_nomenclature, export_customer_service
)
from sorm_export.models import ExportStampTypeEnum, ExportFailedStatus, FiasRecursiveAddressModel
from sorm_export.tasks.task_export import task_export

from networks.models import CustomerIpLeaseModel


def export_all_root_customers():
    customers = Customer.objects.filter()
    data, fname = export_customer_root(
        customers=customers,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ROOT)


def export_all_customer_contracts():
    customers = Customer.objects.filter()
    data, fname = export_contract(
        customers=customers,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_CONTRACT)


def export_all_address_objects():
    # TODO: filter recursive
    addr_objects = FiasRecursiveAddressModel.objects.order_by('ao_level')
    et = datetime.now()
    data = []
    fname = None
    for addr_object in addr_objects.iterator():
        try:
            dat, fname = export_address_object(
                addr_obj=addr_object,
                event_time=et
            )

            data.extend(dat)
        except ExportFailedStatus as err:
            print('ERROR:', err)
    if fname is not None and len(data) > 0:
        task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ADDRESS)


def export_all_access_point_addresses():
    customers = Customer.objects.all()
    data, fname = export_access_point_address(
        customers=customers,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_AP_ADDRESS)


def export_all_individual_customers():
    customers = Customer.objects.select_related('passportinfo')
    data, fname = export_individual_customer(
        customers=customers,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_INDIVIDUAL)


def export_all_legal_customers():
    customers = Customer.objects.all()
    data, fname = export_legal_customer(
        customers=customers,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_LEGAL)


def export_all_customer_contacts():
    customers = Customer.objects.all().only('pk', 'telephone', 'username', 'fio')
    customer_tels = [{
        'customer_id': c.pk,
        'contact': '%s %s' % (c.get_full_name(), c.telephone),
        'actual_start_time': datetime(c.create_date.year, c.create_date.month, c.create_date.day),
        # 'actual_end_time':
    } for c in customers.iterator()]

    # export additional tels
    tels = AdditionalTelephone.objects.select_related('customer')
    customer_tels.extend({
        'customer_id': t.customer_id,
        'contact': '%s %s' % (t.customer.get_full_name(), t.telephone),
        'actual_start_time': t.create_time,
        # 'actual_end_time':
    } for t in tels.iterator())

    data, fname = export_contact(
        customer_tels=customer_tels,
        event_time=datetime.now()
    )

    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_CONTACT)


# FIXME: ??? Можно-ли выгружать
def export_all_customer_unknown_payments():
    pass


def export_all_service_nomenclature():
    services = Service.objects.all()
    data, fname = export_nomenclature(
        services=services,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.SERVICE_NOMENCLATURE)


def export_all_ip_leases():
    leases = CustomerIpLeaseModel.objects.filter(
        is_dynamic=False
    ).exclude(customer=None)
    data, fname = export_ip_leases(
        leases=leases,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.NETWORK_STATIC_IP)


def export_all_customer_services():
    csrv = CustomerService.objects.select_related('customer')
    data, fname = export_customer_service(
        cservices=csrv,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.SERVICE_CUSTOMER)


class Command(BaseCommand):
    help = 'Exports all available data to sorm'

    def handle(self, *args: Any, **options: Any):
        funcs = (
            (export_all_address_objects, 'Address objects export'),
            # (export_all_root_customers, 'Customers root export'),
            # (export_all_customer_contracts, 'Customer contracts export'),
            # (export_all_access_point_addresses, 'Customer ap export'),
            # (export_all_individual_customers, 'Customer individual export'),
            #(export_all_legal_customers, 'Customer legal export'),
            # (export_all_customer_contacts, 'Customer contacts export'),
            # (export_all_ip_leases, 'Network static leases export'),
            # (export_all_service_nomenclature, 'Services export status'),
            #(export_all_customer_services, 'Customer services export status')
        )
        for fn, msg in funcs:
            try:
                fn()
                self.stdout.write(msg + ' ' + self.style.SUCCESS('OK'))
            except ExportFailedStatus as err:
                self.stdout.write(('%s: %s %s' % (msg, err, self.style.ERROR('FAILED'))))
