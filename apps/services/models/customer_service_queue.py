from typing import Optional
from django.db import models
from django.utils.translation import gettext_lazy as _

from customers.models import Customer
from .service import Service


class CustomerServiceConnectingQueueModelManager(models.QuerySet):
    """
    Filter queue by number_queue, and returns only items with maximum in the group.
    """
    def filter_first_queue_items(self):
        return self.annotate(
            max_number_queue=models.Subquery(
                CustomerServiceConnectingQueueModel.objects.filter(
                    customer_id=models.OuterRef('customer'),
                    service_id=models.OuterRef('service')
                ).order_by('-number_queue').values('number_queue')[:1],
                output_field=models.IntegerField()
            )
        ).filter(
            number_queue=models.F('max_number_queue')
        )


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
    number_queue = models.IntegerField('Number in the queue')

    objects = CustomerServiceConnectingQueueModelManager.as_manager()

    class Meta:
        db_table = 'services_queue'
        unique_together = ('customer', 'number_queue')


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
    ).select_related('service', 'customer').filter_first_queue_items()

    for queue_item in queue_services.iterator():
        srv = queue_item.service
        srv.pick_service(
            customer=queue_item.customer,
            author=None,
            comment=_("Automatic connect service '%(service_name)s'") % {
                "service_name": srv.title
            }
        )
