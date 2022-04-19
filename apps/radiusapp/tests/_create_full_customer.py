from typing import Optional
from dataclasses import dataclass
from django.contrib.sites.models import Site
from customers.models import Customer
from devices.models import Device, Port
from groupapp.models import Group
from services.models import Service
from services.custom_logic import SERVICE_CHOICE_DEFAULT


@dataclass
class CreateFullCustomerReturnType:
    group: Group
    customer: Customer
    device: Device
    service: Service
    site: Optional[Site]


def create_full_customer(uname: str,
                         tel: str,
                         dev_type: int,
                         dev_mac: Optional[str] = None,
                         dev_ip: Optional[str] = None,
                         group_title: Optional[str] = None,
                         service_title: Optional[str] = None,
                         service_descr: Optional[str] = None,
                         service_speed_in=11.0,
                         service_speed_out=11.0,
                         service_cost=10,
                         service_calc_type=SERVICE_CHOICE_DEFAULT,
                         initial_balance=0,
                         dev_comment: Optional[str] = None) -> CreateFullCustomerReturnType:
    if group_title is None:
        group_title = 'test_group'

    group, _ = Group.objects.get_or_create(title=group_title, code="tst")

    if dev_mac is None:
        dev_mac = "11:13:14:15:17:17"

    if dev_comment is None:
        dev_comment = 'device for tests'

    # Other device for other customer
    device, _ = Device.objects.get_or_create(
        mac_addr=dev_mac, comment=dev_comment,
        dev_type=dev_type, ip_address=dev_ip,
    )
    ports = tuple(Port(device=device, num=n, descr="test %d" % n) for n in range(1, 3))
    ports = Port.objects.bulk_create(ports)

    customer = Customer.objects.create_user(
        telephone=tel, username=uname, password="passw",
        is_dynamic_ip=True, group=group,
        balance=initial_balance, device=device,
        dev_port=ports[1]
    )

    example_site = Site.objects.first()
    if example_site:
        customer.sites.add(example_site)
    customer.refresh_from_db()

    if service_title is None:
        service_title = 'test service'
    if service_descr is None:
        service_descr = 'test service description'
    # Create service for customer
    service, service_is_created = Service.objects.get_or_create(
        title=service_title, descr=service_descr,
        speed_in=service_speed_in,
        speed_out=service_speed_out,
        cost=service_cost,
        calc_type=service_calc_type
    )
    customer.pick_service(service, customer)
    return CreateFullCustomerReturnType(
        group=group,
        customer=customer,
        site=example_site,
        device=device,
        service=service
    )

