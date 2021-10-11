from datetime import datetime
from typing import Any

import logging
from django.core.management.base import BaseCommand

from addresses.models import AddressModel
from customers.models import Customer, CustomerService, AdditionalTelephone
from devices.device_config.device_type_collection import DEVICE_TYPES
from devices.device_config.switch.switch_device_strategy import SwitchDeviceStrategy
from services.models import Service
from devices.models import Device
from sorm_export.hier_export.addresses import (
    export_address_object, get_remote_export_filename
)
from sorm_export.hier_export.customer import (
    export_customer_root,
    export_contract,
    export_access_point_address,
    export_individual_customer,
    export_legal_customer,
    export_contact,
)

from sorm_export.hier_export.networks import export_ip_leases
from sorm_export.hier_export.service import export_nomenclature, export_customer_service
from sorm_export.hier_export.special_numbers import export_special_numbers
from sorm_export.hier_export.devices import export_devices
from sorm_export.hier_export.ip_numbering import export_ip_numbering
from sorm_export.hier_export.gateways import export_gateways
from sorm_export.management.commands._general_func import export_customer_lease_binds
from sorm_export.models import ExportStampTypeEnum, ExportFailedStatus
from sorm_export.tasks.task_export import task_export

from networks.models import CustomerIpLeaseModel, NetworkIpPool


def export_all_root_customers():
    customers = Customer.objects.all()
    data, fname = export_customer_root(customers=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ROOT)


def export_all_customer_contracts():
    customers = Customer.objects.filter(is_active=True)
    data, fname = export_contract(customers=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_CONTRACT)


def export_all_address_objects():
    addr_objects = AddressModel.objects.order_by("fias_address_level")
    et = datetime.now()
    fname = get_remote_export_filename(event_time=et)

    def _make_exportable_object(addr_object):
        try:
            dat, _ = export_address_object(fias_addr=addr_object, event_time=et)
            if not dat:
                return
            return dat
        except ExportFailedStatus as err:
            logging.error(str(err))

    data = (_make_exportable_object(a) for a in addr_objects.iterator())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ADDRESS)


def export_all_access_point_addresses():
    customers = Customer.objects.filter(is_active=True)
    data, fname = export_access_point_address(customers=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_AP_ADDRESS)


def export_all_individual_customers():
    customers = Customer.objects.filter(is_active=True)
    data, fname = export_individual_customer(customers_queryset=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_INDIVIDUAL)


def export_all_legal_customers():
    customers = Customer.objects.filter(is_active=True)
    data, fname = export_legal_customer(customers=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_LEGAL)


def export_all_customer_contacts():
    customers = Customer.objects.filter(is_active=True).only("pk", "telephone", "username", "fio", "create_date")
    customer_tels = [
        {
            "customer_id": c.pk,
            "contact": f"{c.get_full_name()} {c.telephone}",
            "actual_start_time": datetime(c.create_date.year, c.create_date.month, c.create_date.day),
            # 'actual_end_time':
        }
        for c in customers.iterator()
    ]

    # export additional tels
    tels = AdditionalTelephone.objects.filter(customer__is_active=True).select_related("customer")
    customer_tels.extend(
        {
            "customer_id": t.customer_id,
            "contact": f"{t.customer.get_full_name()} {t.telephone}",
            "actual_start_time": t.create_time,
            # 'actual_end_time':
        }
        for t in tels.iterator()
    )

    data, fname = export_contact(customer_tels=customer_tels, event_time=datetime.now())

    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_CONTACT)


def export_all_service_nomenclature():
    services = Service.objects.all()
    data, fname = export_nomenclature(services=services, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.SERVICE_NOMENCLATURE)


def export_all_ip_leases():
    leases = CustomerIpLeaseModel.objects.exclude(customer=None).filter(customer__is_active=True, is_dynamic=False)
    data, fname = export_ip_leases(leases=leases, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.NETWORK_STATIC_IP)


def export_all_customer_services():
    csrv = CustomerService.objects.select_related("customer").exclude(customer=None).filter(customer__is_active=True)
    data, fname = export_customer_service(cservices=csrv, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.SERVICE_CUSTOMER)


def export_all_switches():
    device_switch_type_ids = [uniq_num for uniq_num, dev_klass in DEVICE_TYPES if issubclass(
        dev_klass, SwitchDeviceStrategy)]
    devs = Device.objects.filter(dev_type__in=device_switch_type_ids).exclude(address=None).select_related('address')
    if devs.exists():
        data, fname = export_devices(devices=devs, event_time=datetime.now())
        task_export(data, fname, ExportStampTypeEnum.DEVICE_SWITCH)


def export_all_ip_numbering():
    data, fname = export_ip_numbering(
        pools=NetworkIpPool.objects.all(),
        event_time=datetime.now()
    )
    task_export(data, fname, ExportStampTypeEnum.IP_NUMBERING)


def export_all_gateways():
    from gateways.models import Gateway
    data, fname = export_gateways(
        event_time=datetime.now(),
        gateways_qs=Gateway.objects.exclude(place=None),
    )
    task_export(data, fname, ExportStampTypeEnum.GATEWAYS)


class Command(BaseCommand):
    help = "Exports all available data to 'СОРМ'"

    def handle(self, *args: Any, **options: Any):
        funcs = (
            (export_customer_lease_binds, "Customer lease binds"),
            (export_all_address_objects, "Address objects export"),
            (export_all_root_customers, "Customers root export"),
            (export_all_customer_contracts, "Customer contracts export"),
            # (export_all_access_point_addresses, 'Customer ap export'),
            (export_all_individual_customers, "Customer individual export"),
            # (export_all_legal_customers, 'Customer legal export'),
            (export_all_customer_contacts, "Customer contacts export"),
            (export_all_ip_leases, "Network static leases export"),
            (export_all_service_nomenclature, "Services export status"),
            (export_all_customer_services, "Customer services export status"),
            (export_special_numbers, "Special numbers export status"),
            (export_all_switches, "Switches export status"),
            (export_all_ip_numbering, "Ip numbering export status"),
            (export_all_gateways, "Gateways export status"),
        )
        for fn, msg in funcs:
            try:
                self.stdout.write(msg, ending=' ')
                fn()
                self.stdout.write(self.style.SUCCESS("OK"))
            except (ExportFailedStatus, FileNotFoundError) as err:
                self.stdout.write("{} {}".format(err, self.style.ERROR("FAILED")))
