import json

from rest_framework import status

from customers.tests import TestRadiusCustomerServiceRequestViewSet
from gateways.gw_facade import MIKROTIK
from .models import Gateway


class FetchCredentialsTestCase(TestRadiusCustomerServiceRequestViewSet):
    def setUp(self):
        super().setUp()

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
