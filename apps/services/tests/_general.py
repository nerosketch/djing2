from customers.models import Customer
from services import models


def create_service(self):
    self.service = models.Service.objects.create(
        title="test service",
        speed_in=10.0,
        speed_out=10.0,
        cost=2,
        calc_type=0  # ServiceDefault
    )
    self.service.sites.add(self.site)
    return self.service


def create_customer_service_queue(customer: Customer, service: models.Service, num=1):
    return models.CustomerServiceConnectingQueueModel.objects.bulk_create([
        models.CustomerServiceConnectingQueueModel(
            customer=customer,
            service=service,
            number_queue=n
        ) for n in range(1, num+1, 1)
    ])
