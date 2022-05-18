import os
from datetime import datetime
from typing import Any

import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.exceptions import ValidationError

from addresses.models import AddressModel, AddressModelTypes
from customers.models import CustomerService, AdditionalTelephone
from customers_legal.models import CustomerLegalModel
from devices.device_config.device_type_collection import DEVICE_TYPES
from devices.device_config.switch.switch_device_strategy import SwitchDeviceStrategy
from devices.models import Device
from networks.models import CustomerIpLeaseModel, NetworkIpPool
from customer_contract.models import CustomerContractModel
from sorm_export.hier_export.addresses import AddressExportTree
from sorm_export.hier_export.customer import (
    general_customer_filter_queryset,
    CustomerRootExportTree,
    CustomerContractExportTree,
    AccessPointExportTree,
    IndividualCustomersExportTree,
    LegalCustomerExportTree,
    ContactSimpleExportTree
)

from sorm_export.hier_export.networks import IpLeaseExportTree
from sorm_export.hier_export.service import NomenclatureSimpleExportTree, CustomerServiceExportTree
from sorm_export.hier_export.special_numbers import export_special_numbers
from sorm_export.hier_export.devices import DeviceExportTree
from sorm_export.hier_export.ip_numbering import IpNumberingExportTree
from sorm_export.hier_export.gateways import GatewayExportTree
from sorm_export.management.commands._general_func import export_customer_lease_binds
from sorm_export.models import ExportFailedStatus


def export_all_root_customers():
    customers = general_customer_filter_queryset()
    CustomerRootExportTree(recursive=False).exportNupload(queryset=customers)


def export_all_customer_contracts():
    contracts = CustomerContractModel.objects.select_related('customer').filter(
        customer__is_active=True
    )
    CustomerContractExportTree(recursive=False).exportNupload(queryset=contracts)


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

    AddressExportTree(event_time=et, recursive=False).exportNupload(queryset=addr_objects)


def export_all_access_point_addresses():
    customers = general_customer_filter_queryset()
    AccessPointExportTree(recursive=False).exportNupload(queryset=customers)


def export_all_individual_customers():
    customers = general_customer_filter_queryset()
    IndividualCustomersExportTree(recursive=False).exportNupload(queryset=customers)


def export_all_legal_customers():
    customers = CustomerLegalModel.objects.all()
    LegalCustomerExportTree(recursive=False).exportNupload(queryset=customers)


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

    ContactSimpleExportTree(recursive=False).exportNupload(data=customer_tels, many=True)


def export_all_service_nomenclature():
    NomenclatureSimpleExportTree(recursive=False).exportNupload()


def export_all_ip_leases():
    customers_qs = general_customer_filter_queryset()
    leases = CustomerIpLeaseModel.objects.filter(
        customer__in=customers_qs,
        is_dynamic=False
    )
    IpLeaseExportTree(recursive=False).exportNupload(queryset=leases)


def export_all_customer_services():
    customers_qs = general_customer_filter_queryset()
    csrv = CustomerService.objects.select_related("customer").filter(
        customer__in=customers_qs
    )
    CustomerServiceExportTree(recursive=False).exportNupload(queryset=csrv)


def export_all_switches():
    device_switch_type_ids = [uniq_num for uniq_num, dev_klass in DEVICE_TYPES if issubclass(
        dev_klass, SwitchDeviceStrategy)]
    devs = Device.objects.filter(dev_type__in=device_switch_type_ids).exclude(address=None).select_related('address')
    if devs.exists():
        DeviceExportTree(recursive=True).exportNupload(queryset=devs)


def export_all_ip_numbering():
    IpNumberingExportTree(recursive=False).exportNupload(queryset=NetworkIpPool.objects.all())


def export_all_gateways():
    from gateways.models import Gateway
    GatewayExportTree(recursive=True).exportNupload(queryset=Gateway.objects.exclude(place=None))


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
            except ExportFailedStatus as err:
                export_logger.error(str(err))
                self.stderr.write(str(err))
            except ValidationError as e:
                export_logger.error(str(e.detail))
                self.stderr.write(str(e.detail))
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
