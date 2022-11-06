from decimal import Decimal

from devices.tests import device_test_case_set_up
from networks.models import CustomerIpLeaseModel, NetworkIpPool, NetworkIpPoolKind
from services.models import Service
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from .customer import CustomAPITestCase


class BaseServiceTestCase(CustomAPITestCase):
    service: Service

    def setUp(self):
        # Initialize customers instances
        super().setUp()

        # Initialize devices instances
        device_test_case_set_up(self)

        self.service = Service.objects.create(
            title="test",
            descr="test",
            speed_in=10.0,
            speed_out=10.0,
            cost=10.0,
            calc_type=SERVICE_CHOICE_DEFAULT
        )


class GetUserCredentialsByIpTestCase(BaseServiceTestCase):
    def setUp(self):
        super().setUp()
        self.ippool = NetworkIpPool.objects.create(
            network="10.11.12.0/24",
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET.value,
            description="test",
            ip_start="10.11.12.2",
            ip_end="10.11.12.254",
            # vlan_if=vlan,
            gateway="10.11.12.1",
            is_dynamic=True,
        )
        self.ippool.groups.add(self.group)

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, Decimal(10000), "test")
        self.customer.save()
        self.customer.refresh_from_db()
        self.service.pick_service(
            customer=self.customer,
            author=self.customer
        )

        self.lease = CustomerIpLeaseModel.objects.filter(
            ip_address="10.11.12.2",
        ).update(
            mac_address="1:2:3:4:5:6",
            pool=self.ippool,
            customer=self.customer,
            is_dynamic=True,
        )
        self.assertIsNotNone(self.lease)
        # lease must be contain ip_address=10.11.12.2'
