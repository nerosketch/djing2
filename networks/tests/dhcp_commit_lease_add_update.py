from collections import OrderedDict

from django.test.utils import override_settings

from customers.models import Customer
from customers.tests.customer import CustomAPITestCase
from djing2.lib import calc_hash
from networks.models import NetworkIpPool, NetworkIpPoolKind
from customers.tests.get_user_credentials_by_ip import BaseServiceTestCase


class DhcpCommitLeaseAddUpdateTestCase(CustomAPITestCase):
    def setUp(self):
        # Initialize customers instances
        BaseServiceTestCase.setUp(self)

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, 10000, 'test')
        self.customer.save()
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

        # customer for tests
        custo2 = Customer.objects.create_user(
            telephone='+79782345679',
            username='custo2',
            password='passw',
            group=self.group,
            device=self.device_onu
        )
        custo2.refresh_from_db()
        self.customer2 = custo2

        self.ippool = NetworkIpPool.objects.create(
            network='10.11.12.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            description='test',
            ip_start='10.11.12.2',
            ip_end='10.11.12.254',
            # vlan_if=vlan,
            gateway='10.11.12.1',
            is_dynamic=True
        )
        self.ippool.groups.add(self.group)

    def _make_dhcp_event_request(self, client_ip: str, client_mac: str, switch_mac: str,
                                 switch_port: int, cmd: str, status_code: int = 200):
        request_data = OrderedDict({
            'client_ip': client_ip,
            'client_mac': client_mac,
            'switch_mac': switch_mac,
            'switch_port': str(switch_port),
            'cmd': cmd
        })
        hdrs = {
            'Api-Auth-Sign': calc_hash(request_data),
            'content_type': 'application/json'
        }
        r = self.client.get('/api/networks/dhcp_lever/', data=request_data, **hdrs)
        self.assertEqual(r.status_code, status_code)

    @override_settings(API_AUTH_SECRET="sdfsdf")
    def test_ok(self):
        self._make_dhcp_event_request('10.11.12.55', '12:13:14:15:16:15', '12:13:14:15:16:17', 2, 'commit')
