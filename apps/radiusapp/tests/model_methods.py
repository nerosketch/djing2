from rest_framework.test import APITestCase

from radiusapp.models import CustomerRadiusSession


class MyTestCase(APITestCase):
    def test_create_lease_w_auto_pool_n_session(self):
        pass
        #is_created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
        #    ip='',
        #    mac='',
        #    customer_id=0,
        #    radius_uname='',
        #    radius_unique_id=''
        #)
