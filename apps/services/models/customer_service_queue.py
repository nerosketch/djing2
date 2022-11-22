from typing import Optional
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from customers.models import Customer
from .service import Service, CustomerService


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
        return self.annotate(
            max_number_queue=self._single_queue_num_subquery(from_start2end=False)
        ).create(
            customer_id=customer_id,
            service_id=service_id,
            number_queue=models.F('max_number_queue') + 1
        )

    def pop_back(self):
        ...

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

    def pop_front(self):
        ...

    def use_multiple(self):
        ...


class CustomerServiceConnectingQueueModelManager(models.Manager):
    """
    Filter queue by number_queue, and returns only items with maximum in the group.
    """
    _queryset_class = CustomerServiceConnectingQuerySet

    def swap(self, first: 'CustomerServiceConnectingQueueModel', second: 'CustomerServiceConnectingQueueModel') -> None:
        with transaction.atomic():
            self.filter(pk=first.pk).update(number_queue=second.number_queue)
            self.filter(pk=second.pk).update(number_queue=first.number_queue)

    def create_new(self, customer_service: CustomerService, ):
        ...


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
        ...

    def prepend(self):
        ...

    def use(self):
        return self.delete()

    class Meta:
        db_table = 'services_queue'
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'number_queue'],
                name='customer_number_queue_unique',
                deferrable=models.Deferrable.DEFERRED,
            )
        ]


def connect_service_if_autoconnect(customer_id: Optional[int] = None):
    """
    Connect service when autoconnect is True, and user have enough money
    """

    customers = Customer.objects.filter(
        is_active=True,
        auto_renewal_service=True,
        balance__gt=0
    ).annotate(
        connected_services_count=models.Count('current_service')
    ).filter(connected_services_count=0)

    if isinstance(customer_id, int):
        customers = customers.filter(pk=customer_id)

    queue_services = CustomerServiceConnectingQueueModel.objects.filter(
        customer__in=customers,
        service__is_admin=False
    ).select_related('service', 'customer').filter_first()

    for queue_item in queue_services.iterator():
        srv = queue_item.service
        srv.pick_service(
            customer=queue_item.customer,
            author=None,
            comment=_("Automatic connect service '%(service_name)s'") % {
                "service_name": srv.title
            }
        )
