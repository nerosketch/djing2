from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from rest_framework.test import APITestCase
from customers import models


UserProfile = get_user_model()


class CustomAPITestCase(APITestCase):
    def get(self, *args, **kwargs):
        return self.client.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client.post(*args, **kwargs)

    def setUp(self):
        UserProfile.objects.create_superuser(
            username='admin',
            password='admin',
            telephone='+797812345678'
        )
        self.client.login(
            username='admin',
            password='admin'
        )


class CustomerServiceTestCase(CustomAPITestCase):
    def test_direct_create(self):
        r = self.post('/api/customers/customer-service/')
        self.assertEqual(r.data, _("Not allowed to direct create Customer service, use 'pick_service' url"))
        self.assertEqual(r.status_code, 403)


class CustomerLogAPITestCase(CustomAPITestCase):
    def test_direct_create(self):
        r = self.post('/api/customers/customer-log/')
        self.assertEqual(r.data, _("Not allowed to direct create Customer log"))
        self.assertEqual(r.status_code, 403)


class CustomerModelAPITestCase(CustomAPITestCase):
    def test_get_random_username(self):
        r = self.get('/api/customers/generate_random_username/')
        random_unique_uname = r.data
        qs = models.Customer.objects.filter(username=random_unique_uname)
        self.assertFalse(qs.exists())
