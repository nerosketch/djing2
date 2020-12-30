from datetime import datetime
from typing import Optional

from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from customers.models import (
    Customer, PassportInfo, CustomerService,
    CustomerRawPassword, AdditionalTelephone,
    PeriodicPayForId
)
from services.models import Service
from sorm_export.hier_export.service import export_nomenclature
from sorm_export.tasks import service_export_task
from sorm_export.tasks.customer_service import customer_service_export_task


@receiver(post_save, sender=Customer)
def customer_post_save_signal(sender, instance: Optional[Customer] = None,
                              created=False, **kwargs):
    pass


@receiver(post_save, sender=PassportInfo)
def customer_passport_info_post_save_signal(sender, instance: Optional[PassportInfo] = None,
                                            created=False, **kwargs):
    pass


@receiver(post_save, sender=CustomerService)
def customer_service_changed(sender, instance: Optional[CustomerService] = None,
                             created=False, **kwargs):
    # if created:
    #     # if created then customer also changed,
    #     # and customer change signal is also called
    #     return
    customer_service_export_task(
        customer_service_id_list=[instance.pk],
        event_time=str(datetime.now())
    )


@receiver(post_save, sender=CustomerRawPassword)
def customer_password_changed(sender, instance: Optional[CustomerRawPassword] = None,
                              created=False, **kwargs):
    if created:
        return
    # process only if changed, not created


@receiver(post_save, sender=AdditionalTelephone)
def customer_additional_telephone_post_save_signal(sender, instance: Optional[AdditionalTelephone] = None,
                                                   created=False, **kwargs):
    pass


@receiver(post_save, sender=PeriodicPayForId)
def customer_periodic_pay_post_save_signal(sender, instance: Optional[PeriodicPayForId] = None,
                                           created=False, **kwargs):
    pass


@receiver(post_save, sender=Service)
def service_post_save_signal(sender, instance: Service, created=False, **kwargs):
    service_export_task(
        service_id_list=[instance.pk],
        event_time=datetime.now()
    )
