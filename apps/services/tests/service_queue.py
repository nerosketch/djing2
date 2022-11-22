from customers.tests.customer import CustomAPITestCase
from customers.models import Customer
from services.models import CustomerServiceConnectingQueueModel, Service
from .customer_service import create_service


def create_customer_service_queue(customer: Customer, service: Service, num=1):
    return CustomerServiceConnectingQueueModel.objects.bulk_create([
        CustomerServiceConnectingQueueModel(
            customer=customer,
            service=service,
            number_queue=n
        ) for n in range(1, num+1, 1)
    ])


class CustomerServiceQueueTestCase(CustomAPITestCase):
    service_queue: CustomerServiceConnectingQueueModel
    service_queues: list[CustomerServiceConnectingQueueModel]
    service: Service

    def setUp(self) -> None:
        super().setUp()

        srv = create_service(self)
        self.service = srv

        self.service_queues = create_customer_service_queue(
            customer=self.customer,
            service=srv,
            num=5
        )
        self.service_queue = self.service_queues[0]

    def _check_initial_queue(self):
        self.assertEqual(self.service_queues[0].number_queue, 1)
        self.assertEqual(self.service_queues[1].number_queue, 2)
        self.assertEqual(self.service_queues[2].number_queue, 3)
        self.assertEqual(self.service_queues[3].number_queue, 4)
        self.assertEqual(self.service_queues[4].number_queue, 5)

    def _refresh_queue(self):
        for q in self.service_queues:
            q.refresh_from_db()

    def test_assign_num_for_new_queue(self):
        self._check_initial_queue()
        CustomerServiceConnectingQueueModel.objects.all()._assign_num_for_new_queue(
            customer_id=self.customer.pk,
            service_id=self.service,
            num=1
        )
        self._refresh_queue()
        sq = self.service_queues
        self.assertEqual(sq[0].number_queue, 2)
        self.assertEqual(sq[1].number_queue, 3)
        self.assertEqual(sq[2].number_queue, 4)
        self.assertEqual(sq[3].number_queue, 5)
        self.assertEqual(sq[4].number_queue, 6)

    def test_assign_num_for_new_queue_in_center(self):
        self._check_initial_queue()
        CustomerServiceConnectingQueueModel.objects.all()._assign_num_for_new_queue(
            customer_id=self.customer.pk,
            service_id=self.service,
            num=3
        )
        self._refresh_queue()
        sq = self.service_queues
        self.assertEqual(sq[0].number_queue, 1)
        self.assertEqual(sq[1].number_queue, 2)
        self.assertEqual(sq[2].number_queue, 4)
        self.assertEqual(sq[3].number_queue, 5)
        self.assertEqual(sq[4].number_queue, 6)

    def test_filter_first(self):
        f = CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer
        ).filter_first().first()
        self.assertIsNotNone(f)
        self.assertEqual(f.pk, self.service_queue.pk)

    def test_filter_last(self):
        f = CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer
        ).filter_last().first()
        self.assertIsNotNone(f)
        self.assertEqual(f.pk, self.service_queues[4].pk)

    def test_push_front(self):
        CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer
        ).push_front(
            customer_id=self.customer.pk,
            service_id=self.service.pk
        )
        queue = CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer.pk
        ).order_by('number_queue')
        self.assertEqual(queue.count(), 6)
        for i, q in enumerate(queue, 1):
            self.assertEqual(q.number_queue, i)
            self.assertEqual(q.customer_id, self.customer.pk)
            self.assertEqual(q.service_id, self.service.pk)
