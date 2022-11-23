from customers.tests.customer import CustomAPITestCase
from services.models import CustomerServiceConnectingQueueModel, Service
from ._general import create_service, create_customer_service_queue


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
        qs = CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer
        )
        new_item = qs.push_front(
            customer_id=self.customer.pk,
            service_id=self.service.pk
        )
        self.assertEqual(new_item.number_queue, 1)
        queue = qs.order_by('number_queue')
        self.assertEqual(queue.count(), 6)
        for i, q in enumerate(queue, 1):
            self.assertEqual(q.number_queue, i)
            self.assertEqual(q.service_id, self.service.pk)

    def test_push_back(self):
        qs = CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer
        )
        new_item = qs.push_back(
            customer_id=self.customer.pk,
            service_id=self.service.pk
        )
        self.assertEqual(new_item.number_queue, 6)
        queue = qs.order_by('number_queue')
        self.assertEqual(queue.count(), 6)
        for i, q in enumerate(queue, 1):
            self.assertEqual(q.number_queue, i)
            self.assertEqual(q.service_id, self.service.pk)

    def test_swap(self):
        first = self.service_queues[0]
        sec = self.service_queues[1]
        self.assertEqual(first.number_queue, 1)
        self.assertEqual(sec.number_queue, 2)
        CustomerServiceConnectingQueueModel.objects.swap(
            first=first,
            second=sec
        )
        first.refresh_from_db()
        sec.refresh_from_db()
        self.assertEqual(first.number_queue, 2)
        self.assertEqual(sec.number_queue, 1)

    def test_append(self):
        query = CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer,
            # service=self.service
        )
        self.assertEqual(query.count(), 5)
        new_queue_item = self.service_queue.append(s=self.service)
        self.assertEqual(new_queue_item.number_queue, 6)
        self.assertEqual(query.count(), 6)
        for i, q in enumerate(query, 1):
            self.assertEqual(q.number_queue, i)

    def test_prepend(self):
        query = CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer,
            # service=self.service
        ).order_by('number_queue')
        self.assertEqual(query.count(), 5)
        new_queue_item = self.service_queue.prepend(s=self.service)
        self.assertEqual(query.count(), 6)
        self.assertEqual(new_queue_item.number_queue, 1)
        for i, q in enumerate(query, 1):
            self.assertEqual(q.number_queue, i)

    def test_pop_back(self):
        query = CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer,
        )
        self.assertEqual(query.count(), 5)
        last = query.pop_back()
        self.assertEqual(last.service.pk, self.service.pk)
        self.assertEqual(last.customer.pk, self.customer.pk)
        self.assertEqual(last.number_queue, 5)
        self.assertEqual(query.count(), 4)

    def test_pop_front(self):
        query = CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer,
        )
        self.assertEqual(query.count(), 5)
        first = query.pop_front()
        self.assertEqual(first.service.pk, self.service.pk)
        self.assertEqual(first.customer.pk, self.customer.pk)
        self.assertEqual(first.number_queue, 1)
        self.assertEqual(query.count(), 4)
