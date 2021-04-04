# from django.contrib.auth.models import Group as ProfileGroup, Permission
# from rest_framework import status
#
# from customers.tests.customer import CustomAPITestCase
#
#
# # Test recursive permission assignment
# class GroupAppTestCase(CustomAPITestCase):
#
#     def setUp(self):
#         super().setUp()
#
#         self.profile_group = ProfileGroup.objects.create(
#             name='Test profile group'
#         )
#
#     def test_get_perms(self):
#         r = self.get('/api/groups/get_all_related_perms/')
#         self.assertEqual(r.status_code, status.HTTP_200_OK)
#
#         codes = ['add_customer', 'can_add_balance', 'can_buy_service', 'can_ping',
#                  'change_customer', 'delete_customer', 'view_customer',
#                  'add_customerstreet', 'change_customerstreet', 'delete_customerstreet',
#                  'view_customerstreet', 'add_device', 'can_apply_onu_config',
#                  'can_fix_onu', 'can_remove_from_olt', 'change_device',
#                  'delete_device', 'view_device', 'add_networkippool', 'change_networkippool',
#                  'delete_networkippool', 'view_networkippool', 'add_userprofile',
#                  'change_userprofile', 'delete_userprofile', 'view_userprofile',
#                  'add_service', 'change_service', 'delete_service', 'view_service']
#
#         for perm in r.data:
#             self.assertIn(perm.get('codename'), codes)
#
#     def test_set_related_perms(self):
#         read_perms = Permission.objects.filter(codename__startswith='view_')
#         read_perm_ids = [p.pk for p in read_perms]
#         r = self.client.put('/api/groups/%d/set_related_perms_recursive/' % self.group.pk, {
#             'profile_group': self.profile_group.pk,
#             'permission_ids': read_perm_ids
#         })
#         self.assertEqual(r.status_code, status.HTTP_200_OK)
#
#     def test_set_related_perms_bad_profile_group(self):
#         r = self.client.put('/api/groups/%d/set_related_perms_recursive/' % self.group.pk, {
#             'profile_group': 0,
#             'permission_ids': [1, 2, 3]
#         })
#         self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
#
#     def test_set_related_perms_bad_neg_profile_group(self):
#         r = self.client.put('/api/groups/%d/set_related_perms_recursive/' % self.group.pk, {
#             'profile_group': -1,
#             'permission_ids': [1, 2, 3]
#         })
#         self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
#
#     def test_set_related_perms_bad_permissions(self):
#         r = self.client.put('/api/groups/%d/set_related_perms_recursive/' % self.group.pk, {
#             'profile_group': self.profile_group.pk,
#             'permission_ids': [1000, 2000, 3000]
#         })
#         self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
#
#     def test_set_related_perms_bad_text_permissions(self):
#         r = self.client.put('/api/groups/%d/set_related_perms_recursive/' % self.group.pk, {
#             'profile_group': self.profile_group.pk,
#             'permission_ids': ['sdfsdf', 'yj', 'sdfdf']
#         })
#         self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
