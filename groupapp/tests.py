from rest_framework import status

from customers.tests.customer import CustomAPITestCase
from devices.device_config import DEVICE_TYPE_DlinkDGS1100_10ME, DEVICE_TYPE_OnuZTE_F601
from devices.models import Device


# Test recursive permission assignment
class GroupAppTestCase(CustomAPITestCase):

    def setUp(self):
        super().setUp()

        self.device_switch = Device.objects.create(
            ip_address='192.168.2.3',
            mac_addr='12:13:14:15:16:17',
            comment='test',
            dev_type=DEVICE_TYPE_DlinkDGS1100_10ME,
            group=self.group
        )
        self.device_onu = Device.objects.create(
            mac_addr='11:13:14:15:16:18',
            comment='test2',
            dev_type=DEVICE_TYPE_OnuZTE_F601,
            group=self.group
        )

    def test_get_perms(self):
        r = self.get('/api/groups/get_all_related_perms/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        codes = ['add_customer', 'can_add_balance', 'can_buy_service', 'can_ping', 'change_customer', 'delete_customer',
                 'view_customer', 'add_customerstreet', 'change_customerstreet', 'delete_customerstreet',
                 'view_customerstreet', 'add_device', 'can_apply_onu_config', 'can_fix_onu', 'can_remove_from_olt',
                 'change_device', 'delete_device', 'view_device', 'add_networkippool', 'change_networkippool',
                 'delete_networkippool', 'view_networkippool', 'add_userprofile', 'change_userprofile',
                 'delete_userprofile', 'view_userprofile', 'add_service', 'change_service', 'delete_service',
                 'view_service']

        for perm in r.data:
            self.assertIn(perm.get('codename'), codes)
