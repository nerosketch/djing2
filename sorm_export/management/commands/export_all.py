from datetime import datetime
from typing import Any
from django.core.management.base import BaseCommand

from customers.models import Customer, CustomerService
from services.models import Service
from sorm_export.hier_export.customer import (
    export_customer_root, export_contract,
    export_address, export_access_point_address,
    export_individual_customer, export_legal_customer,
    export_contact
)
from sorm_export.hier_export.networks import export_ip_leases
from sorm_export.hier_export.service import (
    export_nomenclature, export_customer_service
)
from sorm_export.models import ExportStampTypeEnum
from sorm_export.tasks.task_export import task_export

from networks.models import CustomerIpLeaseModel


def export_all_root_customers():
    customers = Customer.objects.all()
    data, fname = export_customer_root(
        customers=customers,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ROOT)


def export_all_customer_contracts():
    customers = Customer.objects.all()
    data, fname = export_contract(
        customers=customers,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_CONTRACT)


def export_all_customer_addresses():
    customers = Customer.objects.all()
    data, fname = export_address(
        customers=customers,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ADDRESS)


def export_all_access_point_addresses():
    customers = Customer.objects.all()
    data, fname = export_access_point_address(
        customers=customers,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_AP_ADDRESS)


def export_all_individual_customers():
    customers = Customer.objects.all()
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
    customers = Customer.objects.all()
    data, fname = export_contact(
        customers=customers,
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
    )
    data, fname = export_ip_leases(
        leases=leases,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.NETWORK_STATIC_IP)


def export_all_customer_services():
    csrv = CustomerService.objects.all()
    data, fname = export_customer_service(
        cservices=csrv,
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.SERVICE_CUSTOMER)


class Command(BaseCommand):
    help = 'Exports all available data to sorm'

    def handle(self, *args: Any, **options: Any):
        export_all_root_customers()
        self.stdout.write('Customers root export ' + self.style.SUCCESS('OK'))
        export_all_customer_contracts()
        self.stdout.write('Customer contracts export ' + self.style.SUCCESS('OK'))
        export_all_customer_addresses()
        self.stdout.write('Customer addresses export ' + self.style.SUCCESS('OK'))
        export_all_access_point_addresses()
        self.stdout.write('Customer ap export ' + self.style.SUCCESS('OK'))
        export_all_individual_customers()
        self.stdout.write('Customer individual export ' + self.style.SUCCESS('OK'))
        export_all_legal_customers()
        self.stdout.write('Customer legal export ' + self.style.SUCCESS('OK'))
        export_all_customer_contacts()
        self.stdout.write('Customer contacts export ' + self.style.SUCCESS('OK'))
        export_all_ip_leases()
        self.stdout.write('Network static leases export ' + self.style.SUCCESS('OK'))
        export_all_service_nomenclature()
        self.stdout.write('Services export status ' + self.style.SUCCESS('OK'))
        export_all_customer_services()
        self.stdout.write('Customer services export status ' + self.style.SUCCESS('OK'))
