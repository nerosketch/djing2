from dataclasses import dataclass
from django.db import models, transaction

from customers.models import Customer

from .service import Service


@dataclass
class QueueRemovedResult:
    customer_id: int
    service_id: int
    number_queue: int


class CustomerServiceConnectingQuerySet(models.QuerySet):
    def _single_queue_num_subquery(self, from_start2end=True):
        if from_start2end:
            m = ''
        else:
            m = '-'
        return models.Subquery(
            self.model.objects.filter(
                customer_id=models.OuterRef('customer'),
                service_id=models.OuterRef('service')
            ).order_by(f'{m}number_queue').values('number_queue')[:1],
            output_field=models.IntegerField()
        )

    def _assign_num_for_new_queue(self, customer_id: int, service_id: int, num: int):
        return self.filter(
            customer_id=customer_id,
            service_id=service_id,
            number_queue__gte=num
        ).update(
            number_queue=models.F('number_queue') + 1
        )

    def filter_first(self):
        return self.annotate(
            min_number_queue=self._single_queue_num_subquery()
        ).filter(
            number_queue=models.F('min_number_queue')
        )

    def filter_last(self):
        return self.annotate(
            max_number_queue=self._single_queue_num_subquery(from_start2end=False)
        ).filter(
            number_queue=models.F('max_number_queue')
        )

    def push_back(self, customer_id: int, service_id: int):
        # TODO: optimize
        with transaction.atomic():
            max_number_queue = self.select_for_update().filter(
                customer_id=customer_id,
                service_id=service_id,
            ).order_by('-number_queue')[:1].values_list('number_queue', flat=True)[0]
            r = self.create(
                customer_id=customer_id,
                service_id=service_id,
                number_queue=max_number_queue + 1
            )
        return r

    def pop_back(self) -> QueueRemovedResult:
        with transaction.atomic():
            qs = self.select_for_update()
            q_item_last_qs = qs.filter_last()
            q_item_last = q_item_last_qs.first()
            rr = QueueRemovedResult(
                service_id=q_item_last.service_id,
                customer_id=q_item_last.customer_id,
                number_queue=q_item_last.number_queue
            )
            if qs.count() > 1:
                q_item_last_qs.delete()
        return rr

    def push_front(self, customer_id: int, service_id: int):
        with transaction.atomic():
            min_number = 1
            self._assign_num_for_new_queue(
                customer_id=customer_id,
                service_id=service_id,
                num=min_number
            )

            r = self.create(
                customer_id=customer_id,
                service_id=service_id,
                number_queue=min_number
            )
        return r

    def pop_front(self) -> QueueRemovedResult:
        with transaction.atomic():
            qs = self.select_for_update()
            q_item_first_qs = qs.filter_first()
            q_item_first = q_item_first_qs.first()
            rr = QueueRemovedResult(
                service_id=q_item_first.service_id,
                customer_id=q_item_first.customer_id,
                number_queue=q_item_first.number_queue
            )
            if qs.count() > 1:
                q_item_first_qs.delete()
        return rr


class CustomerServiceConnectingQueueModelManager(models.Manager):
    """
    Filter queue by number_queue, and returns only items with maximum in the group.
    """
    _queryset_class = CustomerServiceConnectingQuerySet

    def swap(self, first: 'CustomerServiceConnectingQueueModel', second: 'CustomerServiceConnectingQueueModel'):
        with transaction.atomic():
            self.filter(pk=first.pk).update(number_queue=second.number_queue)
            self.filter(pk=second.pk).update(number_queue=first.number_queue)


class CustomerServiceConnectingQueueModel(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='service_queue',
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='customer_service_queue',
    )
    number_queue = models.IntegerField('Number in the queue', db_index=True)

    objects = CustomerServiceConnectingQueueModelManager()

    def append(self, s: Service):
        return CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer,
            service=self.service
        ).push_back(
            customer_id=self.customer_id,
            service_id=s.pk
        )

    def prepend(self, s: Service):
        return CustomerServiceConnectingQueueModel.objects.filter(
            customer=self.customer,
            service=self.service
        ).push_front(
            customer_id=self.customer_id,
            service_id=s.pk
        )

    @property
    def service_title(self):
        return self.service.title

    class Meta:
        db_table = 'services_queue'
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'number_queue'],
                name='customer_number_queue_unique',
                deferrable=models.Deferrable.DEFERRED,
            )
        ]
