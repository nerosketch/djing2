from rest_framework import status
from rest_framework.test import APITestCase

from profiles.models import UserProfile


class ProfileApiTestCase(APITestCase):
    def get(self, *args, **kwargs):
        return self.client.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client.post(*args, **kwargs)

    def setUp(self):
        self.admin = UserProfile.objects.create_superuser(
            username='admin',
            password='admin',
            telephone='+797812345678'
        )
        self.client.login(
            username='admin',
            password='admin'
        )

    def test_create_superuser(self):
        r = self.post('/api/profiles/', {
            'username': 'test',
            'fio': 'test fio',
            'is_active': True,
            'telephone': '+79781234567',
            'email': 'test@mail.ex'
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        profile = r.data
        self.assertEqual(profile['username'], 'test')
        self.assertEqual(profile['fio'], 'test fio')
        self.assertEqual(profile['telephone'], '+79781234567')
        self.assertEqual(profile['email'], 'test@mail.ex')
        self.assertTrue(profile['is_active'])
        self.assertTrue(profile['is_admin'])
        self.assertTrue(profile['is_superuser'])
