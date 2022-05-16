import os
from datetime import datetime
from typing import Any

import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.exceptions import ValidationError

from djing2.lib.logger import logger
from addresses.models import AddressModel, AddressModelTypes
from customers.models import CustomerService, AdditionalTelephone
from customers_legal.models import CustomerLegalModel
from devices.device_config.device_type_collection import DEVICE_TYPES
from devices.device_config.switch.switch_device_strategy import SwitchDeviceStrategy
from services.models import Service
from devices.models import Device
from networks.models import CustomerIpLeaseModel, NetworkIpPool
from customer_contract.models import CustomerContractModel
from sorm_export.hier_export.addresses import (
    export_address_object, get_remote_export_filename
)
from sorm_export.hier_export.customer import (
    export_access_point_address,
    export_individual_customers_queryset,
    export_legal_customer,
    export_contact,
    general_customer_filter_queryset,
    CustomerRootExportTree,
    CustomerContractExportTree
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


def export_all_root_customers():
    customers = general_customer_filter_queryset()
    exporter = CustomerRootExportTree(recursive=False)
    data = exporter.export(queryset=customers)
    exporter.upload2ftp(data=data, export_type=ExportStampTypeEnum.CUSTOMER_ROOT)


def export_all_customer_contracts():
    contracts = CustomerContractModel.objects.select_related('customer').filter(
        customer__is_active=True
    )
    exporter = CustomerContractExportTree(recursive=False)
    data = exporter.export(queryset=contracts)
    exporter.upload2ftp(data=data, export_type=ExportStampTypeEnum.CUSTOMER_CONTRACT)


def export_all_address_objects():
    addr_objects = AddressModel.objects.filter(
        address_type__in=[
            AddressModelTypes.STREET,
            AddressModelTypes.LOCALITY,
            AddressModelTypes.OTHER,
        ],
    ).order_by(
        "fias_address_level",
        "fias_address_type"
    )
    et = datetime.now()
    fname = get_remote_export_filename(event_time=et)

    def _make_exportable_object(addr_object):
        try:
            dat, _ = export_address_object(fias_addr=addr_object, event_time=et)
            if not dat:
                return
            return dat
        except ExportFailedStatus as err:
            logger.error(str(err))

    data = (_make_exportable_object(a) for a in addr_objects.iterator())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ADDRESS)


def export_all_access_point_addresses():
    customers = general_customer_filter_queryset()
    data, fname = export_access_point_address(customers=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_AP_ADDRESS)


def export_all_individual_customers():
    customers = general_customer_filter_queryset()
    data, fname = export_individual_customers_queryset(customers_queryset=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_INDIVIDUAL)


def export_all_legal_customers():
    customers = CustomerLegalModel.objects.all()
    data, fname = export_legal_customer(legal_customers=customers, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_LEGAL)


def export_all_customer_contacts():
    customers = general_customer_filter_queryset().only("pk", "telephone", "username", "fio", "create_date")
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
    tels = AdditionalTelephone.objects.filter(customer__in=customers).select_related("customer")
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
    customers_qs = general_customer_filter_queryset()
    leases = CustomerIpLeaseModel.objects.filter(
        customer__in=customers_qs,
        is_dynamic=False
    )
    data, fname = export_ip_leases(leases=leases, event_time=datetime.now())
    task_export(data, fname, ExportStampTypeEnum.NETWORK_STATIC_IP)


def export_all_customer_services():
    customers_qs = general_customer_filter_queryset()
    csrv = CustomerService.objects.select_related("customer").filter(
        customer__in=customers_qs
    )
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
            (export_all_root_customers, "Customers root export"),
            (export_customer_lease_binds, "Customer lease binds"),
            (export_all_address_objects, "Address objects export"),
            (export_all_customer_contracts, "Customer contracts export"),
            (export_all_access_point_addresses, 'Customer ap export'),
            (export_all_individual_customers, "Customer individual export"),
            (export_all_legal_customers, 'Customer legal export'),
            (export_all_customer_contacts, "Customer contacts export"),
            (export_all_ip_leases, "Network static leases export"),
            (export_all_service_nomenclature, "Services export status"),
            (export_all_customer_services, "Customer services export status"),
            (export_special_numbers, "Special numbers export status"),
            (export_all_switches, "Switches export status"),
            (export_all_ip_numbering, "Ip numbering export status"),
            (export_all_gateways, "Gateways export status"),
        )
        fname = f"/tmp/export{datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')}.log"
        export_logger = logging.getLogger('djing2.sorm_logger')
        logging.basicConfig(
            filename=fname,
            filemode='w',
            level=logging.INFO
        )
        export_logger.info("Starting full export")
        for fn, msg in funcs:
            try:
                export_logger.info(msg)
                #self.stdout.write(msg, ending=' ')
                fn()
                #self.stdout.write(self.style.SUCCESS("OK"))
            except (ExportFailedStatus, FileNotFoundError) as err:
                export_logger.error(str(err))
                #self.stderr.write(str(err))
            except ValidationError as e:
                export_logger.error(str(e.detail))
                #self.stderr.write(str(e.detail))
        export_logger.info("Finished full export")
        sorm_reporting_emails = getattr(settings, 'SORM_REPORTING_EMAILS', None)
        if not sorm_reporting_emails:
            return
        with open(fname, 'r') as f:
            content = f.read()
            if 'ERROR' in content:
                send_mail(
                    'Отчёт выгрузки',
                    content,
                    getattr(settings, 'DEFAULT_FROM_EMAIL'),
                    sorm_reporting_emails
                )
        os.remove(fname)
