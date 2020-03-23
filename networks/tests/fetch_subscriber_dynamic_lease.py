from django.test import TestCase

from customers.tests import CustomAPITestCase
from networks.models import CustomerIpLeaseModel


class BaseCustomerIpLeaseModelTestCase(TestCase):
    def setUp(self):
        # Initialize customers instances
        CustomAPITestCase.setUp(self)


class FetchSubscriberDynamicLeaseTestCase(BaseCustomerIpLeaseModelTestCase):
    def test_is_ok(self):
        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            self.customer.pk, '1:2:3:4:5:6'
        )
        # TODO: Make real tests
        # self.assertIsNotNone(lease)
