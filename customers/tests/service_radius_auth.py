from django.test import override_settings

from devices.tests import DeviceTestCase
from networks.models import CustomerIpLeaseModel, NetworkIpPool
from services.models import Service, SERVICE_CHOICE_DEFAULT
from .customer import CustomAPITestCase


@override_settings(RADIUS_SESSION_TIME=3600)
class TestRadiusCustomerServiceRequestViewSet(CustomAPITestCase):
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
            kind=NetworkIpPool.NETWORK_KIND_INTERNET,
            description='test',
            ip_start='10.11.12.2',
            ip_end='10.11.12.254',
            # vlan_if=vlan,
            gateway='10.11.12.1'
        )
        self.ippool.groups.add(self.group)
        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, 10000, 'test')
        self.customer.save()
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

        self.lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(self.lease)
        # lease must be contain ip_address=10.11.12.2'
        self.customer_lease_ip = '10.11.12.2'

    def _make_request(self):
        return self.post(path='/api/customers/radius/get_service/', data={
            'username': self.customer_lease_ip,
            'password': 'blabla_doesntmatter'
        })

    def test_auth_customer_service(self):
        r = self._make_request()
        self.assertEqual(r.status_code, 200)
        self.assertDictEqual(r.data, {
            "control:Auth-Type": 'Accept',
            "User-Name": self.customer_lease_ip,
            "Session-Timeout": 3600,
            "Idle-Timeout": 3600,
            "Cisco-AVPair": (
                'subscriber:policer-rate-in=%d' % 10 * 1024,
                'subscriber:policer-rate-out=%d' % 10 * 1024,
                'subscriber:policer-burst-in=188',
                'subscriber:policer-burst-out=188',
            ),
            "Cisco-Account-Info": 'AINTERNET'
        })

    def test_if_customer_not_have_service(self):
        self.customer.stop_service(self.customer)
        r = self._make_request()
        self.assertEqual(r.status_code, 404)

    def test_customer_disabled(self):
        self.customer.is_active = False
        self.customer.save(update_fields=['is_active'])
        r = self._make_request()
        self.assertEqual(r.status_code, 404)
