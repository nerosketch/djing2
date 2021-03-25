import json

from rest_framework import status

from customers.tests.customer import CustomAPITestCase
from devices.tests import DeviceTestCase
from gateways.gw_facade import MIKROTIK
from networks.models import NetworkIpPool, NetworkIpPoolKind, CustomerIpLeaseModel
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from services.models import Service
from .models import Gateway


class FetchCredentialsTestCase(CustomAPITestCase):
    def setUp(self):
        super().setUp()

        # Initialize devices instances
        DeviceTestCase.setUp(self)

        self.service = Service.objects.create(
            title='test',
            descr='test',
            speed_in=10.0,
            speed_out=10.0,
            cost=10.0,
            calc_type=SERVICE_CHOICE_DEFAULT
        )
        self.ippool = NetworkIpPool.objects.create(
            network='10.11.12.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET.value,
            description='test',
            ip_start='10.11.12.2',
            ip_end='10.11.12.254',
            # vlan_if=vlan,
            gateway='10.11.12.1',
            is_dynamic=True
        )
        self.ippool.groups.add(self.group)
        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, 10000, 'test')
        self.customer.save()
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

        self.lease = CustomerIpLeaseModel.objects.create(
            ip_address='10.11.12.2',
            mac_address='1:2:3:4:5:6',
            pool=self.ippool,
            customer=self.customer,
            is_dynamic=True
        )

        self.assertIsNotNone(self.lease)
        # lease must be contain ip_address=10.11.12.2'
        self.customer_lease_ip = '10.11.12.2'

        gw = Gateway.objects.create(
            title='test gw',
            ip_address='192.168.0.100',
            ip_port=11852,
            auth_login='test',
            auth_passw='test',
            gw_type=MIKROTIK
        )
        self.gw = gw

        self.customer.gateway = gw
        self.customer.save(update_fields=['gateway'])

    def test_get_credentials(self):
        r = self.get('/api/gateways/fetch_customers_srvnet_credentials_by_gw/', {
            'gw_id': self.gw.pk
        })

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        data = json.loads(r.content)
        (customer_id, lease_id, lease_time, lease_mac, ip_address,
         speed_in, speed_out, speed_burst, service_start_time,
         service_deadline) = data[0]
        self.assertEqual(ip_address, '10.11.12.2')
        self.assertEqual(lease_mac, '01:02:03:04:05:06')
        self.assertEqual(speed_in, 10)
        self.assertEqual(speed_out, 10)
        self.assertEqual(speed_burst, 1)
