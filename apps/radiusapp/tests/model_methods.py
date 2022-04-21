from rest_framework.test import APITestCase

from devices.device_config.switch.dlink.dgs_1100_10me import DEVICE_UNIQUE_CODE as Dlink_dgs1100_10me_code
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from radiusapp.models import CustomerRadiusSession
from ._create_full_customer import create_full_customer


class CreateLeaseWAutoPoolNSessionTestCase(APITestCase):
    def setUp(self):
        self.full_customer = create_full_customer(
            uname='custo1',
            tel='+797811234567',
            initial_balance=11,
            dev_ip="192.168.2.3",
            dev_mac="12:13:14:15:16:17",
            dev_type=Dlink_dgs1100_10me_code,
            service_title='test',
            service_descr='test',
            service_speed_in=11.0,
            service_speed_out=11.0,
            service_cost=10.0,
            service_calc_type=SERVICE_CHOICE_DEFAULT
        )

    def test_create_lease_w_auto_pool_n_session(self):
        is_created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
            ip='',
            mac='',
            customer_id=0,
            radius_uname='',
            radius_unique_id=''
        )

